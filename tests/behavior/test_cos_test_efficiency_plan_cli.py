from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.behavior
def test_cos_test_efficiency_plan_cli_outputs_commands() -> None:
    proc = subprocess.run(
        [str(PROJECT_ROOT / "scripts/cos-test-efficiency-plan"), "--project-dir", str(PROJECT_ROOT), "--changed-file", "lib/dispatch.py", "--commands", "--include-final-laptop"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert lines[0].startswith("python3 -m py_compile")
    assert lines[-1].startswith("scripts/cos-test-repair-loop")
    assert "make test-laptop" in lines[-1]


@pytest.mark.behavior
def test_cos_test_efficiency_plan_cli_failure_file(tmp_path: Path) -> None:
    failure = tmp_path / "fail.log"
    failure.write_text("FAILED tests/unit/test_example.py::test_a - AssertionError\n")
    proc = subprocess.run(
        [str(PROJECT_ROOT / "scripts/cos-test-efficiency-plan"), "--project-dir", str(PROJECT_ROOT), "--failure-file", str(failure)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["lanes"][0]["name"] == "failed-nodeids"
