"""Invariant tests for auto-derived primitive routing (ADR-174)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib.skill_router import (
    SkillRouter,
    _detect_skill_md_paths,
    _load_routing_from_frontmatter,
)

pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "skill-routing-coverage.yaml"
POC_FRONTMATTER_SKILLS = {
    "add-skill",
    "audit-integrity",
    "code-review",
    "component-reality-check",
    "cognitive-os-init",
}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def _manifest_skill_set(key: str) -> set[str]:
    return {str(row["skill"]) for row in _manifest().get(key, [])}


def _is_repository_skill_path(skill_md: Path) -> bool:
    try:
        rel = skill_md.relative_to(PROJECT_ROOT)
    except ValueError:
        return False
    return rel.parts[:1] == ("skills",) or rel.parts[:1] == ("packages",)


def _repository_detected_skill_md_paths() -> dict[str, Path]:
    return {
        name: path
        for name, path in _detect_skill_md_paths(PROJECT_ROOT).items()
        if _is_repository_skill_path(path)
    }


def _skills_on_disk() -> set[str]:
    return set(_repository_detected_skill_md_paths())


def _repository_primary_routing_skills() -> set[str]:
    runtime_names = set(_detect_skill_md_paths(PROJECT_ROOT)) - _skills_on_disk()
    return SkillRouter().get_primary_routing_skills() - runtime_names


def test_frontmatter_loader_discovers_adr_174_poc_skills() -> None:
    """ADR-174 proof-of-concept skills must be routed from SKILL.md frontmatter."""
    entries = _load_routing_from_frontmatter(PROJECT_ROOT)
    loaded = {entry.skill_name for entry in entries}

    missing = sorted(POC_FRONTMATTER_SKILLS - loaded)
    assert missing == [], (
        "ADR-174 frontmatter routing proof-of-concept skills were not loaded: "
        f"{missing}"
    )


def test_no_unclassified_primary_router_orphans() -> None:
    """Primary router entries must resolve to disk skills or manifest-declared meta-commands."""
    disk_skills = _skills_on_disk()
    primary_skills = _repository_primary_routing_skills()
    meta_commands = _manifest_skill_set("primary_router_orphan_allowlist")

    unexpected_orphans = sorted(primary_skills - disk_skills - meta_commands)
    assert unexpected_orphans == [], (
        "Unexpected primary SkillRouter entries without SKILL.md or manifest "
        f"meta-command classification: {unexpected_orphans}"
    )

    stale_meta_commands = sorted(meta_commands & disk_skills)
    assert stale_meta_commands == [], (
        "Meta-command allowlist entries now have SKILL.md files; remove their "
        f"manifest exceptions: {stale_meta_commands}"
    )


def test_router_coverage_threshold_matches_manifest_baseline() -> None:
    """Global/full-surface routeability must not fall below manifest baseline."""
    disk_skills = _skills_on_disk()
    if not disk_skills:
        pytest.skip("No SKILL.md files found on disk")

    primary_skills = _repository_primary_routing_skills()
    routed_on_disk = disk_skills & primary_skills
    baseline = _manifest()["baseline"]
    min_count = int(baseline["min_routed_skill_count"])
    min_coverage = float(baseline["min_routed_skill_coverage_percent"])
    coverage = (len(routed_on_disk) / len(disk_skills)) * 100

    assert len(routed_on_disk) >= min_count, (
        f"Routed skill count regressed: {len(routed_on_disk)} < {min_count}"
    )
    assert coverage >= min_coverage, (
        f"SkillRouter coverage regressed: {coverage:.1f}% < {min_coverage:.1f}% "
        f"({len(routed_on_disk)}/{len(disk_skills)})"
    )
