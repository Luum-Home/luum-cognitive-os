# SCOPE: both
"""Portability probes for lib/dspy_pilot.py — W3-2 DSPy structured-skill pilot.

Bilateral assertion: importing the module and invoking build_pilot_report() works
identically on any harness that has python3 + the COS repo on disk, regardless
of whether the optional `dspy` dependency is installed. The report shape is
schema-stable (`dspy-structured-skill-pilot/v1`).

Falsification probes:
  - The pilot must NOT silently claim DSPy is available when it is not, and the
    status field must reflect the dependency state.
  - The signature dict must contain the documented sdd-verify inputs/outputs;
    a stub returning empty signatures would fail the test.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.dspy_pilot import (  # noqa: E402
    build_pilot_report,
    dspy_available,
    sdd_verify_signature,
)


def test_pilot_report_runs_and_returns_versioned_payload() -> None:
    """Bilateral: build_pilot_report returns a versioned dict on any harness."""
    report = build_pilot_report("sdd-verify").to_dict()
    assert report["schema_version"] == "dspy-structured-skill-pilot/v1"
    assert report["target_skill"] == "sdd-verify"
    assert report["status"] in {"ready", "dependency-missing"}
    assert report["router_touched"] is False
    assert isinstance(report["signature"], dict)


def test_pilot_status_is_consistent_with_dspy_availability() -> None:
    """Falsification: status must mirror real dspy_available() — no silent lying."""
    available = dspy_available()
    report = build_pilot_report().to_dict()
    assert report["dspy_available"] is available
    expected = "ready" if available else "dependency-missing"
    assert report["status"] == expected, (
        f"falsification: pilot claims status={report['status']} but "
        f"dspy_available={available}"
    )


def test_signature_contains_documented_sdd_verify_io() -> None:
    """Falsification: empty/wrong signature would fail — proves real contract."""
    sig = sdd_verify_signature()
    assert "spec_markdown" in sig["inputs"]
    assert "implementation_diff" in sig["inputs"]
    assert "test_evidence" in sig["inputs"]
    assert "verdict" in sig["outputs"]
    assert "missing_acceptance" in sig["outputs"]
