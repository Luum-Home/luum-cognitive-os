"""Unit tests for the Claude Code harness adapter (ADR-033)."""

from __future__ import annotations

from lib.harness_adapter.base import (
    AgentEnd,
    AgentStart,
    HarnessName,
    HeartbeatTick,
    TokenUsage,
    ToolUse,
)
from lib.harness_adapter.claude_code import ClaudeCodeAdapter


class TestClaudeCodeAdapter:
    def test_parse_pretooluse_agent_yields_start_and_heartbeat(self, tmp_path):
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        raw = {
            "tool_name": "Agent",
            "tool_use_id": "agent-1",
            "tool_input": {"prompt": "Do a thing"},
        }
        events = adapter.parse_event(raw)
        types = {type(e) for e in events}
        assert AgentStart in types, "PreToolUse Agent must emit AgentStart"
        assert HeartbeatTick in types, "PreToolUse Agent must emit HeartbeatTick(alive=True)"
        tick = next(e for e in events if isinstance(e, HeartbeatTick))
        assert tick.alive is True
        start = next(e for e in events if isinstance(e, AgentStart))
        assert start.agent_id == "agent-1"
        assert start.input_summary == "Do a thing"

    def test_parse_posttooluse_agent_yields_end_heartbeat_and_tokens(self, tmp_path):
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        raw = {
            "tool_name": "Agent",
            "tool_use_id": "agent-2",
            "tool_input": {"prompt": "x"},
            "tool_response": {
                "type": "tool_result",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 200,
                    "cache_read_input_tokens": 10,
                },
            },
        }
        events = adapter.parse_event(raw)
        types = {type(e) for e in events}
        assert AgentEnd in types
        assert HeartbeatTick in types
        assert TokenUsage in types
        end = next(e for e in events if isinstance(e, AgentEnd))
        assert end.agent_id == "agent-2"
        assert end.exit_status == "success"
        assert end.token_usage == {"input": 100, "output": 200, "cached": 10}
        tick = next(e for e in events if isinstance(e, HeartbeatTick))
        assert tick.alive is False

    def test_parse_generic_posttooluse_yields_tool_use(self, tmp_path):
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        raw = {
            "tool_name": "Bash",
            "tool_use_id": "tc-1",
            "tool_input": {"command": "ls"},
            "tool_response": {"type": "tool_result", "content": "..."},
        }
        events = adapter.parse_event(raw)
        types = {type(e) for e in events}
        assert ToolUse in types
        tu = next(e for e in events if isinstance(e, ToolUse))
        assert tu.tool_name == "Bash"
        assert tu.exit_status == "success"

    def test_parse_pretooluse_generic_tool_is_ignored(self, tmp_path):
        """PreToolUse on non-Agent tools yields nothing (no telemetry value)."""
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        events = adapter.parse_event(
            {
                "tool_name": "Bash",
                "tool_use_id": "tc-2",
                "tool_input": {"command": "ls"},
            }
        )
        assert events == []

    def test_parse_malformed_input_is_safe(self, tmp_path):
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        # Non-dict → []
        assert adapter.parse_event("not a dict") == []  # type: ignore[arg-type]
        # Missing tool_name → detect_harness also requires tool_use_id; with just a
        # tool_name it still parses (empty tool_name, agent_id unknown fallback),
        # but MUST NOT raise.
        events = adapter.parse_event({"tool_name": ""})
        assert isinstance(events, list)

    def test_detect_harness_positive(self):
        assert ClaudeCodeAdapter.detect_harness(
            {"tool_name": "Agent", "tool_use_id": "x"}
        ) == HarnessName.CLAUDE_CODE
