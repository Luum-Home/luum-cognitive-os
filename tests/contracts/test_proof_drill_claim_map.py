from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CLAIM_MAP = REPO / "manifests" / "proof-drill-claim-map.yaml"
REGISTRY = REPO / "manifests" / "proof-drill-registry.yaml"
REQUIRED_FIELDS = {
    "id",
    "proof_drill_id",
    "claim",
    "scope",
    "risk",
    "consumer_accessibility",
    "lifecycle_status",
    "status_when_passed",
    "docs",
}


def _claim_map() -> dict:
    return yaml.safe_load(CLAIM_MAP.read_text(encoding="utf-8"))


def _registry_ids() -> set[str]:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    return {entry["id"] for entry in registry["entries"]}


def test_proof_drill_claim_map_schema_and_references() -> None:
    data = _claim_map()
    assert data["schema_version"] == "proof-drill-claim-map.v1"
    assert data["claims"]
    registry_ids = _registry_ids()
    claim_ids: set[str] = set()
    for claim in data["claims"]:
        assert REQUIRED_FIELDS <= set(claim), claim.get("id")
        assert claim["id"] not in claim_ids, claim["id"]
        claim_ids.add(claim["id"])
        assert claim["proof_drill_id"] in registry_ids, claim["id"]
        assert claim["scope"] in {"os-self", "consumer-project", "both"}, claim["id"]
        assert claim["risk"] in {"low", "medium", "high", "critical"}, claim["id"]
        assert claim["status_when_passed"] == "aligned", claim["id"]
        for doc in claim["docs"]:
            assert (REPO / doc).exists(), f"missing claim doc for {claim['id']}: {doc}"
