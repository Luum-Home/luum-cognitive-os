from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "control-plane-audit.sh"


def run_hook(payload: dict, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(ROOT)
    env["COS_CONTROL_PLANE_AUDIT_MODE"] = "block"
    env["COS_CONTROL_PLANE_AUDIT_LANE"] = "hook-fast"
    env["HOME"] = str(tmp_path)
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, env=env, check=False)


def test_hook_fast_runs_before_git_commit(tmp_path: Path) -> None:
    proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "git commit -m test"}}, tmp_path)

    assert proc.returncode == 0
    metric = ROOT / ".cognitive-os" / "metrics" / "control-plane-audit-hook.jsonl"
    assert metric.exists()


def test_hook_fast_skips_unrelated_bash(tmp_path: Path) -> None:
    proc = run_hook({"tool_name": "Bash", "tool_input": {"command": "echo hello"}}, tmp_path)

    assert proc.returncode == 0
    assert "control-plane-audit" not in proc.stderr


def test_hook_fast_runs_before_report_publish_write(tmp_path: Path) -> None:
    proc = run_hook({"tool_name": "Write", "tool_input": {"file_path": "docs/reports/example.md"}}, tmp_path)

    assert proc.returncode == 0
