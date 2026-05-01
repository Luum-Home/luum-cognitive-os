"""Unit tests for the bare-CLI harness adapter (ADR-064 Task 1.2)."""

from __future__ import annotations

import os

import pytest

from lib.harness_adapter.base import (
    HarnessName,
    ParseError,
    SessionEnd,
    SessionStart,
    ToolUseEnd,
    ToolUseStart,
    UserPromptSubmit,
)
from lib.harness_adapter.bare_cli import BareCliAdapter, _OTHER_HARNESS_PREFIXES


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any env vars that would trigger other-harness detection."""
    for key in list(os.environ):
        for prefix in _OTHER_HARNESS_PREFIXES:
            if key.startswith(prefix):
                monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)


# ── detect_harness ─────────────────────────────────────────────────────────────


class TestDetectHarness:
    def test_explicit_harness_tag_detected(self, monkeypatch):
        _clean_env(monkeypatch)
        payload = {"harness": "bare_cli", "event": "session_start"}
        assert BareCliAdapter.detect_harness(payload) == HarnessName.BARE_CLI

    def test_env_tag_detected(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "bare_cli")
        payload = {"event": "session_start"}
        assert BareCliAdapter.detect_harness(payload) == HarnessName.BARE_CLI

    def test_fallback_when_no_other_harness(self, monkeypatch):
        _clean_env(monkeypatch)
        payload = {"event": "session_start", "session_id": "abc"}
        assert BareCliAdapter.detect_harness(payload) == HarnessName.BARE_CLI

    def test_not_detected_when_claude_code_env_set(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc123")
        payload = {"event": "session_start"}
        assert BareCliAdapter.detect_harness(payload) is None

    def test_not_detected_when_codex_env_set(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("CODEX_SESSION_ID", "abc123")
        payload = {"event": "session_start"}
        assert BareCliAdapter.detect_harness(payload) is None

    def test_not_detected_for_non_dict(self, monkeypatch):
        _clean_env(monkeypatch)
        assert BareCliAdapter.detect_harness("not-a-dict") is None
        assert BareCliAdapter.detect_harness(None) is None
        assert BareCliAdapter.detect_harness([]) is None

    def test_not_detected_when_no_event_field_and_no_tag(self, monkeypatch):
        _clean_env(monkeypatch)
        # dict without "event" key and without harness tag — not ours
        payload = {"something": "else"}
        assert BareCliAdapter.detect_harness(payload) is None


# ── parse_event: SessionStart ──────────────────────────────────────────────────


class TestParseSessionStart:
    def test_basic_session_start(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "session_start",
            "session_id": "sid-001",
            "started_at": 1714500000.0,
            "cwd": "/workspace/proj",
        }
        events = adapter.parse_event(raw)
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, SessionStart)
        assert ev.session_id == "sid-001"
        assert ev.harness == "bare_cli"
        assert ev.cwd == "/workspace/proj"
        assert ev.started_at == 1714500000.0

    def test_session_start_defaults_cwd(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {"event": "session_start", "session_id": "s2"}
        events = adapter.parse_event(raw)
        ev = events[0]
        assert isinstance(ev, SessionStart)
        assert ev.cwd  # resolved from env or cwd(), must be non-empty


# ── parse_event: UserPromptSubmit ─────────────────────────────────────────────


class TestParseUserPromptSubmit:
    def test_prompt_hash_and_summary(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "user_prompt_submit",
            "session_id": "s1",
            "prompt": "List Python files in /src",
        }
        events = adapter.parse_event(raw)
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, UserPromptSubmit)
        assert ev.harness == "bare_cli"
        assert ev.prompt_hash is not None
        assert "List Python" in (ev.prompt_summary or "")

    def test_prompt_summary_truncated_to_160(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "user_prompt_submit",
            "session_id": "s1",
            "prompt": "x" * 300,
        }
        events = adapter.parse_event(raw)
        ev = events[0]
        assert isinstance(ev, UserPromptSubmit)
        assert len(ev.prompt_summary or "") == 160


# ── parse_event: ToolUseStart / ToolUseEnd ────────────────────────────────────


class TestParseToolUse:
    def test_tool_use_start(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "tool_use_start",
            "session_id": "s1",
            "tool_name": "read_file",
            "agent_id": "agent-42",
            "started_at": 1714500100.0,
            "tool_input": {"path": "/tmp/foo.txt"},
        }
        events = adapter.parse_event(raw)
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, ToolUseStart)
        assert ev.tool_name == "read_file"
        assert ev.agent_id == "agent-42"
        assert ev.session_id == "s1"

    def test_tool_use_end_success(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "tool_use_end",
            "session_id": "s1",
            "tool_name": "run_bash",
            "exit_code": 0,
            "duration_ms": 250,
            "agent_id": "agent-42",
        }
        events = adapter.parse_event(raw)
        ev = events[0]
        assert isinstance(ev, ToolUseEnd)
        assert ev.exit_status == "success"
        assert ev.duration_ms == 250

    def test_tool_use_end_error(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "tool_use_end",
            "session_id": "s1",
            "tool_name": "run_bash",
            "exit_code": 1,
            "agent_id": "agent-42",
        }
        events = adapter.parse_event(raw)
        ev = events[0]
        assert ev.exit_status == "error"


# ── parse_event: SessionEnd ───────────────────────────────────────────────────


class TestParseSessionEnd:
    def test_session_end(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {
            "event": "session_end",
            "session_id": "s1",
            "exit_status": "success",
            "duration_ms": 5000,
        }
        events = adapter.parse_event(raw)
        assert len(events) == 1
        ev = events[0]
        assert isinstance(ev, SessionEnd)
        assert ev.exit_status == "success"
        assert ev.duration_ms == 5000


# ── parse_event: error paths ──────────────────────────────────────────────────


class TestParseErrors:
    def test_missing_event_field_yields_parse_error(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {"session_id": "s1", "data": "no event key"}
        events = adapter.parse_event(raw)
        assert len(events) == 1
        assert isinstance(events[0], ParseError)
        assert events[0].reason == "missing_event_field"

    def test_unsupported_event_yields_parse_error(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        raw = {"event": "pre_compact", "session_id": "s1"}
        events = adapter.parse_event(raw)
        assert isinstance(events[0], ParseError)
        assert events[0].reason == "unsupported_bare_cli_event"

    def test_non_dict_returns_empty(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        assert adapter.parse_event("not-a-dict") == []  # type: ignore[arg-type]


# ── Capability matrix ──────────────────────────────────────────────────────────


class TestCapabilityMatrix:
    def test_supported_events_present(self):
        cap = BareCliAdapter.CAPABILITY_MATRIX
        for ev in ("SessionStart", "UserPromptSubmit", "ToolUseStart", "ToolUseEnd", "SessionEnd"):
            assert cap.get(ev) == "supported", f"{ev} should be supported"

    def test_precompact_unsupported(self):
        assert BareCliAdapter.CAPABILITY_MATRIX.get("PreCompact") == "unsupported"

    def test_all_expected_keys_present(self):
        expected = {
            "SessionStart", "UserPromptSubmit", "ToolUseStart", "ToolUseEnd",
            "SessionEnd", "PreCompact", "SubagentStart", "TeammateIdle",
            "TaskCreated", "TaskCompleted",
        }
        assert expected.issubset(set(BareCliAdapter.CAPABILITY_MATRIX.keys()))


# ── emit_canonical ────────────────────────────────────────────────────────────


class TestEmitCanonical:
    def test_emit_writes_jsonl_line(self, tmp_path, monkeypatch):
        _clean_env(monkeypatch)
        adapter = BareCliAdapter(project_dir=tmp_path)
        ev = SessionStart(
            session_id="s1", started_at=1714500000.0, harness="bare_cli", cwd="/tmp"
        )
        path = adapter.emit_canonical(ev)
        assert path.exists()
        import json
        line = json.loads(path.read_text().strip())
        assert line["event_type"] == "session_start"
        assert line["harness"] == "bare_cli"
