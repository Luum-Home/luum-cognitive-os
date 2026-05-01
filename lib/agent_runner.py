# SCOPE: both
"""Portable sub-agent spawning engine (ADR-064 Task 4.1 / Surface 4).

``spawn()`` is the single public entry point.  It wraps
``lib.openai_compatible_agent_loop.run_agent`` with:

  - Model-hint → provider cascade resolution via ``lib.dispatch`` conventions.
  - Session event persistence to
    ``.cognitive-os/sessions/<sid>/agent-events.jsonl`` in the canonical event
    schema (ADR-033).
  - Hard timeout enforced at the loop level (``timeout_s``).
  - Allowed-tool enforcement delegated to the inner loop (ADR-062 safety rails).
  - ``AgentResult`` dataclass returned to callers.

Security rails (ADR-063 negative scope):
  - No MCP replication.
  - No recursive sub-agents (``COS_AGENT_DEPTH`` env guard; max depth = 1).
  - No ``~/.claude/projects/*.jsonl`` format.
  - No TodoWrite semantics.

Usage::

    from lib.agent_runner import spawn

    result = spawn(
        prompt="List Python files in the project root",
        model="auto",
        allowed_tools=["read_file", "glob_files"],
        timeout_s=120,
    )
    print(result.final_response)

Raises:
    RuntimeError: if recursive sub-agent depth > 1.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.paths import runtime_project_root_or_cwd

# ── Constants ──────────────────────────────────────────────────────────────────

#: Default allowed tool names when caller passes ``None``.
DEFAULT_ALLOWED_TOOLS: List[str] = [
    "read_file",
    "glob_files",
    "grep_files",
    "run_bash",
]

#: ADR-063 depth guard: sub-agents may not spawn further sub-agents.
_MAX_AGENT_DEPTH = 1


# ── Result dataclass ───────────────────────────────────────────────────────────


@dataclass
class AgentResult:
    """Outcome of a ``spawn()`` call."""

    status: str = "unknown"       # "success" | "error" | "timeout"
    final_response: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: Dict[str, int] = field(default_factory=dict)
    session_id: str = ""
    provider: str = ""
    model: str = ""
    iterations: int = 0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Canonical event helpers ────────────────────────────────────────────────────


def _make_event(event_type: str, session_id: str, **kwargs: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "event_type": event_type,
        "session_id": session_id,
        "harness": "bare_cli",
        "ts": time.time(),
    }
    base.update(kwargs)
    return base


def _append_event(path: Path, event: Dict[str, Any]) -> None:
    """Append one canonical event JSON line to the session events file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    except (OSError, TypeError, ValueError):
        pass  # event logging must never crash the agent


# ── Provider resolution ────────────────────────────────────────────────────────


def _resolve_provider(model: str) -> tuple[str, Optional[str]]:
    """Translate an abstract model hint into (provider, model_hint).

    Returns:
        Tuple of (provider_key, model_hint_or_None).
        provider_key is used by run_agent's ``provider`` arg.
        model_hint maps opus/sonnet/haiku to provider-native models.
    """
    model = model.strip().lower()

    if model in ("", "auto"):
        # Default cascade per ADR-049: Qwen primary, Claude fallback.
        return "qwen", None

    if model in ("opus", "claude-opus", "claude"):
        return "qwen", "opus"   # mapped to Qwen's "plus" bundle or Claude

    if model in ("sonnet",):
        return "qwen", "sonnet"

    if model in ("haiku",):
        return "qwen", "haiku"

    if model.startswith("claude-"):
        # Explicit Claude model name: use qwen cascade with tier hint extracted.
        if "opus" in model:
            return "qwen", "opus"
        if "haiku" in model:
            return "qwen", "haiku"
        return "qwen", "sonnet"

    if model.startswith("qwen"):
        return "qwen", model

    # Unknown model name: pass as-is, let run_agent sort it out.
    return "qwen", model


# ── Depth guard ────────────────────────────────────────────────────────────────


def _check_depth() -> None:
    """Raise RuntimeError if already inside a sub-agent (ADR-063)."""
    depth = int(os.environ.get("COS_AGENT_DEPTH", "0") or 0)
    if depth >= _MAX_AGENT_DEPTH:
        raise RuntimeError(
            f"cos-agent: recursive sub-agent detected (depth={depth}). "
            "ADR-063 prohibits nested sub-agents. "
            "Set COS_AGENT_DEPTH=0 in your outer shell to bypass (only for testing)."
        )


# ── Public API ─────────────────────────────────────────────────────────────────


def spawn(
    prompt: str,
    *,
    model: str = "auto",
    allowed_tools: Optional[List[str]] = None,
    timeout_s: int = 600,
    session_id: Optional[str] = None,
    project_dir: Optional[Path] = None,
    verbose: bool = False,
    # Injection points for tests
    _run_agent_fn: Any = None,
) -> AgentResult:
    """Spawn a portable sub-agent and return its result.

    Args:
        prompt: Natural language task for the agent.
        model: Abstract model hint — ``"auto"`` (default), ``"opus"``,
            ``"sonnet"``, ``"haiku"``, or a provider-native name.
        allowed_tools: List of tool names the agent may call.
            Defaults to :data:`DEFAULT_ALLOWED_TOOLS`.
        timeout_s: Hard wall-clock timeout in seconds.  The agent loop is
            terminated after this many seconds; status is set to ``"timeout"``.
        session_id: Optional session identifier.  Auto-generated if omitted.
        project_dir: Root directory for event/transcript files.
            Defaults to :func:`lib.paths.runtime_project_root_or_cwd`.
        verbose: Log loop progress to stderr.
        _run_agent_fn: Test injection — replaces ``run_agent`` call.

    Returns:
        :class:`AgentResult` with ``status``, ``final_response``, ``events``,
        and ``tokens_used`` populated.
    """
    _check_depth()

    sid = session_id or f"bare-cli-{uuid.uuid4().hex[:12]}"
    project = project_dir or runtime_project_root_or_cwd()
    events_path = project / ".cognitive-os" / "sessions" / sid / "agent-events.jsonl"
    tools = list(allowed_tools) if allowed_tools is not None else list(DEFAULT_ALLOWED_TOOLS)

    provider, model_hint = _resolve_provider(model)

    result = AgentResult(
        status="unknown",
        session_id=sid,
        provider=provider,
        model=model_hint or model,
    )

    # Emit session_start
    start_event = _make_event(
        "session_start",
        sid,
        started_at=time.time(),
        cwd=str(project),
        source="cos-agent-spawn",
    )
    _append_event(events_path, start_event)
    result.events.append(start_event)

    # Emit user_prompt_submit
    prompt_event = _make_event(
        "user_prompt_submit",
        sid,
        submitted_at=time.time(),
        prompt_summary=prompt[:160],
    )
    _append_event(events_path, prompt_event)
    result.events.append(prompt_event)

    # ── Run agent loop ─────────────────────────────────────────────────────────
    import signal as _signal

    run_fn = _run_agent_fn
    if run_fn is None:
        from lib.openai_compatible_agent_loop import run_agent as run_fn  # type: ignore[assignment]

    timed_out = False
    loop_result = None

    def _timeout_handler(signum: int, frame: Any) -> None:
        nonlocal timed_out
        timed_out = True
        raise TimeoutError("cos-agent: agent loop timed out")

    old_handler = _signal.signal(_signal.SIGALRM, _timeout_handler)
    _signal.alarm(max(1, int(timeout_s)))

    # Set depth guard so nested spawns are rejected.
    old_depth = os.environ.get("COS_AGENT_DEPTH")
    os.environ["COS_AGENT_DEPTH"] = "1"

    try:
        loop_result = run_fn(
            task=prompt,
            provider=provider,
            tools_allowed=tools if tools else None,
            model_hint=model_hint,
            verbose=verbose,
        )
    except TimeoutError:
        timed_out = True
    except Exception as exc:  # noqa: BLE001
        result.status = "error"
        result.error = f"{type(exc).__name__}: {exc}"[:500]
    finally:
        _signal.alarm(0)
        _signal.signal(_signal.SIGALRM, old_handler)
        # Restore depth env
        if old_depth is None:
            os.environ.pop("COS_AGENT_DEPTH", None)
        else:
            os.environ["COS_AGENT_DEPTH"] = old_depth

    # ── Build result ───────────────────────────────────────────────────────────

    if timed_out:
        result.status = "timeout"
        result.error = f"Agent timed out after {timeout_s}s"
    elif loop_result is not None and result.status not in ("error",):
        result.status = "success" if loop_result.success else "error"
        result.final_response = loop_result.text
        result.iterations = loop_result.iterations
        result.error = loop_result.error
        result.provider = loop_result.provider
        result.model = loop_result.model
        result.tokens_used = {
            "input": loop_result.tokens_in,
            "output": loop_result.tokens_out,
        }

        # Emit ToolUse events from the loop's tool_log
        for entry in loop_result.tool_log:
            te = _make_event(
                "tool_use_end",
                sid,
                tool_name=entry.get("tool") or entry.get("tool_name") or "unknown",
                exit_status=entry.get("status") or "unknown",
                agent_id=sid,
            )
            _append_event(events_path, te)
            result.events.append(te)

    # Emit session_end
    end_event = _make_event(
        "session_end",
        sid,
        ended_at=time.time(),
        exit_status=result.status,
    )
    _append_event(events_path, end_event)
    result.events.append(end_event)

    return result
