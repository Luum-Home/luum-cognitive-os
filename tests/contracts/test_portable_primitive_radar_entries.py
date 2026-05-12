"""Portable primitive radar entries stay connected to ADR-258/ADR-256 work."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "external-tools-adoption.yaml"
ADDENDUM = REPO_ROOT / "docs" / "reports" / "external-tools-radar-portable-primitives-addendum-2026-05-09.md"
INDEX = REPO_ROOT / "docs" / "reports" / "external-tools-radar-INDEX.md"
ECOSYSTEM = REPO_ROOT / "docs" / "patterns" / "ecosystem-tools.md"

REQUIRED = {
    "versa-dotaislash": ("ASSESS", "trial-overlay-standard"),
    "agent-skills-ecosystem": ("ASSESS", "conformance-reference"),
    "zed-acp": ("ASSESS", "adapter-runtime-transport"),
    "opencode-permissions-plugins": ("TRIAL", "adapter-design"),
    "open-agent-passport-preaction-auth": ("MONITOR", "ledger-hardening-pattern"),
}


def _tools() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return {str(row["id"]): row for row in data["tools"]}


def test_missing_portable_primitive_tools_are_registered_as_non_dependencies() -> None:
    tools = _tools()
    assert set(REQUIRED) <= set(tools)
    for tool_id, (verdict, adoption_kind) in REQUIRED.items():
        row = tools[tool_id]
        assert row["verdict"] == verdict
        assert row["adoption_kind"] == adoption_kind
        assert row["package_names"] == []
        assert row["allowed_surfaces"] == {
            "os_repo": False,
            "consumer_projects": False,
            "service_mode": False,
            "docker_runtime": False,
        }
        assert row["source_of_truth"]["radar_report"] == "docs/06-Daily/reports/external-tools-radar-portable-primitives-addendum-2026-05-09.md"


def test_radar_addendum_and_indexes_link_all_required_entries() -> None:
    addendum = ADDENDUM.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    ecosystem = ECOSYSTEM.read_text(encoding="utf-8")
    for token in [
        "VERSA / dotAIslash",
        "Agent Skills ecosystem",
        "Zed Agent Client Protocol",
        "OpenCode permissions/plugins",
        "Open Agent Passport / pre-action authorization",
    ]:
        assert token in addendum
    assert ADDENDUM.name in index
    assert "Portable Primitive Standards and Adapter Runtime Tools" in ecosystem
