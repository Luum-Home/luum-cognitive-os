"""Codex adapter backed by live Codex Desktop session payloads (ADR-081).

Codex is both a projected hook driver (``.codex/hooks.json``) and a native
runtime that records session events under ``~/.codex/sessions``.  This adapter
normalizes those native payloads into the same canonical event stream consumed
by the rest of Cognitive OS.

Supported inputs:
- Codex Desktop session JSONL rows: ``session_meta``, ``response_item`` and
  ``event_msg`` wrappers with a nested ``payload.type``.
- Codex hook payloads that use Claude-like top-level ``hook_event`` names.

Fixtures live in ``tests/fixtures/codex-live-session/`` and are sanitized from
an actual Codex Desktop session on 2026-04-30.  They intentionally replace
absolute paths and long prompt bodies with placeholders so the repository never
stores operator-specific filesystem paths or conversation content.
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


class CodexAdapter(HarnessAdapter):
    """Adapter for OpenAI Codex Desktop / CLI native event payloads."""

    name: ClassVar[HarnessName] = HarnessName.CODEX
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    SUPPORTED_EVENTS: ClassVar[frozenset[str]] = frozenset(
        {
            "session_meta",
            "task_started",
            "task_complete",
            "message",
            "function_call",
            "function_call_output",
            "exec_command_end",
            "mcp_tool_call_end",
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SessionEnd",
        }
    )

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        if not isinstance(raw, dict):
            return None
        if raw.get("type") in {"session_meta", "response_item", "event_msg"}:
            if raw.get("type") == "session_meta":
                return cls.name
            payload = raw.get("payload")
            if isinstance(payload, dict) and cls._payload_kind(payload) in cls.SUPPORTED_EVENTS:
                return cls.name
        if raw.get("harness") == cls.name.value:
            return cls.name
        if raw.get("hook_event") in cls.SUPPORTED_EVENTS:
            return cls.name
        # Codex hook rows often carry Codex env/session fields without a
        # wrapper when invoked through projected .codex/hooks.json commands.
        if raw.get("codex_session_id") or raw.get("codex_thread_id"):
            return cls.name
        return None

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        if not isinstance(raw, dict):
            return []

        # Codex hook stdin payloads: Claude-like event names, but Codex-native
        # event coverage.  Keep this branch first so hook events do not get
        # mistaken for session log wrappers.
        if "hook_event" in raw:
            return self._parse_hook_event(raw)

        payload = raw.get("payload") if raw.get("type") in {"session_meta", "response_item", "event_msg"} else raw
        if not isinstance(payload, dict):
            return []

        kind = "session_meta" if raw.get("type") == "session_meta" else self._payload_kind(payload)
        if kind not in self.SUPPORTED_EVENTS:
            return [
                ParseError(
                    source_line=_safe_json(payload),
                    adapter=self.name.value,
                    reason="unsupported_codex_event",
                    session_id=self._session_id(raw, payload),
                )
            ]

        if raw.get("type") == "session_meta" or kind == "session_meta":
            return [self._session_start(raw, payload)]
        if kind == "task_started":
            return [self._session_start(raw, payload)]
        if kind == "task_complete":
            return [self._session_end(raw, payload)]
        if kind == "message" and payload.get("role") == "user":
            return [self._user_prompt(raw, payload)]
        if kind == "function_call":
            return [self._tool_start(raw, payload)]
        if kind in {"function_call_output", "exec_command_end", "mcp_tool_call_end"}:
            return [self._tool_end(raw, payload)]
        return []

    @staticmethod
    def _payload_kind(payload: Dict[str, Any]) -> str:
        return str(payload.get("type") or payload.get("hook_event") or "")

    def _session_id(self, raw: Dict[str, Any], payload: Dict[str, Any]) -> Optional[str]:
        return (
            payload.get("id")
            or payload.get("turn_id")
            or raw.get("session_id")
            or payload.get("session_id")
            or os.environ.get("COGNITIVE_OS_SESSION_ID")
            or os.environ.get("CODEX_SESSION_ID")
            or os.environ.get("CODEX_THREAD_ID")
        )

    def _session_start(self, raw: Dict[str, Any], payload: Dict[str, Any]) -> SessionStart:
        session_id = self._session_id(raw, payload) or "codex-session"
        return SessionStart(
            session_id=session_id,
            started_at=_timestamp(raw, payload),
            harness=self.name.value,
            cwd=payload.get("cwd") or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR"),
            source=payload.get("source") or payload.get("type"),
            version=payload.get("cli_version"),
        )

    def _session_end(self, raw: Dict[str, Any], payload: Dict[str, Any]) -> SessionEnd:
        return SessionEnd(
            session_id=self._session_id(raw, payload) or "codex-session",
            ended_at=float(payload.get("completed_at") or _timestamp(raw, payload)),
            harness=self.name.value,
            exit_status="success",
            duration_ms=_as_int(payload.get("duration_ms")),
        )

    def _user_prompt(self, raw: Dict[str, Any], payload: Dict[str, Any]) -> UserPromptSubmit:
        text = _message_text(payload)
        return UserPromptSubmit(
            session_id=self._session_id(raw, payload) or os.environ.get("CODEX_THREAD_ID"),
            submitted_at=_timestamp(raw, payload),
            harness=self.name.value,
            prompt_summary=_summarize(text),
            prompt_hash=_hash(text),
        )

    def _tool_start(self, raw: Dict[str, Any], payload: Dict[str, Any]) -> ToolUseStart:
        name = _tool_name(payload)
        return ToolUseStart(
            agent_id=str(payload.get("call_id") or payload.get("id") or _hash(_safe_json(payload))),
            tool_name=name,
            started_at=_timestamp(raw, payload),
            tool_input_summary=_summarize(payload.get("arguments")),
            session_id=self._session_id(raw, payload) or os.environ.get("CODEX_THREAD_ID"),
        )

    def _tool_end(self, raw: Dict[str, Any], payload: Dict[str, Any]) -> ToolUseEnd:
        status = "success"
        if payload.get("exit_code") not in (None, 0):
            status = "error"
        if payload.get("result") and isinstance(payload["result"], dict) and "Err" in payload["result"]:
            status = "error"
        duration = payload.get("duration")
        duration_ms = None
        if isinstance(duration, dict):
            duration_ms = _as_int(duration.get("secs"), 0) * 1000 + _as_int(duration.get("nanos"), 0) // 1_000_000
        else:
            duration_ms = _as_int(payload.get("duration_ms"))
        return ToolUseEnd(
            agent_id=str(payload.get("call_id") or payload.get("process_id") or _hash(_safe_json(payload))),
            tool_name=_tool_name(payload),
            ended_at=_timestamp(raw, payload),
            duration_ms=duration_ms,
            exit_status=status,
            session_id=self._session_id(raw, payload) or os.environ.get("CODEX_THREAD_ID"),
        )

    def _parse_hook_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        event = str(raw.get("hook_event") or "")
        session_id = raw.get("session_id") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_THREAD_ID")
        if event == "SessionStart":
            return [SessionStart(session_id=session_id or "codex-session", started_at=now_epoch(), harness=self.name.value, cwd=raw.get("cwd") or os.environ.get("CODEX_PROJECT_DIR"), source="codex_hook")]
        if event == "UserPromptSubmit":
            prompt = raw.get("prompt") or raw.get("message") or ""
            tool_input = raw.get("tool_input")
            if not prompt and isinstance(tool_input, dict):
                prompt = tool_input.get("prompt") or tool_input.get("message") or ""
            return [UserPromptSubmit(session_id=session_id, submitted_at=now_epoch(), harness=self.name.value, prompt_summary=_summarize(prompt), prompt_hash=_hash(str(prompt)))]
        if event in {"Stop", "SessionEnd"}:
            return [SessionEnd(session_id=session_id or "codex-session", ended_at=now_epoch(), harness=self.name.value, exit_status="success")]
        if event in {"PreToolUse", "PostToolUse"}:
            tool = str(raw.get("tool_name") or "")
            if tool and tool != "Bash":
                return [ParseError(source_line=_safe_json(raw), adapter=self.name.value, reason="codex_tool_coverage_gap", session_id=session_id)]
            if event == "PreToolUse":
                return [self._tool_start(raw, {"type": "function_call", "call_id": raw.get("tool_use_id") or raw.get("call_id") or "codex-bash", "name": "Bash", "arguments": _safe_json(raw.get("tool_input", {}))})]
            return [ToolUse(agent_id=str(raw.get("tool_use_id") or raw.get("call_id") or "codex-bash"), tool_name="Bash", started_at=now_epoch(), exit_status=_hook_exit_status(raw), session_id=session_id)]
        return [ParseError(source_line=_safe_json(raw), adapter=self.name.value, reason="unsupported_codex_hook_event", session_id=session_id)]


def _timestamp(raw: Dict[str, Any], payload: Dict[str, Any]) -> float:
    for value in (payload.get("started_at"), payload.get("completed_at")):
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
    return str(payload.get("type") or "codex_tool")


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


def _hook_exit_status(raw: Dict[str, Any]) -> str:
    if raw.get("exit_code") not in (None, 0):
        return "error"
    if raw.get("is_error") or raw.get("error"):
        return "error"
    return "success"
