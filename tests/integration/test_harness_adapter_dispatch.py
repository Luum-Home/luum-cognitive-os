"""Integration tests for the ADR-033 dispatch entry point.

End-to-end: fake stdin payload → canonical JSONL output.
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.harness_adapter.dispatch import dispatch_event


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TestDispatchEndToEnd:
    def test_claude_code_pre_agent_writes_canonical_and_heartbeat(self, tmp_path):
        payload = json.dumps(
            {
                "tool_name": "Agent",
                "tool_use_id": "agent-dispatch-1",
                "tool_input": {"prompt": "do it"},
            }
        )
        result = dispatch_event(payload, project_dir=tmp_path)
        assert result["harness"] == "claude_code"
        assert result["events"], "at least one canonical event should be emitted"

        # Canonical stream (CC adapter default output is agent-heartbeat.jsonl)
        hb_path = tmp_path / ".cognitive-os" / "metrics" / "agent-heartbeat.jsonl"
        assert hb_path.exists()
        records = _read_jsonl(hb_path)
        # Must contain BOTH canonical events (agent_start / heartbeat_tick) AND
        # the legacy MetricEvent emitted by AgentBusMetrics.on_heartbeat_event.
        types = {r.get("event_type") for r in records}
        assert "agent_start" in types
        assert "heartbeat_tick" in types
        assert "agent_launched" in types, (
            f"Legacy agent_launched MetricEvent must still be present; got {types}"
        )

        # FallbackBus side-effect preserved
        bus_file = (
            tmp_path
            / ".cognitive-os"
            / "agent-bus"
            / "agent-dispatch-1"
            / "heartbeat.jsonl"
        )
        assert bus_file.exists(), "FallbackBus heartbeat.jsonl must be written"

    def test_aider_transcript_delta_routes_to_aider_adapter(self, tmp_path):
        payload = json.dumps(
            {
                "history_file": "/tmp/does-not-exist/.aider.chat.history.md",
                "agent_id": "aider-x",
                "new_lines": [
                    "#### fix the bug",
                    "> Applied edit: src/fix.py",
                ],
                "final": True,
            }
        )
        result = dispatch_event(payload, project_dir=tmp_path)
        assert result["harness"] == "aider"
        canonical = tmp_path / ".cognitive-os" / "metrics" / "canonical-events.jsonl"
        assert canonical.exists()
        records = _read_jsonl(canonical)
        types = {r.get("event_type") for r in records}
        assert {"agent_start", "tool_use", "agent_end"}.issubset(types)

    def test_unknown_payload_is_a_noop(self, tmp_path):
        result = dispatch_event(
            json.dumps({"random": "shape"}), project_dir=tmp_path
        )
        assert result["harness"] == "none"
        assert result["events"] == []
        # No files created
        canonical = tmp_path / ".cognitive-os" / "metrics" / "canonical-events.jsonl"
        hb = tmp_path / ".cognitive-os" / "metrics" / "agent-heartbeat.jsonl"
        assert not canonical.exists()
        assert not hb.exists()
