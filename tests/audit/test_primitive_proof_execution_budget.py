#!/usr/bin/env python3
# SCOPE: os-only
"""Ratchet on registry rows whose paired proof never executes the primitive.

Companion gate for scripts/primitive_proof_execution_audit.py. Three contracts:

1. POPULATION GUARD — an empty scan is a broken scan, not a green one. A budget
   audit that passes because it found nothing is the failure mode this suite has
   already shipped twice, so the guard is asserted before the number is.
2. RATCHET — the measured count may not exceed the budget recorded in
   manifests/primitive-scope-classification.yaml, and the budget itself may not
   be raised above the value this test pins.
3. BITE — a synthetic row that does not execute its primitive must turn the
   audit red. A ratchet that cannot be made to fail is decoration.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = REPO_ROOT / "scripts" / "primitive_proof_execution_audit.py"
MANIFEST = REPO_ROOT / "manifests" / "primitive-scope-classification.yaml"

# Ratchet ceiling. Measured on HEAD 2026-08-18 with:
#   git archive HEAD | tar -x -C <dir>
#   python3 scripts/primitive_proof_execution_audit.py --project-dir <dir>
# -> rows_without_execution: 890 of 1441 rows.
# This constant may only ever be LOWERED. Raising it means accepting more proofs
# that never run their primitive, which is the thing being ratcheted down.
RATCHET_CEILING = 890

# Below this the scan is not measuring the registry any more.
MIN_EXPECTED_ROWS = 1000


def _load_audit():
    spec = importlib.util.spec_from_file_location("primitive_proof_execution_audit", AUDIT_PATH)
    assert spec and spec.loader, AUDIT_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules["primitive_proof_execution_audit"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit():
    return _load_audit()


@pytest.fixture(scope="module")
def rows(audit):
    return audit.build_rows(REPO_ROOT)


def test_population_guard_scan_actually_found_the_registry(rows) -> None:
    """A green budget over an empty population proves nothing about the repo."""
    assert len(rows) >= MIN_EXPECTED_ROWS, (
        f"execution audit scanned only {len(rows)} rows; the registry has >{MIN_EXPECTED_ROWS}. "
        "The scan is broken — do not read this suite as green."
    )
    classes = {row.execution_class for row in rows}
    assert "executes" in classes, "no row was classified as executing: the discriminator is dead"


def test_empty_population_is_a_finding_not_a_pass(audit, tmp_path: Path) -> None:
    """Falsification probe for the guard above, at the audit level."""
    findings = audit.budget_findings(tmp_path, [])
    assert [f.code for f in findings] == ["proof-execution-empty-population"], findings


def test_manifest_budget_is_not_raised_above_the_ratchet() -> None:
    policy = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    budget = (policy.get("proof_execution_budget") or {}).get("max_rows_without_execution")
    assert budget is not None, "proof_execution_budget.max_rows_without_execution is missing"
    assert int(budget) <= RATCHET_CEILING, (
        f"budget {budget} is above the ratchet ceiling {RATCHET_CEILING}. "
        "This number may only go down; raising it needs a written reason in the manifest "
        "and a matching change here, which is a deliberate act, not a green-fixing edit."
    )


def test_rows_without_execution_are_within_budget(audit, rows) -> None:
    findings = audit.budget_findings(REPO_ROOT, rows)
    count = len(audit.without_execution(rows))
    assert count <= RATCHET_CEILING, (
        f"{count} registry rows have a proof that never executes the primitive, "
        f"above the ratchet of {RATCHET_CEILING}. Write a proof that RUNS the primitive; "
        "do not raise the number."
    )
    assert [f.code for f in findings] == [], findings


def test_ratchet_bites_on_one_synthetic_non_executing_row(audit, rows) -> None:
    """Add a single row whose proof does not execute it: the audit must go red."""
    synthetic = replace(
        rows[0],
        path="scripts/synthetic-ratchet-probe.sh",
        execution_class="not-executed",
        evidence="synthetic probe: no execution site references this artifact",
    )
    codes = [f.code for f in audit.budget_findings(REPO_ROOT, list(rows) + [synthetic])]
    assert codes == ["proof-execution-budget-exceeded"], (
        "one extra non-executing row did not break the budget; the ratchet has slack in it"
    )
