# SCOPE: both
"""Qwen agent loop — OpenAI tool-use iteration over Alibaba Qwen (ADR-051 Phase 1).

Minimal multi-turn agent loop for sub-agents dispatched to Qwen instead of
consuming Claude Max quota. Uses the OpenAI SDK's function-calling protocol
(supported by Qwen's OpenAI-compatible endpoint) to iterate:

    user task -> model emits tool_calls (or final text) -> loop executes
    each tool, feeds result back as role=tool message -> repeat until model
    returns text with no tool_calls, or a cap trips.

MVP tool set (Phase 1): read_file, edit_file, run_bash. Phase 2+ add Grep,
Glob, WebFetch (see ADR-051). Safety rails are hard-coded (no config overrides):
run_bash substring blocklist, 30s default timeout, edit_file requires extant
file, max_iterations cap, token budget cap, tools_allowed filter surfaces as
a tool-result error rather than a Python exception.

Reference: docs/adrs/ADR-051-qwen-agent-loop.md
Upstream:  docs/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from lib import qwen_provider

logger = logging.getLogger(__name__)

# Hard caps — set per-call via run_agent args.
DEFAULT_MAX_ITERATIONS = 20
DEFAULT_TOKEN_BUDGET = 100_000
DEFAULT_BASH_TIMEOUT_S = 30

# run_bash blocklist: substring match, safety-first. Not a sandbox — catches
# obvious foot-guns only. Real isolation belongs to the caller (container).
BASH_BLOCKLIST = ("rm -rf", "sudo", "kill", "git push", "curl")


# Tool schemas — OpenAI function-calling format, passed verbatim to the model.

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the local filesystem. Returns the file text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or project-relative path to the file to read.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in an existing file. The old_string must "
                "appear exactly once in the file. Does NOT create new files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path":       {"type": "string", "description": "Path to the file (must already exist)."},
                    "old_string": {"type": "string", "description": "Exact text to replace (must match once)."},
                    "new_string": {"type": "string", "description": "Replacement text."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": (
                "Run a shell command and return stdout, stderr, and exit code. "
                "Times out after 30 seconds by default. Dangerous commands "
                "(rm -rf, sudo, kill, git push, curl) are rejected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command":   {"type": "string", "description": "Shell command to execute."},
                    "timeout_s": {"type": "integer", "description": "Timeout in seconds (default 30, max 120).", "default": 30},
                },
                "required": ["command"],
            },
        },
    },
]

ALL_TOOL_NAMES = {s["function"]["name"] for s in TOOL_SCHEMAS}


@dataclass
class AgentLoopResult:
    """Outcome of a Qwen agent loop run."""

    success: bool
    text: str = ""                                       # final assistant text
    iterations: int = 0                                  # loops consumed
    tool_calls_made: int = 0                             # total tool invocations
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    stop_reason: str = ""                                # "finished" | "max_iterations" | "budget" | "error"
    error: str = ""
    messages_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_log: List[Dict[str, Any]] = field(default_factory=list)


# Tool impls — each returns a string the model sees. Never raise: errors are
# returned as strings so the model can retry with corrected arguments.


def _tool_read_file(args: Dict[str, Any]) -> str:
    path = args.get("path", "")
    if not path:
        return "ERROR: missing required argument 'path'"
    try:
        p = Path(path)
        if not p.exists():
            return f"ERROR: file does not exist: {path}"
        if not p.is_file():
            return f"ERROR: not a regular file: {path}"
        return p.read_text()
    except Exception as exc:  # noqa: BLE001 — surface error to model
        return f"ERROR: {type(exc).__name__}: {exc}"


def _tool_edit_file(args: Dict[str, Any]) -> str:
    path = args.get("path", "")
    old_string = args.get("old_string", "")
    new_string = args.get("new_string", "")

    if not path:
        return "ERROR: missing required argument 'path'"
    if old_string == "":
        return "ERROR: old_string may not be empty"

    try:
        p = Path(path)
        if not p.exists():
            return f"ERROR: file does not exist: {path} (edit_file does not create files)"
        if not p.is_file():
            return f"ERROR: not a regular file: {path}"
        original = p.read_text()
        count = original.count(old_string)
        if count == 0:
            return f"ERROR: old_string not found in {path}"
        if count > 1:
            return f"ERROR: old_string appears {count} times in {path}; must be unique"
        p.write_text(original.replace(old_string, new_string, 1))
        return f"OK: replaced 1 occurrence in {path}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"


def _tool_run_bash(args: Dict[str, Any]) -> str:
    command = args.get("command", "")
    timeout_s = int(args.get("timeout_s", DEFAULT_BASH_TIMEOUT_S) or DEFAULT_BASH_TIMEOUT_S)
    timeout_s = max(1, min(timeout_s, 120))

    if not command:
        return "ERROR: missing required argument 'command'"

    # Blocklist — substring match, no shell tokenization.
    lowered = command.lower()
    for bad in BASH_BLOCKLIST:
        if bad in lowered:
            return f"ERROR: command rejected by blocklist (contains {bad!r})"

    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout_s}s"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"

    return (
        f"exit_code: {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}"
    )


TOOL_IMPLS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "read_file": _tool_read_file,
    "edit_file": _tool_edit_file,
    "run_bash":  _tool_run_bash,
}


def _execute_tool(
    name: str,
    arguments_json: str,
    tools_allowed: Optional[List[str]],
) -> str:
    """Execute a tool call. Returns the string the model will see as result.

    Never raises — any error is surfaced as an ERROR string so the model can
    retry with corrected arguments.
    """
    if tools_allowed is not None and name not in tools_allowed:
        return f"ERROR: tool {name!r} is not in the allowed list {tools_allowed!r} for this task"

    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return f"ERROR: unknown tool {name!r}"

    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON arguments: {exc}"

    return impl(args)


def run_agent(
    task: str,
    tools_allowed: Optional[List[str]] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    model: str = qwen_provider.DEFAULT_MODEL,
    system_prompt: Optional[str] = None,
    verbose: bool = False,
    client: Any = None,
) -> AgentLoopResult:
    """Run a Qwen agent loop until the model stops calling tools or a cap trips.

    Args:
        task: user instruction (natural language).
        tools_allowed: subset of tool names the model may call. None = all.
        max_iterations: hard cap on chat-completion rounds (default 20).
        token_budget: hard cap on cumulative prompt+completion tokens (default 100K).
        model: Qwen model name (see qwen_provider.RECOMMENDED_MODELS).
        system_prompt: optional system message prepended to the conversation.
        verbose: log each iteration to the module logger at INFO level.
        client: OpenAI-compatible client override (tests pass a mock here).
            If None, obtained via qwen_provider._get_openai_client().

    Returns:
        AgentLoopResult with success/text and metrics. On failure, `error`
        is populated; `messages_history` always reflects whatever was exchanged.
    """
    # Validate tools_allowed membership early — cheap guard.
    if tools_allowed is not None:
        unknown = [t for t in tools_allowed if t not in ALL_TOOL_NAMES]
        if unknown:
            return AgentLoopResult(
                success=False,
                stop_reason="error",
                error=f"tools_allowed contains unknown tool(s): {unknown}",
            )

    if client is None:
        client = qwen_provider._get_openai_client()
    if client is None:
        return AgentLoopResult(
            success=False,
            stop_reason="error",
            error="Qwen client unavailable (ALIBABA_QWEN_API_KEY unset or openai SDK missing)",
        )

    # Filter schemas to the allowed subset so we don't tempt the model with
    # tools it can't actually use.
    if tools_allowed is None:
        schemas = TOOL_SCHEMAS
    else:
        schemas = [s for s in TOOL_SCHEMAS if s["function"]["name"] in tools_allowed]

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": task})

    result = AgentLoopResult(success=False, messages_history=messages)

    for i in range(max_iterations):
        result.iterations = i + 1

        if verbose:
            logger.info("qwen-agent iter %d/%d (msgs=%d)", i + 1, max_iterations, len(messages))

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=schemas if schemas else None,
            )
        except Exception as exc:  # noqa: BLE001
            result.stop_reason = "error"
            result.error = f"{type(exc).__name__}: {exc}"[:500]
            return result

        # Track token usage.
        usage = getattr(response, "usage", None)
        if usage is not None:
            result.tokens_in += getattr(usage, "prompt_tokens", 0) or 0
            result.tokens_out += getattr(usage, "completion_tokens", 0) or 0

        if result.tokens_in + result.tokens_out > token_budget:
            result.stop_reason = "budget"
            result.error = (
                f"token budget exceeded: {result.tokens_in + result.tokens_out} > {token_budget}"
            )
            # Keep whatever text we have so far, if any.
            return result

        choices = getattr(response, "choices", None) or []
        if not choices:
            result.stop_reason = "error"
            result.error = "model returned no choices"
            return result
        msg = choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            # Terminal — model has produced a final text response.
            result.text = getattr(msg, "content", "") or ""
            result.success = True
            result.stop_reason = "finished"
            messages.append({"role": "assistant", "content": result.text})
            result.cost_usd = qwen_provider.estimate_cost(
                model, result.tokens_in, result.tokens_out
            )
            return result

        # Record the assistant turn that produced the tool_calls.
        messages.append(
            {
                "role": "assistant",
                "content": getattr(msg, "content", "") or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        # Execute each tool call in order.
        for tc in tool_calls:
            name = tc.function.name
            arguments_json = tc.function.arguments or "{}"
            if verbose:
                logger.info("qwen-agent tool call: %s args=%s", name, arguments_json[:200])

            tool_result = _execute_tool(name, arguments_json, tools_allowed)
            result.tool_calls_made += 1
            result.tool_log.append(
                {
                    "iteration": i + 1,
                    "name": name,
                    "arguments": arguments_json,
                    "result_preview": tool_result[:500],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                }
            )

        # Loop continues — model will see tool results on the next turn.

    # Max iterations reached without a terminal assistant message.
    result.stop_reason = "max_iterations"
    result.error = f"max_iterations ({max_iterations}) reached without a final response"
    result.cost_usd = qwen_provider.estimate_cost(model, result.tokens_in, result.tokens_out)
    return result
