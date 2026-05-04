from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "primitive_readiness_ledger.py"
REPORT = REPO_ROOT / "docs" / "reports" / "primitive-readiness-ledger-scripts-latest.json"


def test_repository_script_ledger_classifies_every_script() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO_ROOT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(REPORT.read_text())
    scripts = [path for path in (REPO_ROOT / "scripts").rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    ignored_suffixes = {".pyc"}
    script_count = sum(1 for path in scripts if path.suffix not in ignored_suffixes)
    assert payload["summary"]["total_scripts"] == script_count
    assert "consumer_accessibility" in payload["summary"]
    assert all(row["role"] in payload["allowed_roles"] for row in payload["scripts"])
    assert all(row["consumer_accessibility"] for row in payload["scripts"])
    assert all(row["consumer_access_next_action"] for row in payload["scripts"])
    assert not any(row["role"] == "unknown" for row in payload["scripts"])
