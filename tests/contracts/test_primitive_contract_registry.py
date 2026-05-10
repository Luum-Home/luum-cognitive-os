"""ADR-256 / ADR-257 primitive contract registry contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "manifests" / "primitive-contracts.yaml"
HARNESS_PROJECTION = REPO_ROOT / "manifests" / "harness-projection.yaml"

REQUIRED_INITIAL_IDS = {
    "destructive-git-blocker",
    "destructive-rm-blocker",
    "reinvention-check",
    "large-file-advisor",
    "skill-router",
}

REQUIRED_PROJECTION_HARNESSES = {
    "claude",
    "codex",
    "opencode",
    "cursor",
    "vscode-copilot",
    "shell-ci",
}

ALLOWED_FIDELITY = {
    "native-lifecycle-enforced",
    "governed-wrapper-enforced",
    "host-plugin-lifecycle-capable",
    "structural-advisory",
    "ci-enforced",
    "documented-only",
    "unsupported",
}

ENFORCEMENT_FIDELITY = {
    "native-lifecycle-enforced",
    "governed-wrapper-enforced",
    "ci-enforced",
}

STRUCTURAL_ADVISORY_ONLY = {"cursor", "vscode-copilot"}


def _registry() -> dict[str, Any]:
    assert REGISTRY.exists(), "ADR-256 Phase 1 requires manifests/primitive-contracts.yaml"
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _contracts() -> list[dict[str, Any]]:
    data = _registry()
    contracts = data.get("contracts")
    assert isinstance(contracts, list) and contracts
    return contracts


def test_primitive_contract_registry_schema_and_initial_ids() -> None:
    data = _registry()
    assert data.get("schema_version") == "primitive-contracts.v1"
    assert set(data.get("fidelity_levels", {})) >= ALLOWED_FIDELITY

    contracts = _contracts()
    ids = [contract.get("id") for contract in contracts]
    assert len(ids) == len(set(ids)), "primitive contract ids must be unique"
    assert REQUIRED_INITIAL_IDS <= set(ids)


def test_primitive_contract_rows_have_required_portable_fields() -> None:
    for contract in _contracts():
        contract_id = contract.get("id")
        for key in [
            "id",
            "family",
            "source",
            "intent",
            "trigger",
            "requires",
            "actions",
            "evidence",
            "projection",
            "impact",
        ]:
            assert key in contract, f"{contract_id}: missing {key}"

        source = REPO_ROOT / str(contract["source"])
        assert source.exists(), f"{contract_id}: source path does not exist: {source}"
        for ref in contract.get("implementation_refs", []):
            assert (REPO_ROOT / str(ref)).exists(), f"{contract_id}: implementation ref missing: {ref}"

        assert isinstance(contract["requires"], list) and contract["requires"], contract_id
        assert "emit_intervention" in contract["requires"], contract_id
        assert contract["trigger"].get("kind"), contract_id
        assert contract["actions"].get("preferred") in {
            "block",
            "warn",
            "advise",
            "suggest",
            "observe",
            "allow",
            "execute",
        }, contract_id
        assert contract["actions"].get("reason_codes"), contract_id

        evidence = contract["evidence"]
        assert evidence.get("interventions") == [".cognitive-os/metrics/primitive-interventions.jsonl"], contract_id
        assert evidence.get("proof_tests"), contract_id
        for proof in evidence["proof_tests"]:
            assert (REPO_ROOT / str(proof)).exists(), f"{contract_id}: proof test missing: {proof}"


def test_primitive_contracts_declare_required_harness_fidelity() -> None:
    for contract in _contracts():
        contract_id = contract["id"]
        projection = contract["projection"]
        assert REQUIRED_PROJECTION_HARNESSES <= set(projection), contract_id
        for harness, row in projection.items():
            fidelity = row.get("fidelity")
            assert fidelity in ALLOWED_FIDELITY, f"{contract_id}/{harness}: invalid fidelity {fidelity}"
            assert row.get("surface"), f"{contract_id}/{harness}: projection surface is required"


def test_structural_only_ide_harnesses_do_not_claim_enforcement() -> None:
    harness_manifest = yaml.safe_load(HARNESS_PROJECTION.read_text(encoding="utf-8"))
    by_harness = {item["id"]: item for item in harness_manifest["harnesses"]}

    for harness in STRUCTURAL_ADVISORY_ONLY:
        assert by_harness[harness]["proof_level"] == "structural"

    for contract in _contracts():
        for harness in STRUCTURAL_ADVISORY_ONLY:
            fidelity = contract["projection"][harness]["fidelity"]
            assert fidelity == "structural-advisory", (
                f"{contract['id']}/{harness} must stay structural-advisory until "
                "a native, governed-wrapper, or plugin runtime adapter is signed"
            )
            assert fidelity not in ENFORCEMENT_FIDELITY


def test_opencode_enforcement_claims_are_limited_to_signed_plugin_smoke_slice() -> None:
    signed = {
        "destructive-git-blocker",
        "destructive-rm-blocker",
        "reinvention-check",
        "large-file-advisor",
        "skill-router",
        "aci-observation-capture",
        "adr-relevance-suggest",
        "adr-section-validator",
        "agent-bash-cwd-enforcer",
        "agent-control-inbound-guard",
        "auto-rollback-trigger",
        "auto-verify",
        "claim-validator",
        "confidence-gate",
        "confidentiality-enforcer",
        "content-policy",
        "context-watchdog",
        "cosd-auth-guard",
        "dispatch-gate",
        "doc-sync-detector",
    }
    for contract in _contracts():
        fidelity = contract["projection"]["opencode"]["fidelity"]
        if contract["id"] in signed:
            assert fidelity == "governed-wrapper-enforced", contract["id"]
            assert "cos-primitive-guard.js" in contract["projection"]["opencode"]["surface"]
        else:
            assert fidelity == "structural-advisory", contract["id"]
            assert fidelity not in ENFORCEMENT_FIDELITY
