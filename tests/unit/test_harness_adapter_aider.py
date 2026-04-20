"""Unit tests for the Aider POC harness adapter (ADR-033)."""

from __future__ import annotations

from lib.harness_adapter.aider import AiderAdapter
from lib.harness_adapter.base import AgentEnd, AgentStart, HarnessName, ToolUse


class TestAiderAdapter:
    def test_detect_harness_matches_history_file_payload(self):
        assert AiderAdapter.detect_harness(
            {"history_file": "/tmp/proj/.aider.chat.history.md"}
        ) == HarnessName.AIDER
        assert AiderAdapter.detect_harness(
            "/tmp/proj/.aider.chat.history.md"
        ) == HarnessName.AIDER
        assert AiderAdapter.detect_harness({"history_file": "/tmp/other.md"}) is None
        assert AiderAdapter.detect_harness({"no_match": True}) is None

    def test_parse_transcript_delta_yields_start_tool_use_and_end(self, tmp_path):
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = {
            "agent_id": "aider-session-1",
            "new_lines": [
                "#### Add a failing test for the parser",
                "> Ran shell command: pytest tests/unit/test_parser.py",
                "```python",
                "def test_x(): pass",
                "```",
                "> Applied edit: src/parser.py",
            ],
            "final": True,
            "token_usage": {"input": 5, "output": 10},
        }
        events = adapter.parse_event(raw)
        types = [type(e) for e in events]
        assert AgentStart in types, "First #### block must produce AgentStart"
        assert ToolUse in types, "> Ran / > Applied lines must produce ToolUse"
        assert AgentEnd in types, "final=True must produce AgentEnd"
        start = next(e for e in events if isinstance(e, AgentStart))
        assert start.tool_name == "aider"
        assert "Add a failing test" in (start.input_summary or "")
        tool_uses = [e for e in events if isinstance(e, ToolUse)]
        assert any(t.tool_name == "Ran shell command" for t in tool_uses)
        end = next(e for e in events if isinstance(e, AgentEnd))
        assert end.agent_id == "aider-session-1"
        assert end.token_usage == {"input": 5, "output": 10}
