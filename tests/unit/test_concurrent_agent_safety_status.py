from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.concurrent_agent_safety_status import collect_status, status_to_json

pytestmark = pytest.mark.unit


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_projection_status_detects_required_safety_hooks(tmp_path: Path) -> None:
    claude_only_hooks = "hooks/plan-claim-validator.sh\nhooks/concurrent-write-guard.sh"
    write(tmp_path / ".claude/settings.json", f"hooks/orchestrator-claim-gate.sh\n{claude_only_hooks}")
    write(tmp_path / ".codex/hooks.json", "hooks/orchestrator-claim-gate.sh")
    write(tmp_path / "cognitive-os.yaml", f"hooks/orchestrator-claim-gate.sh\n{claude_only_hooks}")
    write(
        tmp_path / "scripts/_lib/settings-driver-claude-code.sh",
        f"hooks/orchestrator-claim-gate.sh\n{claude_only_hooks}",
    )

    status = collect_status(tmp_path)

    projections = {item.hook: item for item in status.claim_gate_projection}
    assert projections["hooks/orchestrator-claim-gate.sh"].complete_for_baseline is True
    assert projections["hooks/plan-claim-validator.sh"].complete_for_baseline is True
    assert projections["hooks/plan-claim-validator.sh"].codex_required is False
    assert projections["hooks/concurrent-write-guard.sh"].complete_for_baseline is True
    assert projections["hooks/concurrent-write-guard.sh"].codex is False
    assert projections["hooks/concurrent-write-guard.sh"].codex_required is False
    assert status.findings == []


def test_projection_finding_when_claim_gate_missing_from_driver(tmp_path: Path) -> None:
    write(tmp_path / ".claude/settings.json", "hooks/orchestrator-claim-gate.sh")
    write(tmp_path / ".codex/hooks.json", "hooks/orchestrator-claim-gate.sh")
    write(tmp_path / "cognitive-os.yaml", "hooks/orchestrator-claim-gate.sh")
    write(tmp_path / "scripts/_lib/settings-driver-claude-code.sh", "")

    status = collect_status(tmp_path)

    assert any(finding.code == "projection_incomplete" for finding in status.findings)


def test_collects_sessions_locks_stash_alarm_and_heartbeats(tmp_path: Path) -> None:
    write(
        tmp_path / ".cognitive-os/sessions/active-sessions.json",
        json.dumps({"sessions": [{"id": "s1", "pid": 123, "status": "active"}]}),
    )
    write(
        tmp_path / ".cognitive-os/runtime/git-index.lock/meta.json",
        json.dumps({"session_id": "s1", "operation": "commit"}),
    )
    write(
        tmp_path / ".cognitive-os/runtime/edit-locks/hooks--foo.sh/meta.yaml",
        'session_id: "s1"\ntarget_file: "hooks/foo.sh"\n',
    )
    write(
        tmp_path / ".cognitive-os/sessions/locks/file.lock",
        json.dumps({"session_id": "s1", "file_path": "hooks/foo.sh"}),
    )
    write(
        tmp_path / ".cognitive-os/runtime/stash-leak-alarm.json",
        json.dumps({"blocking": True, "stash_ref": "stash@{0}"}),
    )
    write(
        tmp_path / ".cognitive-os/agent-bus/agent-a/heartbeat.jsonl",
        json.dumps({"agent_id": "agent-a", "alive": True, "timestamp_epoch": 1}) + "\n",
    )

    status = collect_status(tmp_path)

    assert status.active_sessions[0]["id"] == "s1"
    assert status.locks["git_index"][0]["operation"] == "commit"
    assert status.locks["edit"][0]["target_file"] == "hooks/foo.sh"
    assert status.locks["concurrent_write"][0]["file_path"] == "hooks/foo.sh"
    assert status.stash_alarm and status.stash_alarm["blocking"] is True
    assert status.recent_agent_heartbeats[0]["agent_id"] == "agent-a"
    assert any(finding.code == "stash_leak_blocking" for finding in status.findings)


def test_status_to_json_is_stable_json(tmp_path: Path) -> None:
    status = collect_status(tmp_path)

    payload = json.loads(status_to_json(status))

    assert payload["project_dir"] == str(tmp_path.resolve())
    assert "claim_gate_projection" in payload
