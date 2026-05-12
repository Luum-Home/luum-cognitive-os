from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "primitive_authority_audit.py"


def test_current_dynamic_authority_smokes_pass_without_writing_reports() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO), "--json", "--no-write"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=90,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "pass"
    assert report["summary"]["dynamic_smokes"] >= 4
    assert report["summary"]["dynamic_blocks"] == 0
    assert {row["id"] for row in report["dynamic_smokes"]} >= {
        "consumer-improvement-export",
        "consumer-improvement-import",
        "project-shell-ci",
        "cos-init-codex",
    }
