from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


@pytest.mark.chaos
def test_handoff_receiver_timeout_persists_failure_receipt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    send = subprocess.run(
        [
            str(COS), "team", "--json", "--project-dir", str(project),
            "handoff", "send", "--team", "release", "--from-agent", "lead",
            "--to-agent", "worker", "--text", "kill chaos", "--handoff-id", "chaos-kill-1",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert send.returncode == 0, send.stderr

    receive = subprocess.run(
        [
            str(COS), "team", "--json", "--project-dir", str(project),
            "handoff", "receive", "--team", "release", "--session-id", "worker",
            "--hook-command", "python3 -c 'import time; time.sleep(5)'",
            "--timeout-seconds", "1", "--strict", "--once",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=6,
    )
    assert receive.returncode == 2
    receipt = project / ".cognitive-os/teams/release/handoff-receipts/chaos-kill-1.json"
    data = json.loads(receipt.read_text())
    assert data["exit_code"] == 124
    assert data["error"] == "receiver_timeout"
    # Idempotency: second receive skips the already-failed handoff instead of
    # executing the dangerous receiver twice.
    second = subprocess.run(
        [
            str(COS), "team", "--json", "--project-dir", str(project),
            "handoff", "receive", "--team", "release", "--session-id", "worker", "--once",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert second.returncode == 0
    assert json.loads(second.stdout)["received"] == []
