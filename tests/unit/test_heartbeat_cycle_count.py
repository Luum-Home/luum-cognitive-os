"""Unit tests for reasoning_cycle_count in HeartbeatTick (ADR-038 Gap #4).

Tests:
1. PostToolUse:Agent increments reasoning_cycle_count in HeartbeatTick.
2. reasoning_cycle_count resets to 0 on the next AgentStart (new agent).
"""

from __future__ import annotations

import pytest

from lib.harness_adapter.claude_code import ClaudeCodeAdapter
from lib.harness_adapter.base import HeartbeatTick, AgentStart


@pytest.fixture()
def adapter(tmp_path):
    return ClaudeCodeAdapter(project_dir=tmp_path)


class TestHeartbeatCycleCount:
    def test_post_tool_use_increments_cycle_count(self, adapter):
        """PostToolUse:Agent emits HeartbeatTick with reasoning_cycle_count >= 1."""
        agent_id = "cycle-test-agent-1"

        # First send a PreToolUse to register the agent
        pre_payload = {
            "tool_name": "Agent",
            "tool_use_id": agent_id,
            "tool_input": {"prompt": "Do a thing."},
        }
        pre_events = adapter.parse_event(pre_payload)

        # Confirm we got a HeartbeatTick with cycle_count=0 on start
        pre_hb = [e for e in pre_events if isinstance(e, HeartbeatTick)]
        assert pre_hb, "PreToolUse should emit a HeartbeatTick"
        assert pre_hb[0].reasoning_cycle_count == 0, (
            "PreToolUse HeartbeatTick should have reasoning_cycle_count=0"
        )

        # Now send a PostToolUse — one completed cycle
        post_payload = {
            "tool_name": "Agent",
            "tool_use_id": agent_id,
            "tool_input": {"prompt": "Do a thing."},
            "tool_response": {
                "type": "tool_result",
                "content": "Done.",
            },
        }
        post_events = adapter.parse_event(post_payload)

        post_hb = [e for e in post_events if isinstance(e, HeartbeatTick)]
        assert post_hb, "PostToolUse should emit a HeartbeatTick"
        assert post_hb[0].reasoning_cycle_count == 1, (
            f"Expected reasoning_cycle_count=1 after first PostToolUse, "
            f"got {post_hb[0].reasoning_cycle_count}"
        )

    def test_cycle_count_resets_for_new_agent(self, adapter):
        """A new agent_id starts with reasoning_cycle_count=0, not inheriting from previous."""
        # Run through a full cycle for agent-A
        agent_a = "cycle-test-agent-A"
        adapter.parse_event({
            "tool_name": "Agent",
            "tool_use_id": agent_a,
            "tool_input": {"prompt": "Agent A task."},
        })
        adapter.parse_event({
            "tool_name": "Agent",
            "tool_use_id": agent_a,
            "tool_input": {"prompt": "Agent A task."},
            "tool_response": {"type": "tool_result", "content": "A done."},
        })

        # A new agent (agent-B) starts with count 0
        agent_b = "cycle-test-agent-B"
        pre_events_b = adapter.parse_event({
            "tool_name": "Agent",
            "tool_use_id": agent_b,
            "tool_input": {"prompt": "Agent B task."},
        })

        hb_b = [e for e in pre_events_b if isinstance(e, HeartbeatTick)]
        assert hb_b, "Agent-B PreToolUse must emit HeartbeatTick"
        assert hb_b[0].reasoning_cycle_count == 0, (
            f"Agent-B should start at cycle_count=0, got {hb_b[0].reasoning_cycle_count}"
        )
        # Confirm it's the right agent
        assert hb_b[0].agent_id == agent_b
