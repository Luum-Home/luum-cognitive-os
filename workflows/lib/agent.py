"""Execute Claude Code programmatically via CLI."""

import json
import os
import signal
import subprocess
import time
from typing import List, Optional

from .data_types import AgentPromptRequest, AgentPromptResponse

# Load .env files if present (non-fatal if python-dotenv not installed)
try:
    from dotenv import load_dotenv

    _project_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".."
    )
    _project_env = os.path.join(_project_root, ".env")
    _project_env_local = os.path.join(_project_root, ".env.local")
    _workflows_env = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", ".env"
    )
    # Load in order: project .env -> project .env.local -> .cognitive-os/workflows/.env
    # Later files override earlier ones
    if os.path.exists(_project_env):
        load_dotenv(_project_env)
    if os.path.exists(_project_env_local):
        load_dotenv(_project_env_local, override=True)
    if os.path.exists(_workflows_env):
        load_dotenv(_workflows_env, override=True)
except ImportError:
    pass

CLAUDE_PATH = os.getenv("CLAUDE_CODE_PATH", "claude")

# ANSI colors
_CYAN = "\033[36m"
_DIM = "\033[2m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_RESET = "\033[0m"


def _tool_summary(tool_name: str, inp: dict) -> str:
    """Return a short human-readable summary for a tool invocation."""
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
        return f'"{inp.get("pattern", "")}" in {inp.get("path", ".")}'
    if tool_name == "Task":
        return inp.get("description", "")[:60]
    if tool_name == "Skill":
        return inp.get("skill", "")
    return ""


def _kill_process_group(process: subprocess.Popen) -> None:
    """Terminate the full process group, escalating to SIGKILL if needed."""
    try:
        pgid = os.getpgid(process.pid)
        os.killpg(pgid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


def _get_safe_env() -> dict:
    """Build a minimal environment dict for subprocess execution."""
    safe_env = {
        "HOME": os.getenv("HOME"),
        "USER": os.getenv("USER"),
        "PATH": os.getenv("PATH"),
        "SHELL": os.getenv("SHELL"),
        "TERM": os.getenv("TERM"),
        "PYTHONUNBUFFERED": "1",
        "PWD": os.getcwd(),
    }
    return {k: v for k, v in safe_env.items() if v is not None}


def _stream_tool_info(line: str) -> None:
    """Parse a JSONL line and print tool/assistant activity to console."""
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
                    preview = text[:120] + ("..." if len(text) > 120 else "")
                    print(f"  {_CYAN}claude:{_RESET} {preview}")
            elif block.get("type") == "tool_use":
                tool = block.get("name", "unknown")
                detail = _tool_summary(tool, block.get("input", {}))
                print(f"  {_YELLOW}tool:{_RESET} {tool} {_DIM}{detail}{_RESET}")


def prompt_with_retry(
    request: AgentPromptRequest,
    cwd: str,
    output_jsonl_path: Optional[str] = None,
    max_retries: int = 2,
    retry_delays: Optional[List[float]] = None,
) -> AgentPromptResponse:
    """Execute a Claude Code prompt with retry logic.

    Args:
        request: The prompt request configuration.
        cwd: Working directory for Claude.
        output_jsonl_path: Path to save raw JSONL output.
        max_retries: Maximum retry attempts on failure.
        retry_delays: Seconds to wait before each retry (indexed by attempt-1).

    Returns:
        AgentPromptResponse with results.
    """
    if retry_delays is None:
        retry_delays = [3, 10]

    start_time = time.time()

    for attempt in range(max_retries + 1):
        if attempt > 0:
            delay = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
            time.sleep(delay)

        try:
            cmd = [
                CLAUDE_PATH,
                "--print",
                "--verbose",
                "--output-format",
                "stream-json",
                "--dangerously-skip-permissions",
                request.prompt,
            ]

            if request.allowed_tools:
                for tool in request.allowed_tools:
                    cmd.extend(["--allowedTools", tool])

            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                env=_get_safe_env(),
            )

            output_lines = []

            # Stream output
            for line in process.stdout:
                line = line.strip()
                if line:
                    output_lines.append(line)
                    _stream_tool_info(line)

            process.wait(timeout=request.timeout_seconds)

            # Capture stderr for error diagnostics
            stderr_output = process.stderr.read() if process.stderr else ""

            # Save raw output if path provided
            if output_jsonl_path:
                os.makedirs(os.path.dirname(output_jsonl_path), exist_ok=True)
                with open(output_jsonl_path, "w") as f:
                    f.write("\n".join(output_lines))

            # Extract final result
            final_output = ""
            for line in reversed(output_lines):
                try:
                    msg = json.loads(line)
                    if msg.get("type") == "result":
                        final_output = msg.get("result", "")
                        break
                except json.JSONDecodeError:
                    continue

            duration = time.time() - start_time

            fallback_output = "\n".join(output_lines[-10:])
            if not final_output and not fallback_output and stderr_output:
                fallback_output = stderr_output.strip()

            return AgentPromptResponse(
                success=process.returncode == 0,
                output=final_output or fallback_output,
                duration_seconds=duration,
                raw_jsonl_path=output_jsonl_path,
            )

        except subprocess.TimeoutExpired:
            _kill_process_group(process)
            if attempt < max_retries:
                print(
                    f"  {_YELLOW}Timeout, retrying "
                    f"({attempt + 1}/{max_retries})...{_RESET}"
                )
                continue

        except Exception as e:
            if attempt < max_retries:
                print(
                    f"  {_YELLOW}Error: {e}, retrying "
                    f"({attempt + 1}/{max_retries})...{_RESET}"
                )
                continue
            return AgentPromptResponse(
                success=False,
                output=str(e),
                duration_seconds=time.time() - start_time,
            )

    return AgentPromptResponse(
        success=False,
        output="Max retries exceeded",
        duration_seconds=time.time() - start_time,
    )
