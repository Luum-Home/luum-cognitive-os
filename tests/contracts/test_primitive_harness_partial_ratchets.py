from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
COVERAGE_SCRIPT = REPO / "scripts" / "primitive_harness_coverage.py"
PARTIALS_SCRIPT = REPO / "scripts" / "primitive_harness_partials.py"
COVERAGE_REPORT = REPO / "docs" / "reports" / "primitive-harness-coverage-latest.json"
PARTIALS_REPORT = REPO / "docs" / "reports" / "primitive-harness-partials-latest.json"


def test_primitive_harness_partial_debt_does_not_regress() -> None:
    subprocess.run(
        ["python3", str(COVERAGE_SCRIPT), "--project-dir", str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    subprocess.run(
        ["python3", str(PARTIALS_SCRIPT), "--project-dir", str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )

    coverage = json.loads(COVERAGE_REPORT.read_text(encoding="utf-8"))
    partials = json.loads(PARTIALS_REPORT.read_text(encoding="utf-8"))

    assert coverage["summary"].get("unclassified_gaps", 0) == 0
    assert coverage["summary"].get("gaps_by_policy", {}).get("must-fix-parity", 0) == 0
    assert partials["summary"].get("partial_count", 0) <= 87
    assert partials["summary"].get("by_policy", {}).get("codex-adapter-needed", 0) <= 74
