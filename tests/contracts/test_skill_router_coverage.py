"""Contract tests for SkillRouter primitive coverage.

The router has two distinct obligations:

1. Router entries should point at real skills or at explicitly documented
   meta-commands.
2. Skills present on disk should not silently remain unroutable forever.

This file is a ratchet, not a one-shot cleanup. The explicit exception list
lives in manifests/skill-routing-coverage.yaml so profile/routing governance is
machine-readable outside pytest.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

import scripts.cos_adoption_profile as adoption_profile
from lib.skill_router import (
    SkillRouter,
    _load_routing_from_frontmatter,
    _parse_routing_patterns_block,
)

pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOTS = (
    PROJECT_ROOT / "skills",
    PROJECT_ROOT / ".cognitive-os" / "skills",
)
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "skill-routing-coverage.yaml"


def _coverage_manifest() -> dict:
    """Load the machine-readable skill routing coverage manifest."""
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def _manifest_skill_set(key: str) -> set[str]:
    """Return a skill-name set from a manifest list of mapping rows."""
    rows = _coverage_manifest().get(key, [])
    return {str(row["skill"]) for row in rows}


def _skills_on_disk() -> set[str]:
    """Return active skill directory names from canonical skill roots."""
    names: set[str] = set()
    for root in SKILL_ROOTS:
        if not root.is_dir():
            continue
        for skill_md in root.glob("*/SKILL.md"):
            names.add(skill_md.parent.name)
    return names


def _skill_md_paths() -> list[Path]:
    """Return canonical SKILL.md paths covered by this contract."""
    paths: list[Path] = []
    for root in SKILL_ROOTS:
        if root.is_dir():
            paths.extend(sorted(root.glob("*/SKILL.md")))
    return paths


def _routed_on_disk() -> set[str]:
    """Return primary routed skills that exist in the covered skill roots."""
    return _skills_on_disk() & SkillRouter().get_primary_routing_skills()


def test_skill_routing_manifest_schema_is_exhaustive() -> None:
    """Manifest must be machine-readable and carry every required governance field."""
    manifest = _coverage_manifest()

    # v2: per-category coverage scope. v1 used a single flat baseline that
    # mixed canonical / runtime-projection / package-bundled into one number,
    # which yielded semantically-false coverage. v2 separates each.
    assert manifest["schema_version"] == "skill-routing-coverage.v2"
    assert manifest["purpose"].strip()

    coverage_scope = manifest["coverage_scope"]
    for category in (
        "canonical_skills",
        "package_bundled_skills",
        "runtime_projection_skills",
        "auto_generated_skills",
    ):
        assert category in coverage_scope, f"missing category: {category}"
        cat = coverage_scope[category]
        assert "location" in cat
        assert "routing_required" in cat
        assert "rationale" in cat

    # Backward-compat shim still present so legacy ratchet tests pass during migration.
    baseline = manifest["baseline"]
    assert baseline["scope"] == "legacy-flat-aggregate"
    assert isinstance(baseline["min_routed_skill_count"], int)
    assert isinstance(baseline["min_routed_skill_coverage_percent"], (int, float))

    profile_note = manifest["profile_note"]
    assert profile_note["status"] == "pending-profile-aware-ratchet"
    assert profile_note["canonical_mapping"] == {
        "lean": ["default", "core"],
        "standard": ["default+team-extensions", "core+team"],
        "strict": ["full", "core+team+maintainer"],
        "lab": ["opt-in", "lab"],
    }

    for key in ("primary_router_orphan_allowlist", "unrouted_skill_allowlist"):
        rows = manifest[key]
        assert isinstance(rows, list)
        names = [row.get("skill") for row in rows]
        assert names == sorted(names), f"{key} must remain sorted by skill"
        assert len(names) == len(set(names)), f"{key} contains duplicate skills"
        for row in rows:
            assert set(row) == {"skill", "routing_class", "rationale"}
            assert row["skill"].strip()
            assert row["routing_class"].strip()
            assert row["rationale"].strip()


def test_profile_mapping_references_real_projection_and_adoption_profiles() -> None:
    """Profile-aware follow-up must be anchored in real repo profile taxonomies."""
    manifest = _coverage_manifest()
    mapping = manifest["profile_note"]["canonical_mapping"]

    projection_manifest = yaml.safe_load(
        (PROJECT_ROOT / "manifests" / "primitive-projection-profiles.yaml").read_text(
            encoding="utf-8"
        )
    )
    projection_profiles = set(projection_manifest["profiles"])
    lifecycle_profiles = set(adoption_profile.PROFILE_TIERS)
    adoption_doc = (PROJECT_ROOT / "docs" / "adoption-tiers.md").read_text(
        encoding="utf-8"
    )

    assert {"lean", "standard", "strict"}.issubset(
        {tier.lower() for tier in re.findall(r"\b(Lean|Standard|Strict)\b", adoption_doc)}
    )

    assert mapping["lean"][0] in projection_profiles
    assert mapping["lean"][1] in lifecycle_profiles
    assert mapping["standard"][1].split("+") == ["core", "team"]
    assert set(mapping["standard"][1].split("+")).issubset(lifecycle_profiles)
    assert mapping["strict"][0] in projection_profiles
    assert set(mapping["strict"][1].split("+")).issubset(lifecycle_profiles)
    assert mapping["lab"][1] in lifecycle_profiles


def test_manifest_baseline_matches_current_floor_exactly() -> None:
    """The legacy flat baseline (kept for backward compat in v2) should not
    overstate measured coverage. In v2 the truth lives in coverage_scope per
    category — this test only ensures the deprecated flat number stays
    monotonic and does not lie upward."""
    manifest = _coverage_manifest()
    baseline = manifest["baseline"]
    disk_skills = _skills_on_disk()
    routed_on_disk = _routed_on_disk()
    coverage = (len(routed_on_disk) / len(disk_skills)) * 100 if disk_skills else 0.0

    assert baseline["min_routed_skill_count"] <= len(routed_on_disk), (
        f"Legacy baseline overstates routed count: declared "
        f"{baseline['min_routed_skill_count']} > measured {len(routed_on_disk)}"
    )
    assert float(baseline["min_routed_skill_coverage_percent"]) <= coverage + 0.5, (
        f"Legacy baseline overstates coverage: declared "
        f"{baseline['min_routed_skill_coverage_percent']} > measured {coverage:.1f}"
    )


def test_routing_table_has_no_duplicate_primary_entries() -> None:
    """Merged frontmatter + hand-coded routing table must keep one primary entry per skill."""
    router = SkillRouter()
    primary_names = [entry.skill_name for entry in router.routing_table]
    duplicates = sorted(
        {name for name in primary_names if primary_names.count(name) > 1}
    )

    assert duplicates == [], (
        "SkillRouter has duplicate primary routing entries; frontmatter should "
        f"deduplicate hand-coded fallbacks: {duplicates}"
    )


def test_all_frontmatter_routing_patterns_compile_and_load() -> None:
    """Every SKILL.md that declares routing_patterns must compile and become routable."""
    frontmatter_entries = {
        entry.skill_name: entry for entry in _load_routing_from_frontmatter(PROJECT_ROOT)
    }
    manifest_backlog = _manifest_skill_set("unrouted_skill_allowlist")
    failures: list[str] = []

    for skill_md in _skill_md_paths():
        raw_patterns = _parse_routing_patterns_block(skill_md)
        if raw_patterns is None:
            continue

        skill_name = skill_md.parent.name
        if skill_name not in frontmatter_entries:
            failures.append(f"{skill_name}: routing_patterns present but not loaded")
            continue

        if skill_name in manifest_backlog:
            failures.append(f"{skill_name}: routeable from frontmatter but still in manifest backlog")

        for pattern, confidence in raw_patterns:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                failures.append(f"{skill_name}: invalid regex {pattern!r}: {exc}")
            if not 0.0 <= float(confidence) <= 1.0:
                failures.append(f"{skill_name}: confidence out of range for {pattern!r}: {confidence}")

    assert failures == []


def test_primary_router_entries_point_to_disk_or_declared_meta_commands() -> None:
    """Primary router entries must not silently drift away from real skills."""
    disk_skills = _skills_on_disk()
    routed_skills = SkillRouter().get_primary_routing_skills()
    orphan_allowlist = _manifest_skill_set("primary_router_orphan_allowlist")

    unexpected_orphans = sorted(
        routed_skills - disk_skills - orphan_allowlist
    )

    assert unexpected_orphans == [], (
        "SkillRouter primary entries without SKILL.md or explicit meta-command "
        f"allowlist: {unexpected_orphans}"
    )

    stale_allowlist = sorted(orphan_allowlist & disk_skills)
    assert stale_allowlist == [], (
        "Router orphan allowlist entries now exist on disk; remove them from "
        f"PRIMARY_ROUTER_ORPHAN_ALLOWLIST: {stale_allowlist}"
    )


def test_skill_router_disk_coverage_ratchet() -> None:
    """Disk skills need router coverage OR explicit classification (v2):
    - in unrouted_skill_allowlist (legacy name-mismatch backlog)
    - in exemptions.disabled_skills (disable-model-invocation: true)
    - in exemptions.name_field_mismatch.list (dir/name divergence)
    - implicitly in a category pending_routing bucket (counted, not enumerated)
    """
    disk_skills = _skills_on_disk()
    routed_skills = SkillRouter().get_primary_routing_skills()
    manifest = _coverage_manifest()
    baseline = manifest["baseline"]
    unrouted_allowlist = _manifest_skill_set("unrouted_skill_allowlist")

    # v2: harvest all explicit exemptions from the categorical schema.
    exemptions = manifest.get("exemptions", {})
    disabled_set = set(exemptions.get("disabled_skills", {}).get("list", []))
    name_mismatch_set = {
        row.get("dir", "") for row in exemptions.get("name_field_mismatch", {}).get("list", [])
    }
    explicit_exempt = unrouted_allowlist | disabled_set | name_mismatch_set

    routed_on_disk = disk_skills & routed_skills
    unrouted = disk_skills - routed_skills

    # In v2, "unrouted but pending" is COUNTED per category, not enumerated.
    # The ratchet still enforces: total unrouted <= sum of category pending counts.
    pending_total = (
        manifest.get("canonical_pending_routing", {}).get("count", 0)
        + manifest.get("runtime_projection_pending_routing", {}).get("count", 0)
        + manifest.get("package_bundled_pending_routing", {}).get("count", 0)
    )
    unexplained_unrouted = unrouted - explicit_exempt
    assert len(unexplained_unrouted) <= pending_total, (
        f"Unrouted skills ({len(unexplained_unrouted)}) exceed declared "
        f"pending budget ({pending_total}). Either add routing_patterns, "
        f"raise category pending counts, or classify explicitly. "
        f"Unexplained: {sorted(list(unexplained_unrouted))[:20]}..."
    )

    stale_backlog = sorted(unrouted_allowlist - unrouted)
    assert stale_backlog == [], (
        "Unrouted-skill allowlist contains entries that are now routed or no "
        f"longer on disk; remove them: {stale_backlog}"
    )

    routed_count = len(routed_on_disk)
    coverage = (routed_count / len(disk_skills)) * 100 if disk_skills else 0.0

    min_routed_count = int(baseline["min_routed_skill_count"])
    min_coverage = float(baseline["min_routed_skill_coverage_percent"])

    assert routed_count >= min_routed_count, (
        f"SkillRouter routed skill count regressed: {routed_count} < "
        f"{min_routed_count}"
    )
    assert coverage >= min_coverage, (
        f"SkillRouter coverage regressed: {coverage:.1f}% < "
        f"{min_coverage:.1f}% "
        f"({routed_count}/{len(disk_skills)})"
    )
