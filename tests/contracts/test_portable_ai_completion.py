"""ADR-258 completion contracts for derived portable rows and consumer impact."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = REPO_ROOT / ".ai"


def _primitive_rows() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted((OVERLAY / "primitives").glob("**/*.json"))]


def test_every_ai_primitive_has_a_portable_contract_view() -> None:
    rows = _primitive_rows()
    assert rows
    assert all(row["portable_contract"]["is_full_contract"] is True for row in rows)
    sources = {row["portable_contract"]["source"] for row in rows}
    assert "primitive-contract-registry" in sources
    assert "primitive-lifecycle-derived" in sources
    for row in rows:
        contract = row["portable_contract"]
        assert contract["intent"]
        assert contract["requires"]
        assert contract["trigger"]["kind"]
        assert contract["actions"]["preferred"]
        assert "consumer_fleet" in contract["impact"]
        assert "service_mode" in contract["impact"]


def test_adapter_manifests_are_generated_for_profiles() -> None:
    profiles = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((OVERLAY / "profiles").glob("*.json"))]
    assert profiles
    for profile in profiles:
        manifest = OVERLAY / profile["adapter_directory"] / "adapter.json"
        assert manifest.exists(), manifest
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["schema_version"] == "portable-ai-adapter.v1"
        assert data["harness"] == profile["harness"]
        assert data["projected_primitive_count"] == len(data["projected_primitives"])
        assert "never upgrade advisory" in data["fidelity_policy"]


def test_portable_ai_consumer_impact_report_is_read_only_and_blocks_canonical_migration() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-portable-ai-consumer-impact"), "--project-dir", str(REPO_ROOT), "--no-write", "--json"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
    )
    report = json.loads(result.stdout)
    assert report["schema_version"] == "portable-ai-consumer-impact.v1"
    assert report["overlay"]["file_count"] >= 300
    assert report["overlay"]["adapter_file_count"] >= report["overlay"]["profile_file_count"]
    assert report["decision"]["mutates_consumers"] is False
    assert report["decision"]["canonical_migration_allowed"] is False
