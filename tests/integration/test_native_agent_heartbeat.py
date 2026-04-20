"""Integration tests for native-agent-heartbeat.sh (D2).

Tests:
1. PreToolUse:Agent input (no tool_response) → agent_launched written to agent-heartbeat.jsonl.
2. PostToolUse:Agent input (with tool_response) → agent_completed written to agent-heartbeat.jsonl.
3. Missing tool_use_id → agent_id falls back to "native-agent-unknown", event still valid.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]
HOOK = PROJECT_DIR / "hooks" / "native-agent-heartbeat.sh"


@pytest.fixture(autouse=True)
def _require_hook():
    if not HOOK.exists():
        pytest.skip(f"Hook not found: {HOOK}")


@pytest.fixture()
def tmp_project(tmp_path):
    """Minimal project directory wired for the heartbeat hook."""
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    agent_bus_dir = tmp_path / ".cognitive-os" / "agent-bus"
    agent_bus_dir.mkdir(parents=True)
    return tmp_path


def _run_hook(
    tmp_project: Path,
    input_data: dict,
    session_id: str = "test-session-d2",
) -> subprocess.CompletedProcess:
    """Run native-agent-heartbeat.sh with given stdin JSON."""
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_project),
        "CLAUDE_PROJECT_DIR": str(tmp_project),
        "PROJECT_DIR": str(tmp_project),
        "COGNITIVE_OS_SESSION_ID": session_id,
        # Ensure lib/ on Python path
        "PYTHONPATH": str(PROJECT_DIR) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _read_heartbeat_jsonl(tmp_project: Path) -> list[dict]:
    """Read all MetricEvent records from agent-heartbeat.jsonl."""
    hb_file = tmp_project / ".cognitive-os" / "metrics" / "agent-heartbeat.jsonl"
    if not hb_file.exists():
        return []
    records = []
    for line in hb_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


class TestNativeAgentHeartbeat:
    """D2 — native-agent-heartbeat.sh behaviour."""

    def test_pre_tool_use_writes_agent_launched(self, tmp_project):
        """PreToolUse (no tool_response key) emits agent_launched event."""
        agent_id = f"test-agent-pre-{int(time.time() * 1000)}"
        input_data = {
            "tool_name": "Agent",
            "tool_use_id": agent_id,
            "tool_input": {
                "prompt": "Do something useful.",
            },
            # NO tool_response — this is a PreToolUse event
        }

        result = _run_hook(tmp_project, input_data)
        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        records = _read_heartbeat_jsonl(tmp_project)
        assert records, "agent-heartbeat.jsonl must contain at least one record"

        launched = [r for r in records if r.get("event_type") == "agent_launched"]
        assert launched, (
            f"Expected agent_launched event, got event_types: "
            f"{[r.get('event_type') for r in records]}"
        )

        ev = launched[0]
        payload = ev.get("payload", {})
        assert payload.get("agent_id") == agent_id, (
            f"agent_id mismatch: expected {agent_id!r}, got {payload.get('agent_id')!r}"
        )
        assert payload.get("alive") is True, "PreToolUse event must have alive=True"
        # phase in MetricEvent payload is derived from what on_heartbeat_event receives;
        # the hook passes alive=True without an explicit phase key, so it defaults to "".
        # The canonical proof of state is event_type == "agent_launched", already asserted.

    def test_post_tool_use_writes_agent_completed(self, tmp_project):
        """PostToolUse (tool_response present) emits agent_completed event."""
        agent_id = f"test-agent-post-{int(time.time() * 1000)}"

        # First send a launch event so the dedup tracker has a record.
        pre_input = {
            "tool_name": "Agent",
            "tool_use_id": agent_id,
            "tool_input": {"prompt": "Task for completion test."},
        }
        result_pre = _run_hook(tmp_project, pre_input)
        assert result_pre.returncode == 0, f"Pre hook failed: {result_pre.stderr}"

        # Now send the completion event (PostToolUse carries tool_response).
        post_input = {
            "tool_name": "Agent",
            "tool_use_id": agent_id,
            "tool_input": {"prompt": "Task for completion test."},
            "tool_response": {
                "type": "tool_result",
                "content": "Task finished successfully.",
            },
        }
        result_post = _run_hook(tmp_project, post_input)
        assert result_post.returncode == 0, f"Post hook failed: {result_post.stderr}"

        records = _read_heartbeat_jsonl(tmp_project)
        completed = [r for r in records if r.get("event_type") == "agent_completed"]
        assert completed, (
            f"Expected agent_completed event, got event_types: "
            f"{[r.get('event_type') for r in records]}"
        )

        ev = completed[0]
        payload = ev.get("payload", {})
        assert payload.get("agent_id") == agent_id, (
            f"agent_id mismatch: expected {agent_id!r}, got {payload.get('agent_id')!r}"
        )
        assert payload.get("alive") is False, "PostToolUse event must have alive=False"
        # phase in MetricEvent payload is "" (hook does not pass phase to on_heartbeat_event).
        # The canonical proof of state is event_type == "agent_completed", already asserted.

    def test_missing_tool_use_id_uses_unknown_fallback(self, tmp_project):
        """Missing tool_use_id → agent_id = 'native-agent-unknown', event still emitted."""
        input_data = {
            "tool_name": "Agent",
            # No tool_use_id, no tool_input.tool_use_id
            "tool_input": {
                "prompt": "Task with no ID.",
            },
        }

        result = _run_hook(tmp_project, input_data)
        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        records = _read_heartbeat_jsonl(tmp_project)
        assert records, "At least one record must be emitted even without tool_use_id"

        unknown = [
            r for r in records
            if r.get("payload", {}).get("agent_id") == "native-agent-unknown"
        ]
        assert unknown, (
            f"Expected a record with agent_id='native-agent-unknown'. "
            f"Records: {[r.get('payload', {}).get('agent_id') for r in records]}"
        )

        ev = unknown[0]
        # Event type must be agent_launched (PreToolUse — no tool_response)
        assert ev.get("event_type") == "agent_launched", (
            f"Expected agent_launched, got {ev.get('event_type')!r}"
        )

    def test_fallback_bus_file_also_written(self, tmp_project):
        """FallbackBus heartbeat.jsonl is written alongside the MetricEvent."""
        agent_id = f"test-agent-bus-{int(time.time() * 1000)}"
        input_data = {
            "tool_name": "Agent",
            "tool_use_id": agent_id,
            "tool_input": {"prompt": "Bus file test."},
        }

        result = _run_hook(tmp_project, input_data)
        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        bus_file = tmp_project / ".cognitive-os" / "agent-bus" / agent_id / "heartbeat.jsonl"
        assert bus_file.exists(), (
            f"FallbackBus heartbeat file not created at {bus_file}"
        )
        lines = [
            json.loads(ln)
            for ln in bus_file.read_text().splitlines()
            if ln.strip()
        ]
        assert lines, "FallbackBus heartbeat.jsonl must contain at least one record"
        assert lines[0].get("agent_id") == agent_id
        assert lines[0].get("source") == "native-agent-heartbeat-hook"
