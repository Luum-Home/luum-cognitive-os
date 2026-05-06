"""Unit tests for the harness-agnostic event capture base (ADR-033)."""

from __future__ import annotations

import pytest

from lib.harness_adapter.base import (
    AgentEnd,
    AgentStart,
    CanonicalEvent,
    HarnessAdapter,
    HeartbeatTick,
    ParseError,
    SessionEnd,
    SessionStart,
    TokenUsage,
    ToolUse,
    UserPromptSubmit,
)


class TestCanonicalEvents:
    def test_abc_instantiation_blocked(self):
        """HarnessAdapter is abstract — direct instantiation must fail."""
        with pytest.raises(TypeError):
            HarnessAdapter()  # type: ignore[abstract]

    def test_canonical_event_roundtrip(self, tmp_path):
        """Every canonical event subclass must roundtrip via to_dict/from_dict."""
        samples = [
            AgentStart(agent_id="a1", started_at=1.0, tool_name="Agent"),
            AgentEnd(
                agent_id="a1",
                ended_at=2.0,
                exit_status="success",
                token_usage={"input": 10, "output": 20},
            ),
            ToolUse(agent_id="a1", tool_name="Bash", started_at=3.0, exit_status="success"),
            TokenUsage(agent_id="a1", ts=4.0, input_tokens=100, output_tokens=50),
            HeartbeatTick(agent_id="a1", ts=5.0, alive=False),
            SessionStart(session_id="s1", started_at=6.0, harness="codex"),
            UserPromptSubmit(session_id="s1", submitted_at=7.0, harness="codex", prompt_hash="abc"),
            SessionEnd(session_id="s1", ended_at=8.0, harness="codex", exit_status="success"),
            ParseError(source_line="unknown line", adapter="aider", reason="no_match"),
        ]
        for original in samples:
            data = original.to_dict()
            assert data["event_type"] == type(original).event_type
            restored = CanonicalEvent.from_dict(data)
            assert type(restored) is type(original)
            assert restored.to_dict() == data

    def test_detect_harness_returns_none_for_unknown(self):
        """An adapter must return None when the payload is foreign to it."""
        from lib.harness_adapter.claude_code import ClaudeCodeAdapter
        from lib.harness_adapter.aider import AiderAdapter

        assert ClaudeCodeAdapter.detect_harness({"random": "payload"}) is None
        assert AiderAdapter.detect_harness({"random": "payload"}) is None

    def test_parse_error_event_registered(self):
        """ParseError must be in the event registry."""
        assert "parse_error" in CanonicalEvent._registry
        assert CanonicalEvent._registry["parse_error"] is ParseError


def test_read_inbound_signals_reads_control_answer_and_interrupt(tmp_path):
    import json
    from lib.harness_adapter.base import InboundSignal, read_inbound_signals

    agent_dir = tmp_path / ".cognitive-os" / "agent-bus" / "agent-1"
    agent_dir.mkdir(parents=True)
    (agent_dir / "control.jsonl").write_text(
        json.dumps({"command": "pause", "timestamp_epoch": 1.0}) + "\n"
    )
    (agent_dir / "answer.jsonl").write_text(
        json.dumps({"answers": ["use port 8080"], "round": 2, "timestamp_epoch": 2.0})
        + "\n"
    )
    (agent_dir / "interrupt").write_text(json.dumps({"command": "stop", "timestamp_epoch": 3.0}))

    signals = read_inbound_signals(tmp_path, agent_id="agent-1")

    assert all(isinstance(s, InboundSignal) for s in signals)
    assert {s.signal_type for s in signals} == {"control", "answer", "interrupt"}
    assert any(s.command == "stop" for s in signals)
    assert any(s.answers == ["use port 8080"] and s.round == 2 for s in signals)
