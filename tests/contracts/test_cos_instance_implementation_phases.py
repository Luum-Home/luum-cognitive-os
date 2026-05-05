from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASES = REPO_ROOT / "manifests" / "cos-instance-implementation-phases.yaml"
RUNBOOK = REPO_ROOT / ".cognitive-os" / "plans" / "architecture" / "cos-instance-installer-implementation-plan.md"

REQUIRED_PHASE_FIELDS = {
    "id",
    "title",
    "status",
    "proof_level",
    "profiles",
    "objective",
    "deliverables",
    "acceptance",
    "rollback",
}


def _phases() -> dict:
    return yaml.safe_load(PHASES.read_text())


def test_phase_manifest_contract() -> None:
    data = _phases()
    assert data["schema_version"] == "cos-instance-implementation-phases.v1"
    assert str(data["review_date"]) == "2026-05-05"
    assert len(data["phases"]) >= 9

    ids: set[str] = set()
    for phase in data["phases"]:
        missing = REQUIRED_PHASE_FIELDS - set(phase)
        assert not missing, f"{phase.get('id', '<missing-id>')} missing {sorted(missing)}"
        assert phase["id"] not in ids
        ids.add(phase["id"])
        assert isinstance(phase["deliverables"], list)
        assert isinstance(phase["acceptance"], list)
        assert phase["rollback"]


def test_phase_order_keeps_provider_smoke_after_bridge_contract() -> None:
    phases = _phases()["phases"]
    order = {phase["id"]: index for index, phase in enumerate(phases)}
    assert order["phase-3-host-cli-bridge-design"] < order["phase-4-host-cli-bridge-non-provider-smoke"]
    assert order["phase-4-host-cli-bridge-non-provider-smoke"] < order["phase-5-host-provider-smoke"]
    assert order["phase-5-host-provider-smoke"] < order["phase-6-remote-ingress-lab"]


def test_planned_profiles_and_provider_gates_are_explicit() -> None:
    data = _phases()
    assert data["gates"]["host_cli_bridge_provider_call_blocked_until_phase_5"] is True
    assert data["gates"]["remote_ingress_direct_execution_blocked"] is True
    assert data["gates"]["credential_store_copy_blocked"] is True
    assert set(data["gates"]["planned_profiles_write_blocked"]["profiles"]) == {"host-cli-bridge", "vm", "k8s"}


def test_runbook_references_phase_manifest_and_next_slice() -> None:
    text = RUNBOOK.read_text()
    assert "manifests/cos-instance-implementation-phases.yaml" in text
    assert "Phase 2" in text
    assert "Provider execution remains blocked until Phase 5" in text
