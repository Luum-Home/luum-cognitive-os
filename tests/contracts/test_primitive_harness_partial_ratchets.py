from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
COVERAGE_SCRIPT = REPO / "scripts" / "primitive_harness_coverage.py"
PARTIALS_SCRIPT = REPO / "scripts" / "primitive_harness_partials.py"

# --- Debt ratchets ---------------------------------------------------------
# These are the current known-debt ceilings for partial harness coverage.
# They may only ever be LOWERED (as partial rows get resolved), never RAISED.
# Raising either constant to make a failing test pass is a regression in
# disguise and must be treated as a rejected change, not a routine bump.
MAX_PARTIAL_COUNT = 77
MAX_CODEX_ADAPTER_NEEDED_PARTIALS = 59


def test_primitive_harness_partial_debt_does_not_regress(tmp_path: Path) -> None:
    # Regenerate-and-compare: both reports are written to tmp_path instead of
    # the checked-in docs/06-Daily/reports/ snapshot, so this test evaluates
    # fresh generator output rather than a potentially stale, checked-in copy.
    coverage_report = tmp_path / "primitive-harness-coverage-latest.json"
    partials_report = tmp_path / "primitive-harness-partials-latest.json"

    subprocess.run(
        [
            "python3",
            str(COVERAGE_SCRIPT),
            "--project-dir",
            str(REPO),
            "--json-out",
            str(coverage_report),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    subprocess.run(
        [
            "python3",
            str(PARTIALS_SCRIPT),
            "--project-dir",
            str(REPO),
            "--coverage-json",
            str(coverage_report),
            "--json-out",
            str(partials_report),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )

    coverage = json.loads(coverage_report.read_text(encoding="utf-8"))
    partials = json.loads(partials_report.read_text(encoding="utf-8"))

    assert coverage["summary"].get("unclassified_gaps", 0) == 0
    assert coverage["summary"].get("gaps_by_policy", {}).get("must-fix-parity", 0) == 0
    assert partials["summary"].get("partial_count", 0) <= MAX_PARTIAL_COUNT
    assert partials["summary"].get("by_policy", {}).get("codex-adapter-needed", 0) <= MAX_CODEX_ADAPTER_NEEDED_PARTIALS
