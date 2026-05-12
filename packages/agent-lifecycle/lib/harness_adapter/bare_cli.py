"""Bare-CLI harness adapter (ADR-064 Task 1.2 / Surface 1).

Handles events emitted by ``cos-agent`` and ``cos-skill run`` when invoked
outside any other harness (CI, headless shell, Codex-less terminal).  The
"bare CLI" harness is the fallback: if none of Claude Code's or Codex's env
vars are set, this adapter owns the canonical event stream.

Detection rule
--------------
``detect_harness`` returns ``HarnessName.BARE_CLI`` iff:
  - The payload carries ``harness: "bare_cli"``, OR
  - ``COGNITIVE_OS_HARNESS=bare_cli`` is set in env, OR
  - No harness-specific env vars are present (no ``CLAUDE_CODE_*``, ``CODEX_*``,
    ``AIDER_*``).

The "no-other-harness" fallback is intentionally greedy — it means bare_cli
can ingest any well-formed canonical JSON without fighting with the other
adapters in the dispatch ADAPTERS list (those are checked first).

Supported lifecycle events
--------------------------
  - SessionStart (cos-agent session open)
  - UserPromptSubmit (prompt handed to cos-agent spawn)
  - ToolUseStart (cos-skill/tool execution begins)
  - ToolUseEnd (cos-skill/tool execution ends)
  - SessionEnd (cos-agent session close)

NOT supported (bare CLI has no native equivalent):
  - PreCompact (no native context-compaction in bare_cli)
  - SubagentStart / TeammateIdle / TaskCreated / TaskCompleted

Wire format
-----------
Payloads are plain JSON dicts written to stdin by ``cos-agent`` or
``cos-skill run``.  Required top-level field: ``event`` (canonical event name,
e.g. ``"session_start"``).  Any additional keys map to the event's fields.

Example::

    {"event": "session_start", "session_id": "abc123", "harness": "bare_cli",
     "cwd": "/workspace/project", "started_at": 1714500000.0}

Reference: docs/02-Decisions/adrs/ADR-064-harness-agnostic-cognitive-os.md Surface 4,
           manifests/harness-driver-capabilities.yaml bare_cli entry.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, ClassVar, Dict, List, Optional

from .base import (
    CanonicalEvent,
    HarnessAdapter,
    HarnessName,
    ParseError,
    SessionEnd,
    SessionStart,
    ToolUseEnd,
    ToolUseStart,
    UserPromptSubmit,
    now_epoch,
)


# Env-var prefixes that identify other harnesses; used in fallback detection.
_OTHER_HARNESS_PREFIXES = (
    "CLAUDE_CODE_",
    "CLAUDE_PROJECT_DIR",      # CC sets this
    "CODEX_",
    "AIDER_",
    "CURSOR_",
)

# Canonical event names this adapter handles from the ``event`` key.
_SUPPORTED_EVENTS: frozenset[str] = frozenset(
    {
        "session_start",
        "user_prompt_submit",
        "tool_use_start",
        "tool_use_end",
        "session_end",
    }
)


def _other_harness_active() -> bool:
    """True when env vars identify a non-bare harness is already running."""
    for key in os.environ:
        for prefix in _OTHER_HARNESS_PREFIXES:
            if key.startswith(prefix):
                return True
    return False


class BareCliAdapter(HarnessAdapter):
    """Adapter for cos-agent / cos-skill bare-CLI invocations (ADR-064 Surface 4)."""

    name: ClassVar[HarnessName] = HarnessName.BARE_CLI
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    # ── Capability matrix (matches manifests/harness-driver-capabilities.yaml) ─

    CAPABILITY_MATRIX: ClassVar[Dict[str, str]] = {
        "SessionStart":       "supported",
        "UserPromptSubmit":   "supported",
        "ToolUseStart":       "supported",
        "ToolUseEnd":         "supported",
        "SessionEnd":         "supported",
        "PreCompact":         "unsupported",  # no native compaction in bare CLI
        "SubagentStart":      "unsupported",
        "TeammateIdle":       "unsupported",
        "TaskCreated":        "unsupported",
        "TaskCompleted":      "unsupported",
    }

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        """Return BARE_CLI when payload is explicitly tagged or no other harness is active."""
        if not isinstance(raw, dict):
            return None

        # Explicit tag wins first.
        if raw.get("harness") == cls.name.value:
            return cls.name

        # Env-tag from cos-agent/cos-skill invocations.
        if os.environ.get("COGNITIVE_OS_HARNESS", "").strip() == cls.name.value:
            return cls.name

        # Fallback: we own the payload if no other harness env vars are set
        # AND the payload looks like a valid cos canonical event.
        if not _other_harness_active() and "event" in raw:
            return cls.name

        return None

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        """Translate one bare-CLI payload into 0+ canonical events."""
        if not isinstance(raw, dict):
            return []

        event_name = str(raw.get("event") or raw.get("event_type") or "")
        session_id = self._session_id(raw)

        if not event_name or event_name not in _SUPPORTED_EVENTS:
            if not event_name:
                reason = "missing_event_field"
            else:
                reason = "unsupported_bare_cli_event"
            return [
                ParseError(
                    source_line=_safe_json(raw),
                    adapter=self.name.value,
                    reason=reason,
                    session_id=session_id,
                )
            ]

        if event_name == "session_start":
            return [self._session_start(raw, session_id)]
        if event_name == "user_prompt_submit":
            return [self._user_prompt(raw, session_id)]
        if event_name == "tool_use_start":
            return [self._tool_start(raw, session_id)]
        if event_name == "tool_use_end":
            return [self._tool_end(raw, session_id)]
        if event_name == "session_end":
            return [self._session_end(raw, session_id)]

        # Unreachable (covered by _SUPPORTED_EVENTS guard above) but defensive.
        return []

    # ── Private builders ───────────────────────────────────────────────────────

    def _session_id(self, raw: Dict[str, Any]) -> Optional[str]:
        return (
            raw.get("session_id")
            or os.environ.get("COGNITIVE_OS_SESSION_ID")
            or os.environ.get("COS_AGENT_SESSION_ID")
        )

    def _session_start(self, raw: Dict[str, Any], session_id: Optional[str]) -> SessionStart:
        return SessionStart(
            session_id=session_id or "bare-cli-session",
            started_at=float(raw.get("started_at") or now_epoch()),
            harness=self.name.value,
            cwd=raw.get("cwd") or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd(),
            source=raw.get("source") or "bare_cli",
            version=raw.get("version"),
        )

    def _session_end(self, raw: Dict[str, Any], session_id: Optional[str]) -> SessionEnd:
        return SessionEnd(
            session_id=session_id or "bare-cli-session",
            ended_at=float(raw.get("ended_at") or now_epoch()),
            harness=self.name.value,
            exit_status=str(raw.get("exit_status") or "success"),
            duration_ms=_as_int(raw.get("duration_ms")),
        )

    def _user_prompt(self, raw: Dict[str, Any], session_id: Optional[str]) -> UserPromptSubmit:
        prompt = raw.get("prompt") or raw.get("prompt_summary") or ""
        return UserPromptSubmit(
            session_id=session_id,
            submitted_at=float(raw.get("submitted_at") or now_epoch()),
            harness=self.name.value,
            prompt_summary=_summarize(prompt),
            prompt_hash=_hash(str(prompt)) if prompt else None,
        )

    def _tool_start(self, raw: Dict[str, Any], session_id: Optional[str]) -> ToolUseStart:
        return ToolUseStart(
            agent_id=str(raw.get("agent_id") or raw.get("tool_call_id") or _hash(_safe_json(raw))),
            tool_name=str(raw.get("tool_name") or "unknown"),
            started_at=float(raw.get("started_at") or now_epoch()),
            tool_input_summary=_summarize(raw.get("tool_input")),
            session_id=session_id,
        )

    def _tool_end(self, raw: Dict[str, Any], session_id: Optional[str]) -> ToolUseEnd:
        exit_code = raw.get("exit_code")
        if exit_code is not None:
            status = "success" if exit_code == 0 else "error"
        else:
            status = str(raw.get("exit_status") or "unknown")
        return ToolUseEnd(
            agent_id=str(raw.get("agent_id") or raw.get("tool_call_id") or _hash(_safe_json(raw))),
            tool_name=str(raw.get("tool_name") or "unknown"),
            ended_at=float(raw.get("ended_at") or now_epoch()),
            duration_ms=_as_int(raw.get("duration_ms")),
            exit_status=status,
            session_id=session_id,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _summarize(value: Any, limit: int = 160) -> Optional[str]:
    if value is None:
        return None
    text = value if isinstance(value, str) else _safe_json(value)
    return text[:limit]


def _hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)[:500]
    except TypeError:
        return str(value)[:500]


def _as_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
