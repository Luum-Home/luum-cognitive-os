"""Unit tests for ADR-033b duration correlation in ClaudeCodeAdapter.

Tests:
1. Pre→Post round-trip produces real duration_ms (non-None, non-negative int)
2. Post-without-Pre returns duration_ms = None
3. Malformed input is handled gracefully
"""

from __future__ import annotations

import time

import pytest

from lib.harness_adapter.base import AgentEnd, AgentStart
from lib.harness_adapter.claude_code import ClaudeCodeAdapter
from lib.harness_adapter.tool_use_correlation import CorrelationStore


class TestClaudeCodeDuration:
    def test_pre_post_round_trip_produces_real_duration_ms(self, tmp_path):
        """A Pre event followed by a Post event yields a non-None, non-negative duration_ms."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        adapter = ClaudeCodeAdapter(project_dir=tmp_path, correlation_store=store)

        pre_raw = {
            "tool_name": "Agent",
            "tool_use_id": "duration-test-1",
            "tool_input": {"prompt": "run something"},
        }
        adapter.parse_event(pre_raw)  # records start time

        # Simulate a brief delay
        time.sleep(0.01)

        post_raw = {
            "tool_name": "Agent",
            "tool_use_id": "duration-test-1",
            "tool_input": {"prompt": "run something"},
            "tool_response": {
                "type": "tool_result",
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
        }
        events = adapter.parse_event(post_raw)
        end_events = [e for e in events if isinstance(e, AgentEnd)]
        assert end_events, "Post should emit AgentEnd"
        end = end_events[0]
        assert end.duration_ms is not None, "duration_ms must not be None after Pre→Post"
        assert end.duration_ms >= 0, "duration_ms must be non-negative"
        # Should be at least ~10 ms since we slept
        assert end.duration_ms >= 5, f"Expected >= 5 ms, got {end.duration_ms}"

    def test_post_without_pre_returns_none_duration(self, tmp_path):
        """A Post event with no corresponding Pre yields duration_ms = None."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        adapter = ClaudeCodeAdapter(project_dir=tmp_path, correlation_store=store)

        post_raw = {
            "tool_name": "Agent",
            "tool_use_id": "no-pre-id",
            "tool_input": {"prompt": "orphaned post"},
            "tool_response": {
                "type": "tool_result",
                "usage": {"input_tokens": 5, "output_tokens": 5},
            },
        }
        events = adapter.parse_event(post_raw)
        end_events = [e for e in events if isinstance(e, AgentEnd)]
        assert end_events, "Post should still emit AgentEnd"
        end = end_events[0]
        assert end.duration_ms is None, (
            "duration_ms must be None when no Pre event was recorded"
        )

    def test_malformed_input_does_not_raise(self, tmp_path):
        """Malformed or non-dict inputs must not raise exceptions."""
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        # Non-dict
        result = adapter.parse_event("not-a-dict")  # type: ignore[arg-type]
        assert result == []
        # Empty dict
        result = adapter.parse_event({})
        assert isinstance(result, list)
        # None value in tool_use_id slot
        result = adapter.parse_event(
            {"tool_name": "Agent", "tool_use_id": None, "tool_response": {}}
        )
        assert isinstance(result, list)
