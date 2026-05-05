from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import acc_pipeline  # noqa: E402


def test_acc_maps_proof_drill_evidence_to_claim_capabilities() -> None:
    status, capabilities, findings = acc_pipeline.load_proof_drill_evidence(REPO)

    assert status.status == "ok"
    assert status.summary["claim_map"]["claims"] >= 4
    claim_ids = {cap.id for cap in capabilities if cap.kind == "proof_claim"}
    assert "proof_claim:host-claude-provider-adapter" in claim_ids
    assert "proof_claim:host-codex-provider-adapter" in claim_ids
    assert "proof_claim:headless-docker-local-command-runtime" in claim_ids
    assert not [finding for finding in findings if finding.capability_id.startswith("proof_claim:")]


def test_missing_claim_evidence_becomes_unverified() -> None:
    status, capabilities, findings = acc_pipeline.load_proof_drill_claim_map(REPO, {})

    assert status.status == "ok"
    assert any(cap.mapping_status == "unverified" for cap in capabilities)
    assert any(finding.status == "unverified" for finding in findings)
