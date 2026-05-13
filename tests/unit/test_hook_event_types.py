"""Unit tests for lib.hook_event_types (ADR-290 Pattern 2)."""
from __future__ import annotations

import pytest

from lib.hook_event_types import (
    HookPayloadError,
    PostToolUseEvent,
    PreToolUseEvent,
    SessionStartEvent,
    StopEvent,
    SubagentStartEvent,
    parse_event,
)


def _common(name: str) -> dict:
    return {
        "hook_event_name": name,
        "session_id": "sess-1",
        "timestamp": "2026-05-13T10:00:00Z",
    }


def test_session_start_parses():
    payload = _common("SessionStart") | {"source": "startup"}
    event = parse_event(payload)
    assert isinstance(event, SessionStartEvent)
    assert event.source == "startup"
    assert event.session_id == "sess-1"


def test_pre_tool_use_parses_with_tool_input():
    payload = _common("PreToolUse") | {
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/x"},
    }
    event = parse_event(payload)
    assert isinstance(event, PreToolUseEvent)
    assert event.tool_name == "Read"
    assert event.tool_input == {"file_path": "/tmp/x"}


def test_post_tool_use_roundtrip_preserves_info():
    payload = _common("PostToolUse") | {
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_output": "file.txt\n",
    }
    event = parse_event(payload)
    assert isinstance(event, PostToolUseEvent)
    roundtrip = event.to_dict()
    assert roundtrip["tool_name"] == "Bash"
    assert roundtrip["tool_output"] == "file.txt\n"
    assert roundtrip["tool_input"] == {"command": "ls"}


def test_stop_event_parses():
    payload = _common("Stop") | {"stop_reason": "end_turn"}
    event = parse_event(payload)
    assert isinstance(event, StopEvent)
    assert event.stop_reason == "end_turn"


def test_subagent_start_requires_agent_type():
    payload = _common("SubagentStart")  # missing agent_type
    with pytest.raises(HookPayloadError, match="agent_type"):
        parse_event(payload)

    payload = _common("SubagentStart") | {
        "agent_type": "general-purpose",
        "parent_session_id": "parent-1",
    }
    event = parse_event(payload)
    assert isinstance(event, SubagentStartEvent)
    assert event.agent_type == "general-purpose"
    assert event.parent_session_id == "parent-1"


def test_missing_common_field_raises():
    payload = {"hook_event_name": "Stop", "session_id": "x"}  # no timestamp
    with pytest.raises(HookPayloadError, match="timestamp"):
        parse_event(payload)


def test_unknown_event_name_raises():
    payload = _common("DoesNotExist")
    with pytest.raises(HookPayloadError, match="unknown hook_event_name"):
        parse_event(payload)


def test_non_dict_payload_raises():
    with pytest.raises(HookPayloadError):
        parse_event("not a dict")  # type: ignore[arg-type]


def test_extra_unknown_fields_are_ignored():
    """Forward compatibility — unknown payload fields must not error out."""
    payload = _common("Stop") | {"stop_reason": "x", "future_field": 999}
    event = parse_event(payload)
    assert isinstance(event, StopEvent)
    assert event.stop_reason == "x"


def test_pre_tool_use_missing_tool_name_raises():
    payload = _common("PreToolUse")
    with pytest.raises(HookPayloadError, match="tool_name"):
        parse_event(payload)


def test_parse_pre_tool_use_event_returns_typed_dataclass():
    """Original stub test, preserved."""
    event = parse_event(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "s1",
            "timestamp": "2026-05-13T00:00:00Z",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest"},
        }
    )
    assert isinstance(event, PreToolUseEvent)
    assert event.tool_name == "Bash"
    assert event.tool_input["command"] == "pytest"
