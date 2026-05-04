from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "acc_pipeline.py"
REPORT = REPO_ROOT / "docs" / "acc" / "latest.json"


def test_repository_acc_pipeline_generates_report() -> None:
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
    assert payload["schema_version"] == "acc.report.v1"
    assert payload["capabilities"]
    assert payload["mapping_statuses"] == ["aligned", "missing", "overexposed", "partial", "stale", "unverified"]
    assert "consumer_accessibility" in payload["capabilities"][0]
    assert "persistence" in payload
    assert payload["persistence"]["engram"]["status"] in {"unavailable", "ok"}
    for adapter in ("readiness:scripts", "readiness:hooks", "readiness:skills", "readiness:rules"):
        assert payload["adapters"][adapter]["status"] == "ok"
