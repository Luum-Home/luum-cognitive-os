"""Unit tests for the harness-agnostic event capture base (ADR-033)."""

from __future__ import annotations

import pytest

from lib.harness_adapter.base import (
    AgentEnd,
    AgentStart,
    CanonicalEvent,
    HarnessAdapter,
    HarnessName,
    HeartbeatTick,
    TokenUsage,
    ToolUse,
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

        random_payload = {"foo": "bar", "no_known_keys": True}
        assert ClaudeCodeAdapter.detect_harness(random_payload) is None
        assert AiderAdapter.detect_harness(random_payload) is None
        # Also None for non-dict garbage
        assert ClaudeCodeAdapter.detect_harness(42) is None
        assert AiderAdapter.detect_harness(None) is None
        # Sanity: known CC shape detects as CLAUDE_CODE
        cc = {"tool_name": "Agent", "tool_use_id": "x", "tool_input": {}}
        assert ClaudeCodeAdapter.detect_harness(cc) == HarnessName.CLAUDE_CODE
