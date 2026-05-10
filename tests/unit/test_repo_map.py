from __future__ import annotations

from lib.repo_map import build_repo_map


def test_repo_map_respects_budget_and_includes_changed_file(project_root) -> None:
    packet = build_repo_map(project_root, "engram memory ppr", max_tokens=250, changed_files=["lib/engram_lifecycle.py"])
    data = packet.to_dict()
    assert data["schema_version"] == "repo-map-context-selector/v1"
    assert data["budget"]["estimated_tokens"] <= data["budget"]["max_tokens"]
    assert any(row["path"] == "lib/engram_lifecycle.py" for row in data["code_symbols"])


def test_repo_map_exposes_governance_sections(project_root) -> None:
    packet = build_repo_map(project_root, "primitive hooks manifests", max_tokens=800)
    assert set(packet.governance) == {"hooks", "skills", "rules", "manifests"}
