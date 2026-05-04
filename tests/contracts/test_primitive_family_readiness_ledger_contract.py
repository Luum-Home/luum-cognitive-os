from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "primitive_family_readiness_ledger.py"


def test_repository_family_ledgers_cover_hooks_skills_and_rules() -> None:
    for family in ("hooks", "skills", "rules"):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--project-dir", str(REPO_ROOT), "--target-family", family],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        report = REPO_ROOT / "docs" / "reports" / f"primitive-readiness-ledger-{family}-latest.json"
        payload = json.loads(report.read_text())
        assert payload["target_family"] == family
        assert payload["summary"]["total"] > 0
        assert "consumer_accessibility" in payload["summary"]
        assert all(item["role"] in payload["allowed_roles"] for item in payload["items"])
        assert all(item["consumer_accessibility"] for item in payload["items"])
        assert all(item["consumer_access_next_action"] for item in payload["items"])
