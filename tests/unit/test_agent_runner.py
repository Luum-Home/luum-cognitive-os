"""Unit tests for lib.agent_runner (ADR-064 Task 4.1)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pytest

from lib.agent_runner import (
    DEFAULT_ALLOWED_TOOLS,
    spawn,
    _resolve_provider,
)


# ── Minimal stub for AgentLoopResult ─────────────────────────────────────────


@dataclass
class _StubLoopResult:
    success: bool = True
    text: str = "stub response"
    iterations: int = 1
    tool_calls_made: int = 0
    tokens_in: int = 10
    tokens_out: int = 20
    cost_usd: float = 0.0
    stop_reason: str = "finished"
    error: str = ""
    provider: str = "qwen"
    model: str = "qwen3-plus"
    messages_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_log: List[Dict[str, Any]] = field(default_factory=list)


# ── _resolve_provider ─────────────────────────────────────────────────────────


class TestResolveProvider:
    def test_auto_maps_to_qwen(self):
        p, h = _resolve_provider("auto")
        assert p == "qwen"
        assert h is None

    def test_empty_maps_to_qwen(self):
        p, h = _resolve_provider("")
        assert p == "qwen"

    def test_opus_hint(self):
        p, h = _resolve_provider("opus")
        assert p == "qwen"
        assert h == "opus"

    def test_sonnet_hint(self):
        p, h = _resolve_provider("sonnet")
        assert h == "sonnet"

    def test_haiku_hint(self):
        p, h = _resolve_provider("haiku")
        assert h == "haiku"

    def test_claude_model_name_maps_to_qwen(self):
        p, h = _resolve_provider("claude-sonnet-4-6")
        assert p == "qwen"

    def test_qwen_model_stays_qwen(self):
        p, h = _resolve_provider("qwen3-plus")
        assert p == "qwen"
        assert h == "qwen3-plus"


# ── spawn with mock dispatch ──────────────────────────────────────────────────


class TestSpawnMockDispatch:
    def _stub_run(self, **kwargs) -> _StubLoopResult:
        return _StubLoopResult(text="hello world", success=True)

    def test_spawn_returns_success(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        result = spawn(
            prompt="echo hello",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(text="hello world", success=True),
        )
        assert result.status == "success"
        assert result.final_response == "hello world"
        assert result.session_id.startswith("bare-cli-")

    def test_spawn_writes_events_jsonl(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        result = spawn(
            prompt="echo hello",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(),
        )
        events_dir = tmp_path / ".cognitive-os" / "sessions" / result.session_id
        jsonl = events_dir / "agent-events.jsonl"
        assert jsonl.exists(), "agent-events.jsonl must be written"
        lines = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
        event_types = [l["event_type"] for l in lines]
        assert "session_start" in event_types
        assert "user_prompt_submit" in event_types
        assert "session_end" in event_types

    def test_spawn_records_tokens_used(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        result = spawn(
            prompt="something",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(tokens_in=100, tokens_out=200),
        )
        assert result.tokens_used == {"input": 100, "output": 200}

    def test_spawn_error_status_on_loop_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        result = spawn(
            prompt="fail task",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(success=False, error="LLM error"),
        )
        assert result.status == "error"
        assert "LLM error" in result.error

    def test_spawn_uses_explicit_session_id(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        result = spawn(
            prompt="p",
            model="auto",
            session_id="my-fixed-sid",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(),
        )
        assert result.session_id == "my-fixed-sid"

    def test_spawn_passes_allowed_tools_to_loop(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        captured = {}

        def _capture(**kw):
            captured.update(kw)
            return _StubLoopResult()

        spawn(
            prompt="p",
            model="auto",
            allowed_tools=["read_file", "glob_files"],
            project_dir=tmp_path,
            _run_agent_fn=_capture,
        )
        assert captured.get("tools_allowed") == ["read_file", "glob_files"]

    def test_spawn_default_tools_when_none(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        captured = {}

        def _capture(**kw):
            captured.update(kw)
            return _StubLoopResult()

        spawn(
            prompt="p",
            model="auto",
            allowed_tools=None,
            project_dir=tmp_path,
            _run_agent_fn=_capture,
        )
        assert set(captured.get("tools_allowed", [])) == set(DEFAULT_ALLOWED_TOOLS)

    def test_spawn_emits_tool_log_events(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        loop_result = _StubLoopResult(
            tool_log=[
                {"tool": "read_file", "status": "success"},
                {"tool": "run_bash", "status": "error"},
            ]
        )
        result = spawn(
            prompt="p",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: loop_result,
        )
        tool_end_events = [e for e in result.events if e.get("event_type") == "tool_use_end"]
        assert len(tool_end_events) == 2


# ── Timeout path ──────────────────────────────────────────────────────────────


class TestSpawnTimeout:
    def test_timeout_path(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        import time

        def _slow(**kw):
            time.sleep(10)  # will be interrupted by SIGALRM
            return _StubLoopResult()

        result = spawn(
            prompt="slow task",
            model="auto",
            timeout_s=1,
            project_dir=tmp_path,
            _run_agent_fn=_slow,
        )
        assert result.status == "timeout"
        assert "timed out" in result.error.lower()

    def test_timeout_exit_code_in_events(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        import time

        def _slow(**kw):
            time.sleep(10)
            return _StubLoopResult()

        result = spawn(
            prompt="slow",
            model="auto",
            timeout_s=1,
            project_dir=tmp_path,
            _run_agent_fn=_slow,
        )
        end_event = next(
            (e for e in result.events if e.get("event_type") == "session_end"), None
        )
        assert end_event is not None
        assert end_event["exit_status"] == "timeout"


# ── Depth guard ───────────────────────────────────────────────────────────────


class TestDepthGuard:
    def test_depth_guard_blocks_nested_spawn(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COS_AGENT_DEPTH", "1")
        with pytest.raises(RuntimeError, match="recursive sub-agent"):
            spawn(
                prompt="nested",
                model="auto",
                project_dir=tmp_path,
                _run_agent_fn=lambda **kw: _StubLoopResult(),
            )

    def test_depth_guard_allows_depth_zero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("COS_AGENT_DEPTH", "0")
        result = spawn(
            prompt="ok",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(text="ok"),
        )
        assert result.status == "success"

    def test_depth_env_restored_after_spawn(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        spawn(
            prompt="p",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(),
        )
        assert os.environ.get("COS_AGENT_DEPTH") is None


# ── AgentResult.to_dict ───────────────────────────────────────────────────────


class TestAgentResultToDict:
    def test_to_dict_is_json_serialisable(self, tmp_path, monkeypatch):
        monkeypatch.delenv("COS_AGENT_DEPTH", raising=False)
        result = spawn(
            prompt="p",
            model="auto",
            project_dir=tmp_path,
            _run_agent_fn=lambda **kw: _StubLoopResult(),
        )
        d = result.to_dict()
        assert json.dumps(d)  # must not raise
        assert d["status"] == "success"
