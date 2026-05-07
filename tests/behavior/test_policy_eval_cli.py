from __future__ import annotations

import json
import subprocess

import pytest


@pytest.mark.behavior
def test_policy_eval_cli_strict_blocks(project_root) -> None:
    proc = subprocess.run(
        [str(project_root / "scripts" / "cos-policy-eval"), "--project-dir", str(project_root), "--tool", "Bash", "--command", "rm -rf /*", "--json", "--strict"],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["decision"] == "block"
