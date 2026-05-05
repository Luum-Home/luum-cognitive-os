from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import acc_pipeline  # noqa: E402


def test_acc_loads_proof_drill_evidence_as_aligned_capabilities() -> None:
    status, capabilities, findings = acc_pipeline.load_proof_drill_evidence(REPO)

    assert status.status == "ok"
    ids = {cap.id for cap in capabilities}
    assert "proof_drill:headless-codex-provider-smoke" in ids
    assert "proof_drill:headless-docker-service-drill" in ids
    assert all(cap.mapping_status == "aligned" for cap in capabilities)
    assert findings == []


def test_acc_proof_drill_evidence_summary_counts_passed_rows() -> None:
    status, capabilities, _findings = acc_pipeline.load_proof_drill_evidence(REPO)

    proof_capabilities = [cap for cap in capabilities if cap.kind == "proof_drill"]
    assert status.summary["status_counts"]["passed"] == len(proof_capabilities)
    codex = next(cap for cap in proof_capabilities if cap.id == "proof_drill:headless-codex-provider-smoke")
    assert codex.risk == "high"
    assert any("COS_CODEX_EXEC_MODEL" in item for item in codex.evidence)
