from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.behavior
def test_branch_task_check_strict_exit_codes(project_root: Path, tmp_path: Path) -> None:
    ok = subprocess.run(
        [str(project_root / "scripts" / "cos-branch-task-check"), "--project-dir", str(tmp_path), "--task-id", "abc", "--current", "codex/task/abc", "--json", "--strict"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(ok.stdout)["status"] == "PASS"

    blocked = subprocess.run(
        [str(project_root / "scripts" / "cos-branch-task-check"), "--project-dir", str(tmp_path), "--task-id", "abc", "--current", "main", "--json", "--strict"],
        text=True,
        capture_output=True,
    )
    assert blocked.returncode == 2
    assert json.loads(blocked.stdout)["status"] == "BLOCK"
