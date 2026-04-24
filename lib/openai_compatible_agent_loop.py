# SCOPE: both
"""OpenAI-compatible tool-use loop over any provider with an OpenAI-shaped endpoint.

Supports Qwen, OpenRouter, Gemini (OpenAI-compat), DeepSeek, Ollama,
OpenAI itself, and any other provider in lib/providers/ that speaks the
OpenAI function-calling protocol.

This module is a generalization of the Qwen-specific loop (ADR-051) to the
full multi-provider cascade (ADR-062). The Qwen-specific module
(lib/qwen_agent_loop.py) is now a backward-compat shim that imports from
here and pre-fills provider="qwen".

Loop mechanics:
    user task → model emits tool_calls (or final text) → loop executes
    each tool, feeds result back as role=tool message → repeat until model
    returns text with no tool_calls, or a cap trips.

Tool set (Phase 1): read_file, edit_file, run_bash, web_fetch, grep_files,
glob_files. Phase 2+ may add write_file, sub-agents (see ADR-062).

Safety rails (hard-coded, not config-overridable):
    - run_bash blocklist (rm -rf, sudo, kill, git push, curl)
    - 30s default bash timeout (max 120s)
    - edit_file requires the file to already exist
    - max_iterations cap (default 20)
    - token_budget cap (default 100K)
    - tools_allowed filter returned as tool-result error (not Python exception)

Reference: docs/adrs/ADR-062-multi-provider-agent-loop.md
           docs/adrs/ADR-051-qwen-agent-loop.md
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Hard caps ─────────────────────────────────────────────────────────────────

DEFAULT_MAX_ITERATIONS = 20
DEFAULT_TOKEN_BUDGET = 100_000
DEFAULT_BASH_TIMEOUT_S = 30

BASH_BLOCKLIST = ("rm -rf", "sudo", "kill", "git push", "curl")

# ── Tool schemas (OpenAI function-calling format) ─────────────────────────────

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the local filesystem. Returns the file text (auto-paginated for files >40KB via lib/smart_reader).",
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
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch a URL and return its content as markdown. Delegates to "
                "lib/web_crawler for consistent HTML→markdown conversion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url":       {"type": "string", "description": "HTTP(S) URL to fetch."},
                    "timeout_s": {"type": "integer", "description": "Timeout in seconds (default 30, max 60).", "default": 30},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": (
                "Search file contents for a regex pattern. Uses ripgrep when "
                "available (falls back to grep). Returns matching lines with "
                "file:line prefixes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for."},
                    "path":    {"type": "string", "description": "Directory or file to search (default: current directory).", "default": "."},
                    "glob":    {"type": "string", "description": "Optional file glob filter (e.g. '*.py')."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": (
                "List files matching a glob pattern via pathlib. Returns newline-"
                "separated file paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py' or 'src/*.ts')."},
                    "path":    {"type": "string", "description": "Root directory for the glob (default: current directory).", "default": "."},
                },
                "required": ["pattern"],
            },
        },
    },
]

ALL_TOOL_NAMES = {s["function"]["name"] for s in TOOL_SCHEMAS}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class AgentLoopResult:
    """Outcome of an agent loop run (provider-agnostic)."""

    success: bool
    text: str = ""
    iterations: int = 0
    tool_calls_made: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    stop_reason: str = ""   # "finished" | "max_iterations" | "budget" | "error"
    error: str = ""
    provider: str = ""
    model: str = ""
    messages_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_log: List[Dict[str, Any]] = field(default_factory=list)


# ── Tool implementations ──────────────────────────────────────────────────────

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
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"

    try:
        from lib.smart_reader import SmartReader
        result = SmartReader().read_file(str(p))
        return result.content if hasattr(result, "content") else str(result)
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        pass

    try:
        return p.read_text()
    except Exception as exc:  # noqa: BLE001
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
    lowered = command.lower()
    for bad in BASH_BLOCKLIST:
        if bad in lowered:
            return f"ERROR: command rejected by blocklist (contains {bad!r})"
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout_s}s"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"

    raw_output = f"{proc.stdout}\n{proc.stderr}" if proc.stderr else proc.stdout
    try:
        from lib.smart_truncator import smart_truncate
        compact = smart_truncate(command, raw_output, max_chars=5000)
    except Exception:  # noqa: BLE001
        compact = raw_output[:5000] + (f"\n\n[truncated, {len(raw_output)} total chars]" if len(raw_output) > 5000 else "")

    return f"exit_code: {proc.returncode}\n--- output ---\n{compact}"


def _tool_web_fetch(args: Dict[str, Any]) -> str:
    url = args.get("url", "")
    timeout_s = int(args.get("timeout_s", 30) or 30)
    if not url:
        return "ERROR: missing required argument 'url'"
    timeout_s = max(1, min(timeout_s, 120))
    try:
        from lib.web_crawler import fetch_markdown_sync
    except ImportError as exc:
        return f"ERROR: web_crawler module unavailable: {exc}"
    try:
        markdown = fetch_markdown_sync(url, timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: fetch failed: {type(exc).__name__}: {exc}"
    try:
        from lib.smart_truncator import _head_tail
        return _head_tail(markdown, max_chars=8000)
    except Exception:  # noqa: BLE001
        return markdown[:8000]


def _tool_grep_files(args: Dict[str, Any]) -> str:
    pattern = args.get("pattern", "")
    path = args.get("path", ".")
    glob = args.get("glob", "")
    max_matches = int(args.get("max_matches", 100) or 100)
    max_matches = max(1, min(max_matches, 500))
    if not pattern:
        return "ERROR: missing required argument 'pattern'"
    import shutil
    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "-n", "--no-heading", "--color=never", pattern, path]
        if glob:
            cmd += ["-g", glob]
    else:
        if not shutil.which("grep"):
            return "ERROR: neither rg nor grep found on PATH"
        cmd = ["grep", "-rn", "--color=never", pattern, path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return "ERROR: search timed out after 30s"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"
    if proc.returncode not in (0, 1):
        return f"ERROR: search exit {proc.returncode}: {proc.stderr.strip()[:200]}"
    lines = proc.stdout.strip().splitlines()
    if glob and not rg:
        from fnmatch import fnmatch
        lines = [ln for ln in lines if fnmatch(ln.split(":", 1)[0], glob)]
    if not lines:
        return "no matches"
    truncated = lines[:max_matches]
    suffix = f"\n[truncated — {len(lines)} total matches, showing first {max_matches}]" if len(lines) > max_matches else ""
    return "\n".join(truncated) + suffix


def _tool_glob_files(args: Dict[str, Any]) -> str:
    pattern = args.get("pattern", "")
    root = args.get("path") or args.get("root") or "."
    max_results = int(args.get("max_results", 200) or 200)
    max_results = max(1, min(max_results, 1000))
    if not pattern:
        return "ERROR: missing required argument 'pattern'"
    try:
        root_path = Path(root)
        if not root_path.exists():
            return f"ERROR: root does not exist: {root}"
        if not root_path.is_dir():
            return f"ERROR: root is not a directory: {root}"
        matches = sorted(str(p) for p in root_path.glob(pattern))
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"
    if not matches:
        return "no matches"
    truncated = matches[:max_results]
    suffix = f"\n[truncated — {len(matches)} total matches, showing first {max_results}]" if len(matches) > max_results else ""
    return "\n".join(truncated) + suffix


TOOL_IMPLS: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "read_file":  _tool_read_file,
    "edit_file":  _tool_edit_file,
    "run_bash":   _tool_run_bash,
    "web_fetch":  _tool_web_fetch,
    "grep_files": _tool_grep_files,
    "glob_files": _tool_glob_files,
}


def _execute_tool(name: str, arguments_json: str, tools_allowed: Optional[List[str]]) -> str:
    if tools_allowed is not None and name not in tools_allowed:
        return f"ERROR: tool {name!r} is not in the allowed list {tools_allowed!r}"
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return f"ERROR: unknown tool {name!r}"
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON arguments: {exc}"
    return impl(args)


# ── Provider client resolution ────────────────────────────────────────────────

def _resolve_client(provider: str) -> Any:
    """Return an OpenAI-compatible client for the given provider key.

    Looks up the provider in lib/providers/REGISTRY. Returns None if the
    provider is not configured or not in the registry.
    """
    try:
        from lib.providers import REGISTRY
    except ImportError:
        return None
    mod = REGISTRY.get(provider)
    if mod is None:
        return None
    try:
        return mod.get_client()
    except Exception:  # noqa: BLE001
        return None


def _resolve_model(provider: str, model_hint: Optional[str], default_model: str) -> str:
    """Resolve abstract model tier to provider-native model name."""
    if not model_hint:
        return default_model
    try:
        from lib.providers import REGISTRY
        mod = REGISTRY.get(provider)
        if mod is not None:
            return mod.MODEL_MAP.get(model_hint, default_model)
    except Exception:  # noqa: BLE001
        pass
    return default_model


def _estimate_cost_for_provider(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    try:
        from lib.providers import REGISTRY
        mod = REGISTRY.get(provider)
        if mod is not None and hasattr(mod, "estimate_cost"):
            return mod.estimate_cost(model, tokens_in, tokens_out)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_agent(
    task: str,
    provider: str = "qwen",
    tools_allowed: Optional[List[str]] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    model: Optional[str] = None,
    model_hint: Optional[str] = None,
    system_prompt: Optional[str] = None,
    verbose: bool = False,
    client: Any = None,
    *,
    context_level: str = "none",
) -> AgentLoopResult:
    """Run an OpenAI-compatible agent loop until the model stops calling tools or a cap trips.

    Args:
        task: user instruction (natural language).
        provider: provider key from lib/providers/REGISTRY (default: "qwen").
        tools_allowed: subset of tool names the model may call. None = all.
        max_iterations: hard cap on chat-completion rounds (default 20).
        token_budget: hard cap on cumulative prompt+completion tokens (default 100K).
        model: explicit provider-native model name. Takes priority over model_hint.
        model_hint: abstract tier ("opus"/"sonnet"/"haiku") — mapped per provider.
        system_prompt: optional system message prepended to the conversation.
        verbose: log each iteration to the module logger at INFO level.
        client: OpenAI-compatible client override (tests pass a mock here).
            If None, resolved via lib/providers/REGISTRY[provider].get_client().
        context_level: governance-context injection level (ADR-051 Phase 3).
            "none" (default, backward-compat) = no injection.
            "minimal" prepends templates/agent-preamble.md (~1.5K tokens).
            "full" prepends mandatory-rules + preamble (~5K tokens).

    Returns:
        AgentLoopResult with success/text and metrics.
    """
    # Resolve model name
    try:
        from lib.providers import REGISTRY
        mod = REGISTRY.get(provider)
        default_model = getattr(mod, "DEFAULT_MODEL", "gpt-4o") if mod else "gpt-4o"
    except Exception:  # noqa: BLE001
        default_model = "gpt-4o"

    resolved_model = model or _resolve_model(provider, model_hint, default_model)

    # Governance context injection (ADR-051 Phase 3)
    try:
        from lib.qwen_context_injector import compose_system_prompt
        system_prompt = compose_system_prompt(level=context_level, user_system_prompt=system_prompt)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        pass  # context injection is best-effort

    # Validate tools_allowed
    if tools_allowed is not None:
        unknown = [t for t in tools_allowed if t not in ALL_TOOL_NAMES]
        if unknown:
            return AgentLoopResult(
                success=False,
                stop_reason="error",
                error=f"tools_allowed contains unknown tool(s): {unknown}",
                provider=provider,
                model=resolved_model,
            )

    # Resolve client
    if client is None:
        client = _resolve_client(provider)
    if client is None:
        return AgentLoopResult(
            success=False,
            stop_reason="error",
            error=f"Provider {provider!r} client unavailable (not configured or SDK missing)",
            provider=provider,
            model=resolved_model,
        )

    schemas = TOOL_SCHEMAS if tools_allowed is None else [
        s for s in TOOL_SCHEMAS if s["function"]["name"] in tools_allowed
    ]

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": task})

    result = AgentLoopResult(
        success=False,
        messages_history=messages,
        provider=provider,
        model=resolved_model,
    )

    for i in range(max_iterations):
        result.iterations = i + 1

        if verbose:
            logger.info(
                "agent-loop [%s] iter %d/%d (msgs=%d)",
                provider, i + 1, max_iterations, len(messages),
            )

        try:
            response = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                tools=schemas if schemas else None,
            )
        except Exception as exc:  # noqa: BLE001
            result.stop_reason = "error"
            result.error = f"{type(exc).__name__}: {exc}"[:500]
            return result

        usage = getattr(response, "usage", None)
        if usage is not None:
            result.tokens_in += getattr(usage, "prompt_tokens", 0) or 0
            result.tokens_out += getattr(usage, "completion_tokens", 0) or 0

        if result.tokens_in + result.tokens_out > token_budget:
            result.stop_reason = "budget"
            result.error = f"token budget exceeded: {result.tokens_in + result.tokens_out} > {token_budget}"
            return result

        choices = getattr(response, "choices", None) or []
        if not choices:
            result.stop_reason = "error"
            result.error = "model returned no choices"
            return result

        msg = choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            result.text = getattr(msg, "content", "") or ""
            result.success = True
            result.stop_reason = "finished"
            messages.append({"role": "assistant", "content": result.text})
            result.cost_usd = _estimate_cost_for_provider(
                provider, resolved_model, result.tokens_in, result.tokens_out
            )
            return result

        messages.append({
            "role": "assistant",
            "content": getattr(msg, "content", "") or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            name = tc.function.name
            arguments_json = tc.function.arguments or "{}"
            if verbose:
                logger.info("agent-loop [%s] tool call: %s args=%s", provider, name, arguments_json[:200])

            tool_result = _execute_tool(name, arguments_json, tools_allowed)
            result.tool_calls_made += 1
            result.tool_log.append({
                "iteration": i + 1,
                "name": name,
                "arguments": arguments_json,
                "result_preview": tool_result[:500],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })

    result.stop_reason = "max_iterations"
    result.error = f"max_iterations ({max_iterations}) reached without a final response"
    result.cost_usd = _estimate_cost_for_provider(
        provider, resolved_model, result.tokens_in, result.tokens_out
    )
    return result
