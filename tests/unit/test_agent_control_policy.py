from __future__ import annotations

import json

from lib.agent_control_policy import evaluate_control, target_ids_from_payload


def _write_control(root, target, command, ts):
    path = root / ".cognitive-os" / "agent-bus" / target
    path.mkdir(parents=True, exist_ok=True)
    with (path / "control.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"command": command, "timestamp_epoch": ts}) + "\n")


def test_target_ids_from_payload_includes_agent_and_session(monkeypatch):
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "session-1")
    ids = target_ids_from_payload({"agent_id": "agent-1", "tool_use_id": "tool-1"})
    assert ids[:3] == ["agent-1", "tool-1", "session-1"]


def test_stop_interrupt_blocks(tmp_path):
    agent_dir = tmp_path / ".cognitive-os" / "agent-bus" / "agent-1"
    agent_dir.mkdir(parents=True)
    (agent_dir / "interrupt").write_text(json.dumps({"command": "stop", "timestamp_epoch": 10}))

    decision = evaluate_control(tmp_path, payload={"agent_id": "agent-1"})

    assert decision.should_block is True
    assert decision.command == "stop"
    assert decision.target_id == "agent-1"


def test_pause_blocks_until_newer_resume(tmp_path):
    _write_control(tmp_path, "agent-1", "pause", 10)
    paused = evaluate_control(tmp_path, payload={"agent_id": "agent-1"})
    assert paused.should_block is True
    assert paused.command == "pause"

    _write_control(tmp_path, "agent-1", "resume", 11)
    resumed = evaluate_control(tmp_path, payload={"agent_id": "agent-1"})
    assert resumed.should_block is False
    assert resumed.command == "resume"


def test_latest_target_across_session_and_agent_wins(tmp_path):
    _write_control(tmp_path, "session-1", "pause", 10)
    _write_control(tmp_path, "agent-1", "resume", 20)

    decision = evaluate_control(
        tmp_path,
        payload={"agent_id": "agent-1", "session_id": "session-1"},
    )

    assert decision.should_block is False
    assert decision.target_id == "agent-1"
