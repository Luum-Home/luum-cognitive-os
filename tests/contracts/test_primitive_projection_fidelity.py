"""ADR-256 Phase 4 primitive projection fidelity report contracts."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "primitive_projection_fidelity.py"


def test_projection_fidelity_report_joins_registry_to_harness_coverage() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(REPO_ROOT), "--print-json", "--no-write"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)

    assert report["schema_version"] == "primitive-projection-fidelity.v1"
    assert report["summary"]["contracts"] >= 5
    by_id = {item["contract_id"]: item for item in report["items"]}
    assert {
        "destructive-git-blocker",
        "destructive-rm-blocker",
        "reinvention-check",
        "large-file-advisor",
        "skill-router",
    } <= set(by_id)

    git = by_id["destructive-git-blocker"]
    assert git["coverage_present"] is True
    projections = {row["harness"]: row for row in git["projection_fidelity"]}
    assert projections["claude"]["declared_fidelity"] == "native-lifecycle-enforced"
    assert projections["opencode"]["declared_fidelity"] == "governed-wrapper-enforced"
    assert projections["opencode"]["status"] == "aligned"
    assert "opencode-plugin-smoke" in projections["opencode"]["observed"]["evidence"]
    assert projections["cursor"]["status"] == "aligned"
    assert projections["cursor"]["declared_fidelity"] == "structural-advisory"


def test_projection_fidelity_does_not_convert_contracts_into_runtime_proof() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(REPO_ROOT), "--print-json", "--no-write"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)

    for item in report["items"]:
        for row in item["projection_fidelity"]:
            if row["declared_fidelity"] == "host-plugin-lifecycle-capable":
                assert row["status"] == "pending-runtime-smoke"
                assert row["observed"]["wired"] is False
            if row["declared_fidelity"] == "structural-advisory":
                assert row["status"] == "aligned"
                assert "enforced" not in row["status"]


def test_registry_impact_values_are_bounded_for_projection_reports() -> None:
    registry = yaml.safe_load((REPO_ROOT / "manifests" / "primitive-contracts.yaml").read_text(encoding="utf-8"))
    allowed_consumer = {"none", "install-update-risk", "unknown"}
    allowed_service = {"harness-embedded-only", "shell-ci-safe", "headless-worker-safe", "cosd-service-safe", "unsupported"}

    for contract in registry["contracts"]:
        impact = contract["impact"]
        assert impact["consumer_fleet"] in allowed_consumer, contract["id"]
        assert impact["service_mode"] in allowed_service, contract["id"]
