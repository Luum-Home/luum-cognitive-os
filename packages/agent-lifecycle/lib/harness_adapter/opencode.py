"""OpenCode harness adapter for native plugin/event payloads.

OpenCode project plugins expose lifecycle and tool events such as
``session.created``, ``session.idle``, ``tui.prompt.append``,
``tool.execute.before`` and ``tool.execute.after``. This adapter normalizes
those payloads into the Cognitive OS canonical event stream without depending
on raw prompt or command content.
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


_SUPPORTED_NATIVE_EVENTS = frozenset(
    {
        "session.created",
        "session.idle",
        "session.compacted",
        "experimental.session.compacting",
        "tui.prompt.append",
        "tool.execute.before",
        "tool.execute.after",
    }
)


class OpenCodeAdapter(HarnessAdapter):
    """Adapter for OpenCode plugin event payloads."""

    name: ClassVar[HarnessName] = HarnessName.OPENCODE
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        if not isinstance(raw, dict):
            return None
        if raw.get("harness") == cls.name.value:
            return cls.name
        if raw.get("opencode") is True or raw.get("opencode_session_id"):
            return cls.name
        event = _native_event(raw)
        if event in _SUPPORTED_NATIVE_EVENTS:
            return cls.name
        return None

    @classmethod
    def supports_payload(cls, raw: Dict[str, Any]) -> bool:
        return _native_event(raw) in _SUPPORTED_NATIVE_EVENTS

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        event = _native_event(raw)
        session_id = _session_id(raw)
        payload = _payload(raw)

        if event == "session.created":
            return [
                SessionStart(
                    session_id=session_id or "opencode-session",
                    started_at=_timestamp(raw),
                    harness=self.name.value,
                    cwd=_cwd(raw),
                    source="opencode_plugin",
                    version=_version(raw),
                )
            ]
        if event == "session.idle":
            return [
                SessionEnd(
                    session_id=session_id or "opencode-session",
                    ended_at=_timestamp(raw),
                    harness=self.name.value,
                    exit_status=str(raw.get("exit_status") or payload.get("status") or "success"),
                    duration_ms=_as_int(raw.get("duration_ms") or payload.get("duration_ms")),
                )
            ]
        if event in {"session.compacted", "experimental.session.compacting"}:
            return [
                ParseError(
                    source_line=_safe_json({"type": event, "session_id": session_id}),
                    adapter=self.name.value,
                    reason="opencode_compaction_event_limited",
                    session_id=session_id,
                )
            ]
        if event == "tui.prompt.append":
            text = str(payload.get("prompt") or payload.get("text") or raw.get("prompt") or "")
            return [
                UserPromptSubmit(
                    session_id=session_id,
                    submitted_at=_timestamp(raw),
                    harness=self.name.value,
                    prompt_summary=_summarize(text),
                    prompt_hash=_hash(text),
                )
            ]
        if event == "tool.execute.before":
            return [
                ToolUseStart(
                    agent_id=_tool_id(raw),
                    tool_name=_tool_name(raw),
                    started_at=_timestamp(raw),
                    tool_input_summary=_summarize(_safe_json(_tool_args(raw))),
                    session_id=session_id,
                )
            ]
        if event == "tool.execute.after":
            return [
                ToolUseEnd(
                    agent_id=_tool_id(raw),
                    tool_name=_tool_name(raw),
                    ended_at=_timestamp(raw),
                    duration_ms=_as_int(raw.get("duration_ms") or payload.get("duration_ms")),
                    exit_status=_exit_status(raw),
                    session_id=session_id,
                )
            ]
        return [
            ParseError(
                source_line=_safe_json(raw),
                adapter=self.name.value,
                reason="unsupported_opencode_event",
                session_id=session_id,
            )
        ]


def _payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    event = raw.get("event")
    if isinstance(event, dict):
        props = event.get("properties")
        if isinstance(props, dict):
            return props
    for key in ("payload", "input", "output", "data"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return raw


def _native_event(raw: Dict[str, Any]) -> str:
    for key in ("type", "event_type", "opencode_event"):
        value = raw.get(key)
        if isinstance(value, str):
            return value
    event = raw.get("event")
    if isinstance(event, str):
        return event
    if isinstance(event, dict):
        value = event.get("type")
        if isinstance(value, str):
            return value
    return ""


def _session_id(raw: Dict[str, Any]) -> Optional[str]:
    payload = _payload(raw)
    event = raw.get("event") if isinstance(raw.get("event"), dict) else {}
    event_props = event.get("properties", {}) if isinstance(event, dict) else {}
    info = event_props.get("info", {}) if isinstance(event_props.get("info"), dict) else {}
    return (
        raw.get("session_id")
        or raw.get("opencode_session_id")
        or payload.get("session_id")
        or payload.get("sessionID")
        or payload.get("sessionId")
        or info.get("id")
        or os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("OPENCODE_SESSION_ID")
    )


def _cwd(raw: Dict[str, Any]) -> Optional[str]:
    payload = _payload(raw)
    return raw.get("cwd") or payload.get("cwd") or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("OPENCODE_PROJECT_DIR")


def _version(raw: Dict[str, Any]) -> Optional[str]:
    payload = _payload(raw)
    return raw.get("version") or payload.get("version")


def _timestamp(raw: Dict[str, Any]) -> float:
    payload = _payload(raw)
    for value in (raw.get("timestamp"), raw.get("ts"), payload.get("timestamp"), payload.get("ts")):
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass
    return now_epoch()


def _tool_name(raw: Dict[str, Any]) -> str:
    payload = _payload(raw)
    tool = raw.get("tool") or payload.get("tool") or payload.get("name")
    if isinstance(tool, dict):
        return str(tool.get("name") or tool.get("id") or "opencode_tool")
    return str(tool or "opencode_tool").lower()


def _tool_args(raw: Dict[str, Any]) -> Any:
    payload = _payload(raw)
    return raw.get("args") or payload.get("args") or payload.get("input") or {}


def _tool_id(raw: Dict[str, Any]) -> str:
    payload = _payload(raw)
    value = raw.get("tool_use_id") or raw.get("id") or payload.get("tool_use_id") or payload.get("id")
    if value:
        return str(value)
    return _hash(_safe_json({"event": _native_event(raw), "tool": _tool_name(raw), "args": _tool_args(raw)}))


def _exit_status(raw: Dict[str, Any]) -> str:
    payload = _payload(raw)
    code = raw.get("exit_code") or payload.get("exit_code")
    if code not in (None, 0, "0"):
        return "error"
    if raw.get("error") or payload.get("error"):
        return "error"
    return str(raw.get("exit_status") or payload.get("status") or "success")


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
