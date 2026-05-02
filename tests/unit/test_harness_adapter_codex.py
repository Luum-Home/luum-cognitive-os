"""Unit tests for the Codex harness adapter (ADR-081)."""

from __future__ import annotations

import json
from pathlib import Path

from lib.harness_adapter.base import (
    HarnessName,
    ParseError,
    SessionEnd,
    SessionStart,
    ToolUse,
    ToolUseEnd,
    ToolUseStart,
    UserPromptSubmit,
)
from lib.harness_adapter.codex import CodexAdapter
from lib.harness_adapter.dispatch import dispatch_event

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex-live-session"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestCodexAdapter:
    def test_detects_live_session_wrappers(self, tmp_path):
        assert CodexAdapter.detect_harness(_fixture("session_meta.json")) == HarnessName.CODEX
        assert CodexAdapter.detect_harness(_fixture("function_call.json")) == HarnessName.CODEX
        assert CodexAdapter.detect_harness(_fixture("exec_command_end.json")) == HarnessName.CODEX

    def test_session_meta_yields_session_start(self, tmp_path):
        adapter = CodexAdapter(project_dir=tmp_path)
        events = adapter.parse_event(_fixture("session_meta.json"))
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, SessionStart)
        assert event.session_id == "codex-live-session-001"
        assert event.harness == "codex"
        assert event.cwd == "/workspace/luum-agent-os"
        assert event.version == "0.126.0-alpha.8"

    def test_user_message_yields_prompt_submit_without_prompt_leak(self, tmp_path):
        adapter = CodexAdapter(project_dir=tmp_path)
        events = adapter.parse_event(_fixture("user_message.json"))
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserPromptSubmit)
        assert event.harness == "codex"
        assert event.prompt_hash
        assert event.prompt_summary == "Implement ADR-081 Codex harness adapter using captured payloads."

    def test_function_call_yields_tool_start(self, tmp_path):
        adapter = CodexAdapter(project_dir=tmp_path)
        event = adapter.parse_event(_fixture("function_call.json"))[0]
        assert isinstance(event, ToolUseStart)
        assert event.agent_id == "call_live_exec_001"
        assert event.tool_name == "exec_command"
        assert "git status" in (event.tool_input_summary or "")

    def test_exec_and_mcp_end_yield_tool_end(self, tmp_path):
        adapter = CodexAdapter(project_dir=tmp_path)
        exec_end = adapter.parse_event(_fixture("exec_command_end.json"))[0]
        mcp_end = adapter.parse_event(_fixture("mcp_tool_call_end.json"))[0]
        assert isinstance(exec_end, ToolUseEnd)
        assert exec_end.agent_id == "call_live_exec_001"
        assert exec_end.tool_name == "exec_command"
        assert exec_end.exit_status == "success"
        assert isinstance(mcp_end, ToolUseEnd)
        assert mcp_end.tool_name == "mcp.engram.mem_current_project"
        assert mcp_end.duration_ms == 26

    def test_task_complete_yields_session_end(self, tmp_path):
        adapter = CodexAdapter(project_dir=tmp_path)
        event = adapter.parse_event(_fixture("task_complete.json"))[0]
        assert isinstance(event, SessionEnd)
        assert event.session_id == "codex-turn-001"
        assert event.duration_ms == 189206
        assert event.exit_status == "success"

    def test_hook_events_supported_and_non_bash_gap_is_explicit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CODEX_THREAD_ID", "thread-1")
        adapter = CodexAdapter(project_dir=tmp_path)
        session = adapter.parse_event({"hook_event": "SessionStart", "session_id": "s1", "cwd": "/workspace"})[0]
        prompt = adapter.parse_event({"hook_event": "UserPromptSubmit", "session_id": "s1", "prompt": "hello"})[0]
        stop = adapter.parse_event({"hook_event": "Stop", "session_id": "s1"})[0]
        gap = adapter.parse_event({"hook_event": "PreToolUse", "tool_name": "Edit", "session_id": "s1"})[0]
        bash = adapter.parse_event({"hook_event": "PostToolUse", "tool_name": "Bash", "tool_use_id": "bash-1", "exit_code": 0, "session_id": "s1"})[0]
        assert isinstance(session, SessionStart)
        assert isinstance(prompt, UserPromptSubmit)
        assert isinstance(stop, SessionEnd)
        assert isinstance(gap, ParseError)
        assert gap.reason == "codex_tool_coverage_gap"
        assert isinstance(bash, ToolUse)
        assert bash.tool_name == "Bash"

    def test_adapter_instantiation_is_idempotent(self, tmp_path):
        a = CodexAdapter(project_dir=tmp_path)
        b = CodexAdapter(project_dir=tmp_path)
        assert a.name == b.name == HarnessName.CODEX
        assert a.SUPPORTED_EVENTS == b.SUPPORTED_EVENTS

    def test_supported_events_lists_canonical_outputs_only(self, tmp_path):
        assert "session_start" in CodexAdapter.SUPPORTED_EVENTS
        assert "parse_error" in CodexAdapter.SUPPORTED_EVENTS
        assert "SessionStart" not in CodexAdapter.SUPPORTED_EVENTS
        assert "SessionStart" in CodexAdapter.SUPPORTED_INPUT_EVENTS
        assert "PreCompact" not in CodexAdapter.SUPPORTED_INPUT_EVENTS

    def test_dispatch_consults_supported_input_guard(self, tmp_path):
        payload = {
            "harness": "codex",
            "hook_event": "PreCompact",
            "session_id": "codex-precompact",
        }

        result = dispatch_event(payload, adapters=[CodexAdapter], project_dir=tmp_path)

        assert result["harness"] == "none"
        assert result["events"] == []
