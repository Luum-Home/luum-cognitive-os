"""Execute Claude Code programmatically via CLI subprocess.

Provides a structured executor with cost tracking, retry logic,
timeout management, and stream-json output parsing.

Usage:
    from lib.claude_executor import ClaudeExecutor, ClaudeResult

    executor = ClaudeExecutor(working_dir="/path/to/project")
    result = executor.run("Explain this codebase structure")

    print(result.success)
    print(result.result_text)
    print(result.cost_usd)

Python 3.9+ compatible.
"""

import json
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Model name mapping for the --model flag
MODEL_MAP: Dict[str, str] = {
    "opus": "claude-opus-4-20250514",
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-haiku-3-5-20241022",
}

# Cost per 1M tokens (input, output) by model family
MODEL_COSTS: Dict[str, Tuple[float, float]] = {
    "opus": (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku": (0.25, 1.25),
}

# Environment variables safe to pass to subprocess
ENV_ALLOWLIST: List[str] = [
    "ANTHROPIC_API_KEY",
    "HOME",
    "USER",
    "PATH",
    "SHELL",
    "TERM",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "CLAUDE_CODE_PATH",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_PAT",
]


class RetryCode(str, Enum):
    """Classification of errors for retry decisions."""
    NONE = "none"
    CLAUDE_CODE_ERROR = "claude_code_error"
    TIMEOUT_ERROR = "timeout_error"
    EXECUTION_ERROR = "execution_error"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"


# Exit codes / error patterns that are retryable
_RETRYABLE_CODES = {RetryCode.CLAUDE_CODE_ERROR, RetryCode.TIMEOUT_ERROR, RetryCode.RATE_LIMIT}
_NON_RETRYABLE_CODES = {RetryCode.AUTH_ERROR}


@dataclass
class ToolCall:
    """A single tool invocation extracted from stream output."""
    name: str
    input_summary: str
    tool_use_id: str = ""


@dataclass
class ClaudeResult:
    """Structured result from a Claude Code execution."""
    success: bool
    result_text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_secs: float = 0.0
    tool_calls: List[ToolCall] = field(default_factory=list)
    model_used: str = ""
    session_id: str = ""
    retry_code: RetryCode = RetryCode.NONE
    error_message: str = ""
    exit_code: int = 0


def _classify_error(exit_code: int, stderr: str) -> RetryCode:
    """Classify an error into a retry code based on exit code and stderr."""
    stderr_lower = stderr.lower()
    if "rate limit" in stderr_lower or "429" in stderr_lower:
        return RetryCode.RATE_LIMIT
    if "auth" in stderr_lower or "401" in stderr_lower or "api key" in stderr_lower:
        return RetryCode.AUTH_ERROR
    if exit_code != 0:
        return RetryCode.CLAUDE_CODE_ERROR
    return RetryCode.NONE


def _get_safe_env(extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build a filtered environment dict with only allowlisted vars."""
    safe: Dict[str, str] = {}
    for key in ENV_ALLOWLIST:
        val = os.environ.get(key)
        if val is not None:
            safe[key] = val

    # Map GITHUB_PAT -> GH_TOKEN if GH_TOKEN not already set
    if "GH_TOKEN" not in safe:
        pat = os.environ.get("GITHUB_PAT")
        if pat:
            safe["GH_TOKEN"] = pat

    safe["PYTHONUNBUFFERED"] = "1"
    safe["PWD"] = os.getcwd()

    if extra_env:
        safe.update(extra_env)

    return safe


def _kill_process_group(process: subprocess.Popen) -> None:
    """Kill the entire process group (parent + all children)."""
    try:
        pgid = os.getpgid(process.pid)
        os.killpg(pgid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


def _resolve_model(model: Optional[str]) -> Optional[str]:
    """Resolve a short model name to a full model ID."""
    if model is None:
        return None
    if model in MODEL_MAP:
        return MODEL_MAP[model]
    # Assume it's already a full model ID
    return model


def _model_family(model_id: str) -> str:
    """Extract the model family (opus/sonnet/haiku) from a model ID."""
    model_lower = model_id.lower()
    for family in ("opus", "sonnet", "haiku"):
        if family in model_lower:
            return family
    return "sonnet"  # default assumption


def _estimate_cost(tokens_in: int, tokens_out: int, model_family_name: str) -> float:
    """Estimate USD cost from token counts and model family."""
    input_price, output_price = MODEL_COSTS.get(model_family_name, MODEL_COSTS["sonnet"])
    return (tokens_in * input_price + tokens_out * output_price) / 1_000_000


def _tool_summary(tool_name: str, inp: Dict[str, Any]) -> str:
    """Return a short summary of what a tool is doing."""
    if tool_name in ("Read", "read"):
        return inp.get("file_path", "")[-60:]
    if tool_name in ("Write", "write"):
        return inp.get("file_path", "")[-60:]
    if tool_name in ("Edit", "edit"):
        return inp.get("file_path", "")[-60:]
    if tool_name in ("Bash", "bash"):
        return inp.get("command", "")[:80]
    if tool_name in ("Glob", "glob"):
        return inp.get("pattern", "")
    if tool_name in ("Grep", "grep"):
        return '"%s" in %s' % (inp.get("pattern", ""), inp.get("path", "."))
    if tool_name == "Task":
        return inp.get("description", "")[:60]
    if tool_name == "Skill":
        return inp.get("skill", "")
    return ""


class ClaudeExecutor:
    """Execute Claude Code CLI as a subprocess with structured output parsing.

    Uses ``claude -p <prompt> --output-format stream-json --verbose`` to run
    Claude Code in non-interactive mode. Parses the JSONL stream to extract
    tool calls, assistant text, token usage, and the final result message.

    Args:
        working_dir: Directory to run claude in. Defaults to cwd.
        claude_path: Path to the claude CLI binary. Defaults to CLAUDE_CODE_PATH
                     env var or "claude".
        default_model: Default model shortname (opus/sonnet/haiku) or full ID.
        default_timeout: Default timeout in seconds. 0 means no timeout.
        allowed_tools: List of tool names to allow (passed as --allowedTools).
        extra_env: Additional environment variables to pass to subprocess.
        verbose: Whether to print streaming output to console.
        agent_id: Optional agent ID for bus communication. When set and Valkey
                  is available, publishes heartbeats and progress events.
    """

    def __init__(
        self,
        working_dir: Optional[str] = None,
        claude_path: Optional[str] = None,
        default_model: Optional[str] = None,
        default_timeout: int = 600,
        allowed_tools: Optional[List[str]] = None,
        extra_env: Optional[Dict[str, str]] = None,
        verbose: bool = False,
        agent_id: Optional[str] = None,
    ):
        self.working_dir = working_dir or os.getcwd()
        self.claude_path = claude_path or os.environ.get("CLAUDE_CODE_PATH", "claude")
        self.default_model = default_model
        self.default_timeout = default_timeout
        self.allowed_tools = allowed_tools
        self.extra_env = extra_env
        self.verbose = verbose
        self.agent_id = agent_id
        self._bus_publisher: Optional[Any] = None

        # Initialize agent bus publisher if agent_id is provided
        if agent_id:
            try:
                from lib.agent_bus import AgentPublisher

                self._bus_publisher = AgentPublisher(agent_id)
                self._bus_publisher.start_heartbeat_thread()
                logger.debug("Agent bus publisher initialized for %s", agent_id)
            except Exception as e:
                logger.debug("Agent bus not available: %s", e)
                self._bus_publisher = None

    def _build_command(
        self,
        prompt: str,
        model: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> List[str]:
        """Build the claude CLI command list."""
        cmd: List[str] = [self.claude_path, "-p", prompt]
        cmd.extend(["--output-format", "stream-json"])
        cmd.append("--verbose")

        resolved = _resolve_model(model or self.default_model)
        if resolved:
            cmd.extend(["--model", resolved])

        tools = allowed_tools or self.allowed_tools
        if tools:
            for tool in tools:
                cmd.extend(["--allowedTools", tool])

        return cmd

    def _parse_stream(
        self,
        messages: List[Dict[str, Any]],
    ) -> Tuple[str, List[ToolCall], int, int, str, str]:
        """Parse collected JSONL messages into structured data.

        Returns:
            Tuple of (result_text, tool_calls, tokens_in, tokens_out,
            model_used, session_id).
        """
        tool_calls: List[ToolCall] = []
        assistant_texts: List[str] = []
        result_text = ""
        tokens_in = 0
        tokens_out = 0
        model_used = ""
        session_id = ""

        for msg in messages:
            msg_type = msg.get("type", "")

            if msg_type == "assistant":
                content = msg.get("message", {}).get("content", [])
                usage = msg.get("message", {}).get("usage", {})
                if usage:
                    tokens_in += usage.get("input_tokens", 0)
                    tokens_out += usage.get("output_tokens", 0)

                m = msg.get("message", {}).get("model", "")
                if m:
                    model_used = m

                for block in content:
                    if block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            assistant_texts.append(text)
                    elif block.get("type") == "tool_use":
                        tc = ToolCall(
                            name=block.get("name", "unknown"),
                            input_summary=_tool_summary(
                                block.get("name", ""), block.get("input", {})
                            ),
                            tool_use_id=block.get("id", ""),
                        )
                        tool_calls.append(tc)

            elif msg_type == "result":
                result_text = msg.get("result", "")
                session_id = msg.get("session_id", "")
                is_error = msg.get("is_error", False)
                if is_error and not result_text:
                    result_text = "[error] " + msg.get("error", "Unknown error")

                # Also capture usage from result message if present
                usage = msg.get("usage", {})
                if usage:
                    tokens_in += usage.get("input_tokens", 0)
                    tokens_out += usage.get("output_tokens", 0)

        # Fallback: if result_text is empty, use assistant text
        if not result_text:
            result_text = "\n".join(assistant_texts)

        return result_text, tool_calls, tokens_in, tokens_out, model_used, session_id

    def _stream_to_console(self, line: str) -> None:
        """Print tool/assistant activity from a JSONL line to console."""
        try:
            msg = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return

        msg_type = msg.get("type")
        if msg_type == "assistant":
            content = msg.get("message", {}).get("content", [])
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        if self.verbose:
                            preview = text[:120] + ("..." if len(text) > 120 else "")
                            print("  \033[36mclaude:\033[0m %s" % preview)
                        # Check for NEEDS_CLARIFICATION in text
                        if self._bus_publisher and "NEEDS_CLARIFICATION" in text:
                            # Extract questions (lines starting with - or *)
                            questions = [
                                ln.strip().lstrip("-* ")
                                for ln in text.split("\n")
                                if ln.strip().startswith(("-", "*"))
                                and ln.strip().lstrip("-* ")
                            ]
                            if questions:
                                self._bus_publisher.ask_clarification(questions, timeout=0)
                elif block.get("type") == "tool_use":
                    tool = block.get("name", "unknown")
                    detail = _tool_summary(tool, block.get("input", {}))
                    if self.verbose:
                        print("  \033[33mtool:\033[0m %s \033[2m%s\033[0m" % (tool, detail))
                    # Publish tool progress to agent bus
                    if self._bus_publisher:
                        file_path = ""
                        if tool in ("Read", "Write", "Edit", "read", "write", "edit"):
                            file_path = block.get("input", {}).get("file_path", "")
                        self._bus_publisher.progress(
                            tool=tool, file=file_path, action=detail
                        )

    def run(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> ClaudeResult:
        """Execute a single Claude Code prompt and return structured result.

        Args:
            prompt: The prompt string or slash command to execute.
            model: Model shortname (opus/sonnet/haiku) or full ID. Overrides default.
            timeout: Timeout in seconds. 0 for no timeout. Overrides default.
            allowed_tools: Tool allowlist. Overrides instance default.

        Returns:
            ClaudeResult with execution details.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout
        cmd = self._build_command(prompt, model=model, allowed_tools=allowed_tools)
        env = _get_safe_env(self.extra_env)

        start_time = time.monotonic()
        process: Optional[subprocess.Popen] = None
        messages: List[Dict[str, Any]] = []

        try:
            logger.debug("Running: %s", " ".join(cmd[:5]))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=self.working_dir,
                start_new_session=True,
            )

            # Stream stdout line by line, collecting JSONL messages
            assert process.stdout is not None
            for line in process.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except (json.JSONDecodeError, ValueError):
                    pass
                self._stream_to_console(line)

            # Wait for process to finish
            wait_timeout: Optional[int] = effective_timeout if effective_timeout > 0 else None
            try:
                process.wait(timeout=wait_timeout)
            except subprocess.TimeoutExpired:
                _kill_process_group(process)
                duration = time.monotonic() - start_time
                if self._bus_publisher:
                    self._bus_publisher.report_error(
                        "Timeout after %d seconds" % effective_timeout
                    )
                    self._bus_publisher.stop()
                return ClaudeResult(
                    success=False,
                    result_text="Timeout after %d seconds" % effective_timeout,
                    duration_secs=round(duration, 2),
                    retry_code=RetryCode.TIMEOUT_ERROR,
                    error_message="Process timed out",
                    exit_code=-1,
                )

            stderr_output = process.stderr.read() if process.stderr else ""
            duration = time.monotonic() - start_time
            exit_code = process.returncode

            # Parse collected messages
            result_text, tool_calls, tokens_in, tokens_out, model_used, session_id = (
                self._parse_stream(messages)
            )

            # Determine model family for cost calculation
            effective_model = model or self.default_model or ""
            family = _model_family(model_used or effective_model)
            cost = _estimate_cost(tokens_in, tokens_out, family)

            if exit_code == 0:
                # Check if result message indicated an error
                result_msg: Optional[Dict[str, Any]] = None
                for m in reversed(messages):
                    if m.get("type") == "result":
                        result_msg = m
                        break

                is_error = False
                if result_msg:
                    is_error = result_msg.get("is_error", False)

                # Report to agent bus
                if self._bus_publisher:
                    if is_error:
                        self._bus_publisher.report_error(result_text[:500])
                    else:
                        self._bus_publisher.report_complete(result_text[:500])
                    self._bus_publisher.stop()

                return ClaudeResult(
                    success=not is_error,
                    result_text=result_text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=round(cost, 6),
                    duration_secs=round(duration, 2),
                    tool_calls=tool_calls,
                    model_used=model_used,
                    session_id=session_id,
                    retry_code=RetryCode.NONE,
                    exit_code=exit_code,
                )
            else:
                retry_code = _classify_error(exit_code, stderr_output)
                error_msg = "Exit code %d: %s" % (exit_code, stderr_output.strip()[:500])

                # Report error to agent bus
                if self._bus_publisher:
                    self._bus_publisher.report_error(error_msg[:500])
                    self._bus_publisher.stop()

                return ClaudeResult(
                    success=False,
                    result_text=result_text or error_msg,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=round(cost, 6),
                    duration_secs=round(duration, 2),
                    tool_calls=tool_calls,
                    model_used=model_used,
                    session_id=session_id,
                    retry_code=retry_code,
                    error_message=error_msg,
                    exit_code=exit_code,
                )

        except Exception as e:
            duration = time.monotonic() - start_time
            if process is not None:
                _kill_process_group(process)
            if self._bus_publisher:
                self._bus_publisher.report_error("Execution error: %s" % str(e))
                self._bus_publisher.stop()
            return ClaudeResult(
                success=False,
                result_text="Execution error: %s" % str(e),
                duration_secs=round(duration, 2),
                retry_code=RetryCode.EXECUTION_ERROR,
                error_message=str(e),
                exit_code=-1,
            )

    def run_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        allowed_tools: Optional[List[str]] = None,
        max_retries: int = 3,
        base_delay: float = 2.0,
    ) -> ClaudeResult:
        """Execute with exponential backoff retry on transient errors.

        Retries on CLAUDE_CODE_ERROR, TIMEOUT_ERROR, and RATE_LIMIT.
        Stops immediately on AUTH_ERROR or success.

        Args:
            prompt: The prompt to execute.
            model: Model shortname or full ID.
            timeout: Timeout in seconds.
            allowed_tools: Tool allowlist.
            max_retries: Maximum number of retry attempts (total = max_retries + 1).
            base_delay: Base delay in seconds for exponential backoff.

        Returns:
            ClaudeResult from the last attempt.
        """
        last_result: Optional[ClaudeResult] = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logger.info(
                    "Retry %d/%d after %.1fs delay", attempt, max_retries, delay
                )
                time.sleep(delay)

            result = self.run(
                prompt=prompt,
                model=model,
                timeout=timeout,
                allowed_tools=allowed_tools,
            )
            last_result = result

            # Success -> return immediately
            if result.success:
                return result

            # Non-retryable error -> return immediately
            if result.retry_code in _NON_RETRYABLE_CODES:
                logger.warning(
                    "Non-retryable error (%s), stopping", result.retry_code.value
                )
                return result

            # Not retryable (NONE means unknown) -> return
            if result.retry_code not in _RETRYABLE_CODES:
                return result

            logger.warning(
                "Attempt %d failed with %s: %s",
                attempt + 1,
                result.retry_code.value,
                result.error_message[:200],
            )

        # Exhausted retries
        assert last_result is not None
        return last_result

    def slash(
        self,
        command: str,
        args: str = "",
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ClaudeResult:
        """Execute a Claude Code slash command.

        Args:
            command: Slash command (e.g. "/plan-feature" or "plan-feature").
            args: Arguments to pass after the command.
            model: Model shortname or full ID.
            timeout: Timeout in seconds.

        Returns:
            ClaudeResult from execution.
        """
        if not command.startswith("/"):
            command = "/" + command
        prompt = ("%s %s" % (command, args)).strip()
        return self.run(prompt=prompt, model=model, timeout=timeout)
