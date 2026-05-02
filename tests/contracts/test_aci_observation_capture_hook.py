from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "aci-observation-capture.sh"


def test_aci_observation_capture_writes_metrics_and_trajectory(tmp_path: Path) -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/unit -q"},
        "tool_response": {"content": "1 failed", "exit_code": 1},
    }
    result = subprocess.run(
        ["bash", str(HOOK)],
        cwd=tmp_path,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(tmp_path), "CLAUDE_PROJECT_DIR": str(tmp_path)},
    )

    assert result.returncode == 0
    metrics = tmp_path / ".cognitive-os" / "metrics" / "aci-observations.jsonl"
    trajectory = tmp_path / ".cognitive-os" / "metrics" / "agent-trajectory.jsonl"
    assert metrics.exists()
    assert trajectory.exists()
    assert "aci.observation" in metrics.read_text()
    assert "test_failure" in metrics.read_text()
    assert "Bash" in trajectory.read_text()
