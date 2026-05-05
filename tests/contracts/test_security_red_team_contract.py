"""Contract tests for the unified security-red-team primitive."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "security-red-team.yaml"
SKILL = REPO / "skills" / "security-red-team" / "SKILL.md"
RUNNER = REPO / "scripts" / "security_red_team.py"
SHIM = REPO / "scripts" / "security-red-team"
DOC = REPO / "docs" / "security" / "security-red-team.md"


def test_manifest_shape() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    assert data["schema_version"] == "security-red-team.v1"
    assert set(data["families"]) == {
        "surface-inventory",
        "threat-model",
        "abuse-probes",
        "primitive-scoring",
        "mitigation-backlog",
    }
    assert len(data["score_dimensions"]) == 8
    assert "credential_safe_integrity" in data["required_probes"]
    assert data["outputs"]["json"].endswith("security-red-team-latest.json")


def test_files_exist_and_reference_each_other() -> None:
    assert RUNNER.exists()
    assert SHIM.exists()
    assert SKILL.exists()
    assert DOC.exists()

    skill_text = SKILL.read_text(encoding="utf-8")
    runner_text = RUNNER.read_text(encoding="utf-8")
    doc_text = DOC.read_text(encoding="utf-8")

    assert "scripts/security-red-team" in skill_text
    assert "build_report" in runner_text
    assert "no direct reads" in doc_text


def test_catalog_mentions_security_red_team() -> None:
    catalog = (REPO / "skills" / "CATALOG.md").read_text(encoding="utf-8")

    assert "security-red-team" in catalog
    assert "/security-red-team" in catalog


def test_deferred_deep_mode_backlog_tracks_open_security_followups() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    backlog = {item["id"]: item for item in data["deferred_deep_mode_backlog"]}

    assert "deep-provider-metrics-audits" in backlog
    assert "docker-network-none-smoke" in backlog
    assert "mcp-pins-when-servers-exist" in backlog
    assert "expand-adversarial-security-scenarios" in backlog
    for item in backlog.values():
        assert item["description"]
        assert item["target_files"]
        assert item["acceptance"]


def test_security_red_team_docs_mention_deferred_deep_mode_backlog() -> None:
    doc_text = DOC.read_text(encoding="utf-8")
    skill_text = SKILL.read_text(encoding="utf-8")

    for needle in [
        "Provider/metrics audits in deep mode",
        "Real Docker no-network smoke",
        "MCP pins when servers exist",
        "Expanded adversarial scenarios",
    ]:
        assert needle in doc_text
    assert "deferred_deep_mode_backlog" in skill_text
