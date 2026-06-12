"""OpenCode adapter backed by OpenCode plugin payloads and session logs (ADR-064).

OpenCode exposes a native plugin API that fires on lifecycle events:
- session.created
- session.idle
- tui.prompt.append
- tool.execute.before
- tool.execute.after
- experimental.session.compacting (legacy: session.compacted)

The cos-primitive-guard.js plugin (packages/opencode-adapter/plugins/cos-primitive-guard.js)
projects COS hooks from .opencode/cos-hooks.json onto these events and emits
primitive-interventions rows to .cognitive-os/metrics/primitive-interventions.jsonl.

This adapter normalizes OpenCode plugin payloads and session logs into the
canonical event stream consumed by the rest of Cognitive OS.

Fixtures live in tests/fixtures/opencode-live-session/ (sanitized from actual
OpenCode sessions).
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
    ToolUse,
    ToolUseEnd,
    ToolUseStart,
    UserPromptSubmit,
    now_epoch,
)


class OpencodeAdapter(HarnessAdapter):
    """Adapter for OpenCode native plugin payloads and session logs."""

    name: ClassVar[HarnessName] = HarnessName.OPENCODE
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    #: Canonical event types this adapter can produce.
    SUPPORTED_EVENTS: ClassVar[frozenset[str]] = frozenset(
        {
            "session_start",
            "user_prompt_submit",
            "session_end",
            "tool_use",
            "tool_use_start",
            "tool_use_end",
            "parse_error",
        }
    )

    #: OpenCode native/plugin event kinds accepted as adapter input.
    SUPPORTED_INPUT_EVENTS: ClassVar[frozenset[str]] = frozenset(
        {
            "session.created",
            "session.idle",
            "tui.prompt.append",
            "tool.execute.before",
            "tool.execute.after",
            "experimental.session.compacting",
            "session.compacted",
            "primitive_intervention",
        }
    )

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        if not isinstance(raw, dict):
            return None
        # OpenCode plugin primitive-intervention rows
        if raw.get("schema_version") == "primitive-intervention.v1":
            if raw.get("harness") == cls.name.value:
                return cls.name
        # OpenCode plugin hook payloads
        hook_event = raw.get("hook_event") or raw.get("opencode_event") or raw.get("type")
        if hook_event in cls.SUPPORTED_INPUT_EVENTS:
            return cls.name
        # OpenCode session log payloads (if available)
        if raw.get("type") in {"session_meta", "turn_meta"}:
            return cls.name
        # Harness hint from env
        if raw.get("harness") == cls.name.value:
            return cls.name
        return None

    @classmethod
    def supports_payload(cls, raw: Dict[str, Any]) -> bool:
        """Return True when this OpenCode input kind is explicitly supported."""
        if raw.get("schema_version") == "primitive-intervention.v1":
            return raw.get("harness") == cls.name.value
        hook_event = raw.get("hook_event") or raw.get("opencode_event") or raw.get("type")
        if hook_event:
            return str(hook_event) in cls.SUPPORTED_INPUT_EVENTS
        if raw.get("type") in {"session_meta", "turn_meta"}:
            return True
        return False

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        if not isinstance(raw, dict):
            return []

        # Primitive intervention rows from cos-primitive-guard.js plugin
        if raw.get("schema_version") == "primitive-intervention.v1":
            return self._parse_primitive_intervention(raw)

        # Plugin hook payloads
        hook_event = raw.get("hook_event") or raw.get("opencode_event") or raw.get("type")
        if hook_event:
            return self._parse_plugin_hook(raw, hook_event)

        # Session log payloads (if OpenCode exposes them)
        if raw.get("type") in {"session_meta", "turn_meta"}:
            return self._parse_session_log(raw)

        return [
            ParseError(
                source_line=_safe_json(raw),
                adapter=self.name.value,
                reason="unsupported_opencode_event",
                session_id=self._session_id(raw),
            )
        ]

    def _parse_primitive_intervention(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        """Parse primitive-intervention.v1 rows emitted by cos-primitive-guard.js."""
        # These are already canonical evidence rows — just extract metadata
        # for correlation. The actual enforcement decision is in the row.
        session_id = (
            raw.get("session_id")
            or os.environ.get("COGNITIVE_OS_SESSION_ID")
            or os.environ.get("OPENCODE_SESSION_ID")
            or "opencode-session"
        )
        # Emit a parse marker so the canonical stream records that an
        # intervention evidence row was observed.
        primitive_id = raw.get("primitive_id")
        action_kind = raw.get("action_kind")
        reason_code = raw.get("reason_code")
        target_ref = raw.get("target_ref")
        reason = f"primitive_intervention:{primitive_id}:{action_kind}:{reason_code}:{target_ref}"
        return [
            ParseError(
                source_line=_safe_json(raw),
                adapter=self.name.value,
                reason=reason,
                session_id=session_id,
            )
        ]

    def _parse_plugin_hook(self, raw: Dict[str, Any], hook_event: str) -> List[CanonicalEvent]:
        """Parse OpenCode plugin hook payloads."""
        session_id = (
            raw.get("session_id")
            or os.environ.get("COGNITIVE_OS_SESSION_ID")
            or os.environ.get("OPENCODE_SESSION_ID")
            or "opencode-session"
        )

        if hook_event == "session.created":
            return [
                SessionStart(
                    session_id=session_id,
                    started_at=now_epoch(),
                    harness=self.name.value,
                    cwd=raw.get("cwd") or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("OPENCODE_PROJECT_DIR"),
                    source="opencode_plugin",
                    version=raw.get("version"),
                )
            ]

        if hook_event == "tui.prompt.append":
            payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
            prompt = raw.get("prompt") or raw.get("message") or raw.get("text") or payload.get("prompt") or payload.get("message") or payload.get("text") or ""
            return [
                UserPromptSubmit(
                    session_id=session_id,
                    submitted_at=now_epoch(),
                    harness=self.name.value,
                    prompt_summary=_summarize(prompt),
                    prompt_hash=_hash(str(prompt)),
                )
            ]

        if hook_event in {"session.idle", "session.compacted", "experimental.session.compacting"}:
            return [
                SessionEnd(
                    session_id=session_id,
                    ended_at=now_epoch(),
                    harness=self.name.value,
                    exit_status="success",
                    duration_ms=None,
                )
            ]

        if hook_event == "tool.execute.before":
            tool_name = str(raw.get("tool") or raw.get("tool_name") or "unknown")
            return [
                ToolUseStart(
                    agent_id=str(raw.get("tool_use_id") or raw.get("call_id") or _hash(_safe_json(raw))),
                    tool_name=tool_name,
                    started_at=now_epoch(),
                    tool_input_summary=_summarize(raw.get("args")),
                    session_id=session_id,
                )
            ]

        if hook_event == "tool.execute.after":
            tool_name = str(raw.get("tool") or raw.get("tool_name") or "unknown")
            status = "success"
            payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
            exit_code = raw.get("exit_code", payload.get("exit_code"))
            if exit_code not in (None, 0):
                status = "error"
            if raw.get("is_error") or raw.get("error"):
                status = "error"
            return [
                ToolUseEnd(
                    agent_id=str(raw.get("tool_use_id") or raw.get("call_id") or _hash(_safe_json(raw))),
                    tool_name=tool_name,
                    ended_at=now_epoch(),
                    duration_ms=None,
                    exit_status=status,
                    session_id=session_id,
                )
            ]

        return [
            ParseError(
                source_line=_safe_json(raw),
                adapter=self.name.value,
                reason="unsupported_opencode_plugin_event",
                session_id=session_id,
            )
        ]

    def _parse_session_log(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        """Parse OpenCode session log payloads (if available)."""
        payload = raw.get("payload") if raw.get("type") in {"session_meta", "turn_meta"} else raw
        if not isinstance(payload, dict):
            return []

        kind = str(payload.get("type") or payload.get("hook_event") or "")
        if kind not in self.SUPPORTED_INPUT_EVENTS:
            return []

        session_id = self._session_id(raw, payload)
        events: List[CanonicalEvent] = []

        if kind in {"session_meta", "session.created"}:
            events.append(
                SessionStart(
                    session_id=session_id,
                    started_at=_timestamp(raw, payload),
                    harness=self.name.value,
                    cwd=payload.get("cwd") or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("OPENCODE_PROJECT_DIR"),
                    source=payload.get("source") or payload.get("type"),
                    version=payload.get("cli_version"),
                )
            )
        elif kind in {"session.idle", "turn_meta"} and payload.get("completed"):
            events.append(
                SessionEnd(
                    session_id=session_id,
                    ended_at=_timestamp(raw, payload),
                    harness=self.name.value,
                    exit_status="success",
                    duration_ms=_as_int(payload.get("duration_ms")),
                )
            )
        elif kind == "tui.prompt.append":
            text = _message_text(payload)
            events.append(
                UserPromptSubmit(
                    session_id=session_id,
                    submitted_at=_timestamp(raw, payload),
                    harness=self.name.value,
                    prompt_summary=_summarize(text),
                    prompt_hash=_hash(text),
                )
            )
        elif kind == "tool.execute.before":
            name = _tool_name(payload)
            events.append(
                ToolUseStart(
                    agent_id=str(payload.get("call_id") or payload.get("id") or _hash(_safe_json(payload))),
                    tool_name=name,
                    started_at=_timestamp(raw, payload),
                    tool_input_summary=_summarize(payload.get("arguments")),
                    session_id=session_id,
                )
            )
        elif kind == "tool.execute.after":
            status = "success"
            if payload.get("exit_code") not in (None, 0):
                status = "error"
            if payload.get("result") and isinstance(payload["result"], dict) and "Err" in payload["result"]:
                status = "error"
            duration = payload.get("duration")
            duration_ms = None
            if isinstance(duration, dict):
                duration_ms = (_as_int(duration.get("secs"), 0) or 0) * 1000 + (_as_int(duration.get("nanos"), 0) or 0) // 1_000_000
            else:
                duration_ms = _as_int(payload.get("duration_ms"))
            events.append(
                ToolUseEnd(
                    agent_id=str(payload.get("call_id") or payload.get("process_id") or _hash(_safe_json(payload))),
                    tool_name=_tool_name(payload),
                    ended_at=_timestamp(raw, payload),
                    duration_ms=duration_ms,
                    exit_status=status,
                    session_id=session_id,
                )
            )

        return events

    def _session_id(self, raw: Dict[str, Any], payload: Optional[Dict[str, Any]] = None) -> Optional[str]:
        payload = payload or raw
        return (
            payload.get("id")
            or payload.get("turn_id")
            or raw.get("session_id")
            or payload.get("session_id")
            or os.environ.get("COGNITIVE_OS_SESSION_ID")
            or os.environ.get("OPENCODE_SESSION_ID")
        )


def _timestamp(raw: Dict[str, Any], payload: Dict[str, Any]) -> float:
    for value in (payload.get("started_at"), payload.get("completed_at"), payload.get("timestamp")):
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return now_epoch()


def _message_text(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    content = payload.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
    elif isinstance(content, str):
        parts.append(content)
    return "\n".join(parts)


def _tool_name(payload: Dict[str, Any]) -> str:
    if payload.get("name"):
        namespace = payload.get("namespace")
        return f"{namespace}.{payload['name']}" if namespace else str(payload["name"])
    invocation = payload.get("invocation")
    if isinstance(invocation, dict):
        server = invocation.get("server")
        tool = invocation.get("tool")
        if server and tool:
            return f"mcp.{server}.{tool}"
    command = payload.get("command")
    if isinstance(command, list) and command:
        return "exec_command"
    return str(payload.get("type") or "opencode_tool")


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

# Backward-compatible public name used by dispatch.py and existing imports.
OpenCodeAdapter = OpencodeAdapter
