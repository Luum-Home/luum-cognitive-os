from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LANDSCAPE = REPO_ROOT / "manifests" / "ai-agent-harness-landscape.yaml"
PROJECTION = REPO_ROOT / "manifests" / "harness-projection.yaml"
IDE_COMPAT = REPO_ROOT / "docs" / "ide-compatibility.md"

REQUIRED_FIELDS = {
    "id",
    "display_name",
    "category",
    "status",
    "proof_level",
    "availability_boundary",
    "projection_surface",
    "official_sources",
    "next_action",
}

VALID_PROOF_LEVELS = {"native-lifecycle", "runtime-smoke", "structural", "none"}


def _landscape() -> dict:
    return yaml.safe_load(LANDSCAPE.read_text())


def test_landscape_candidates_have_required_metadata() -> None:
    data = _landscape()
    assert data["schema_version"] == "ai-agent-harness-landscape.v1"
    candidates = data["candidates"]
    assert len(candidates) >= 30

    ids = set()
    for candidate in candidates:
        missing = REQUIRED_FIELDS - set(candidate)
        assert not missing, f"{candidate.get('id', '<missing-id>')} missing {sorted(missing)}"
        assert candidate["id"] not in ids, candidate["id"]
        ids.add(candidate["id"])
        assert candidate["proof_level"] in VALID_PROOF_LEVELS, candidate["id"]
        assert isinstance(candidate["projection_surface"], list), candidate["id"]
        assert isinstance(candidate["official_sources"], list), candidate["id"]


def test_implemented_projection_harnesses_are_represented_in_landscape() -> None:
    landscape_ids = {item["id"] for item in _landscape()["candidates"]}
    projection = yaml.safe_load(PROJECTION.read_text())
    implemented_ids = {item["id"] for item in projection["harnesses"] if item["status"] == "implemented"}

    assert implemented_ids <= landscape_ids


def test_core_missing_harness_backlog_is_tracked() -> None:
    ids = {item["id"] for item in _landscape()["candidates"]}
    expected = {
        "gemini-cli",
        "kiro",
        "cline",
        "continue-dev",
        "aider",
        "goose",
        "jetbrains-junie",
        "amp-code",
        "warp",
        "factory-droid",
        "qoder",
        "tabnine-agent",
        "github-copilot-coding-agent",
        "minimax-mini-agent",
        "deepseek-provider",
    }
    assert expected <= ids


def test_ide_compatibility_uses_proof_levels_not_legacy_claims() -> None:
    text = IDE_COMPAT.read_text()
    forbidden = [
        "FULL COMPATIBILITY",
        "HIGH COMPATIBILITY",
        "COS Coverage",
        "70-90%",
        "100%",
        "all COS layers work",
    ]
    for phrase in forbidden:
        assert phrase not in text
    assert "proof levels" in text.lower()
    assert "does not claim COS works in every listed IDE/CLI" in text
