from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "remote-control-plane-alternatives.yaml"
REPORT = REPO_ROOT / "docs" / "06-Daily" / "reports" / "remote-control-plane-alternatives-2026-05-05.md"
ADR = REPO_ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-161-remote-control-plane-and-provider-adapter-boundary.md"

REQUIRED_PROJECT_FIELDS = {
    "id",
    "display_name",
    "source",
    "proof_level",
    "license_posture",
    "classifications",
    "remote_ingress",
    "provider_strategy",
    "credential_strategy",
    "source_urls",
    "notes",
}

VALID_LICENSE_POSTURES = {"allowed", "blocked", "review"}
VALID_PROOF_LEVELS = {"official-doc", "repo-readme", "local-doc", "unverified"}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text())


def test_remote_alternatives_manifest_contract() -> None:
    data = _manifest()
    assert data["schema_version"] == "remote-control-plane-alternatives.v1"
    assert str(data["review_date"]) == "2026-05-05"
    assert len(data["projects"]) >= 15

    ids: set[str] = set()
    for project in data["projects"]:
        missing = REQUIRED_PROJECT_FIELDS - set(project)
        assert not missing, f"{project.get('id', '<missing-id>')} missing {sorted(missing)}"
        assert project["id"] not in ids, project["id"]
        ids.add(project["id"])
        assert project["proof_level"] in VALID_PROOF_LEVELS, project["id"]
        assert project["license_posture"] in VALID_LICENSE_POSTURES, project["id"]
        assert isinstance(project["classifications"], list), project["id"]
        assert isinstance(project["remote_ingress"], list), project["id"]
        assert isinstance(project["source_urls"], list), project["id"]
        assert project["source_urls"], project["id"]


def test_core_remote_patterns_are_represented() -> None:
    by_id = {project["id"]: project for project in _manifest()["projects"]}
    expected = {
        "openclaw",
        "nanoclaw",
        "picoclaw",
        "zeroclaw-labs",
        "nullclaw",
        "ironclaw",
        "zeptoclaw",
        "opencode-current",
        "agent-zero",
    }
    assert expected <= set(by_id)
    assert "telegram" in by_id["openclaw"]["remote_ingress"]
    assert "http-server" in by_id["opencode-current"]["remote_ingress"]
    assert "cli-connector" in by_id["agent-zero"]["remote_ingress"]
    assert by_id["pinchy"]["license_posture"] == "blocked"


def test_report_and_adr_reference_manifest() -> None:
    report_text = REPORT.read_text()
    adr_text = ADR.read_text()
    assert "remote-control-plane-alternatives.yaml" in report_text
    assert "remote-control-plane-alternatives.yaml" in adr_text
    assert "No credential scraping" in report_text
    assert "remote ingress" in adr_text
