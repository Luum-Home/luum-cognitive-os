from __future__ import annotations

from pathlib import Path

from lib.feature_tool_due_diligence import deepwiki_url_for_github, fetch_external_source, scan_due_diligence

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifests" / "feature-tool-due-diligence.yaml"
CAPS = ROOT / "manifests" / "capability-coverage.yaml"


def test_deepwiki_url_derived_from_github_owner_repo() -> None:
    assert deepwiki_url_for_github("https://github.com/getzep/graphiti") == "https://deepwiki.com/getzep/graphiti"
    assert deepwiki_url_for_github("https://github.com/HKUDS/LightRAG.git") == "https://deepwiki.com/HKUDS/LightRAG"


def test_feature_tool_scan_warns_for_legacy_missing_records_but_does_not_block_seeded_records() -> None:
    report = scan_due_diligence(ROOT, MANIFEST, CAPS)

    assert report["status"] == "warn"
    assert report["summary"]["block"] == 0
    assert report["summary"]["records"] >= 3
    missing = {finding["capability_id"] for finding in report["findings"] if finding["code"] == "missing-feature-due-diligence"}
    assert "skill-router-retrieval-boundary" not in missing
    assert "agent-orchestration-boundary" not in missing
    assert "capability-coverage-matrix" not in missing


def test_external_source_fetch_plan_uses_gitignored_cache_without_cloning() -> None:
    report = fetch_external_source(ROOT, MANIFEST, "https://github.com/ossf/scorecard", execute=False)

    assert report["status"] == "planned"
    assert report["executed"] is False
    assert report["deepwiki_url"] == "https://deepwiki.com/ossf/scorecard"
    assert ".cognitive-os/external-source-cache" in report["target"]
