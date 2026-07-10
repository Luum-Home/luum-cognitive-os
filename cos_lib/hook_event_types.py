# SCOPE: os-only
"""Typed hook event registry (ADR-290 Pattern 2).

Claude Code emits JSON payloads for hook lifecycle events
(``SessionStart``, ``PreToolUse``, ``PostToolUse``, ``Stop``,
``SubagentStart``). Today the 237 hook scripts in this repository parse these
payloads as untyped dicts with manual ``.get()`` key fishing, which makes
typos like ``tool_inpiut`` silently degrade to ``None``.

This module is the canonical schema. Hooks adopt it opportunistically; no
existing hook is rewritten by this ADR.

Public API
----------
- :class:`HookEvent`              — common base.
- :class:`SessionStartEvent`      — ``hook_event_name == "SessionStart"``.
- :class:`PreToolUseEvent`        — ``hook_event_name == "PreToolUse"``.
- :class:`PostToolUseEvent`       — ``hook_event_name == "PostToolUse"``.
- :class:`StopEvent`              — ``hook_event_name == "Stop"``.
- :class:`SubagentStartEvent`     — ``hook_event_name == "SubagentStart"``.
- :func:`parse_event(payload)`    — dispatch a raw dict to its dataclass.
- :class:`HookPayloadError`       — raised for missing/unknown fields.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class HookPayloadError(ValueError):
    """Raised when a hook payload is missing required fields or has an unknown event name."""


@dataclass(frozen=True)
class HookEvent:
    """Common fields present on every hook event payload."""

    hook_event_name: str
    session_id: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SessionStartEvent(HookEvent):
    """Emitted once at the start of a Claude Code session."""

    source: str = ""  # e.g. "startup", "resume"


@dataclass(frozen=True)
class PreToolUseEvent(HookEvent):
    """Emitted before a tool call. ``tool_input`` is the raw arguments dict."""

    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PostToolUseEvent(HookEvent):
    """Emitted after a tool call. ``tool_output`` is the tool's structured result."""

    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_output: Any = None


@dataclass(frozen=True)
class StopEvent(HookEvent):
    """Emitted at the end of a turn (assistant stop)."""

    stop_reason: str = ""


@dataclass(frozen=True)
class SubagentStartEvent(HookEvent):
    """Emitted when a sub-agent is launched via the ``Agent`` tool."""

    agent_type: str = ""
    parent_session_id: str = ""


# Mapping of hook_event_name -> (dataclass, required-extra-fields)
_EVENT_REGISTRY: dict[str, tuple[type[HookEvent], tuple[str, ...]]] = {
    "SessionStart": (SessionStartEvent, ()),
    "PreToolUse": (PreToolUseEvent, ("tool_name",)),
    "PostToolUse": (PostToolUseEvent, ("tool_name",)),
    "Stop": (StopEvent, ()),
    "SubagentStart": (SubagentStartEvent, ("agent_type",)),
}

_COMMON_REQUIRED = ("hook_event_name", "session_id", "timestamp")


def parse_event(payload: dict[str, Any]) -> HookEvent:
    """Dispatch a raw hook payload to its typed dataclass.

    Raises :class:`HookPayloadError` if the payload is missing the common
    fields, missing the per-event required fields, or carries an unknown
    ``hook_event_name``.
    """
    if not isinstance(payload, dict):
        raise HookPayloadError(f"payload must be a dict, got {type(payload).__name__}")

    for required in _COMMON_REQUIRED:
        if required not in payload:
            raise HookPayloadError(f"hook payload missing required field: {required!r}")

    name = payload["hook_event_name"]
    if name not in _EVENT_REGISTRY:
        raise HookPayloadError(f"unknown hook_event_name: {name!r}")

    cls, extra_required = _EVENT_REGISTRY[name]
    for required in extra_required:
        if required not in payload:
            raise HookPayloadError(
                f"hook payload for {name!r} missing required field: {required!r}"
            )

    # Build kwargs by intersecting the dataclass fields with the payload.
    field_names = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    kwargs = {k: v for k, v in payload.items() if k in field_names}
    return cls(**kwargs)  # type: ignore[arg-type]
