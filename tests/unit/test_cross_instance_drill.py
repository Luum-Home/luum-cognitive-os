"""Tests for manual cross-instance drills."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.cos_cross_instance_drill import (
    drill_engram_conflict,
    drill_external_evidence,
    drill_registry_drift,
    drill_shape_b_governance,
    drill_shape_b_trigger,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_external_evidence_drill_signs_only_temp_manifest() -> None:
    result = drill_external_evidence(PROJECT_ROOT)

    assert result["status"] == "pass"
    assert result["mutates_real_manifest"] is False
    assert result["helps_projects_signed_in_temp_manifest"] is True


def test_shape_b_trigger_drill_fires_temp_config() -> None:
    result = drill_shape_b_trigger()

    assert result["status"] == "triggered"
    assert result["shape"] == "Shape B"
    assert result["mutates_real_manifest"] is False


def test_registry_drift_drill_detects_drift_without_real_locks() -> None:
    result = drill_registry_drift(PROJECT_ROOT)

    assert result["status"] == "pass"
    assert result["drift_detected"] is True
    assert result["mutates_real_locks"] is False


def test_engram_conflict_drill_is_propose_only() -> None:
    result = drill_engram_conflict()

    assert result["status"] == "pass"
    assert result["mutates_memory_store"] is False
    assert result["proposal"]["runtime_effect"] == "none"
    assert result["conflict_detected"] is True


def test_shape_b_governance_drill_writes_checklist_only() -> None:
    result = drill_shape_b_governance()

    assert result["status"] == "pass"
    assert result["mutates_real_governance"] is False
    assert result["required_items"] >= 6


def test_cli_all_drills_pass() -> None:
    proc = subprocess.run(
        ["scripts/cos-cross-instance-drill", "--scenario", "all"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["mutates_real_evidence"] is False
