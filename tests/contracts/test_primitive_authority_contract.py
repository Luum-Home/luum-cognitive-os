from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "primitive-authority.yaml"
DOC = REPO / "docs" / "04-Concepts" / "architecture" / "primitive-authority-write-effects.md"
ADR = REPO / "docs" / "02-Decisions" / "adrs" / "ADR-276-primitive-authority-write-effects.md"
VALID_MODES = {
    "observe-only",
    "propose-only",
    "project-local-write",
    "os-maintainer-write",
    "profile-projection-write",
    "dangerous-human-approved",
}


def test_primitive_authority_manifest_schema_and_docs_exist() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    assert data["schema_version"] == "primitive-authority.v1"
    assert data["owner_adr"] == "ADR-276"
    assert set(data["authority_modes"]) == VALID_MODES
    assert data["entries"], "first ratchet needs explicit rows for high-risk surfaces"
    assert DOC.is_file()
    assert ADR.is_file()


def test_explicit_authority_entries_reference_existing_paths_and_valid_modes() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for item in data["entries"]:
        path = REPO / item["path"]
        assert path.exists(), f"authority entry path does not exist: {item['path']}"
        mode = item.get("authority", {}).get("mode")
        assert mode in VALID_MODES
        assert item.get("authority", {}).get("forbidden_write") is not None


def test_authority_manifest_names_derivation_inputs() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    inputs = set(data["derivation"]["inputs"])
    expected = {
        "manifests/primitive-scope-classification.yaml",
        "manifests/primitive-consumer-availability.yaml",
        "manifests/primitive-projection-profiles.yaml",
        "docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json",
        "manifests/protected-config-write-policy.yaml",
    }
    assert expected <= inputs
