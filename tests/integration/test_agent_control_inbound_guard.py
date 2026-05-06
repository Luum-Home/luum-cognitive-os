from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "agent-control-inbound-guard.sh"


def _run_hook(tmp_path, payload):
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def _write_control(root, target, command, ts):
    path = root / ".cognitive-os" / "agent-bus" / target
    path.mkdir(parents=True, exist_ok=True)
    with (path / "control.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"command": command, "timestamp_epoch": ts}) + "\n")


def test_guard_allows_without_control(tmp_path):
    result = _run_hook(tmp_path, {"agent_id": "agent-1"})
    assert result.returncode == 0, result.stderr


def test_guard_blocks_paused_agent(tmp_path):
    _write_control(tmp_path, "agent-1", "pause", 1)
    result = _run_hook(tmp_path, {"agent_id": "agent-1"})
    assert result.returncode == 2
    assert "pause" in result.stderr


def test_guard_allows_after_resume(tmp_path):
    _write_control(tmp_path, "agent-1", "pause", 1)
    _write_control(tmp_path, "agent-1", "resume", 2)
    result = _run_hook(tmp_path, {"agent_id": "agent-1"})
    assert result.returncode == 0, result.stderr
