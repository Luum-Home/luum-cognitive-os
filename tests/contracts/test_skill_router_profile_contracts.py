"""Profile-aware SkillRouter and lazy catalog contracts.

These tests protect ADR-174's future behavior: every new skill must either be
routeable from SKILL.md frontmatter or explicitly classified, projected profile
surfaces must be 100% routeable, service runtimes must not serve stale routing
indexes, and compact catalogs must stay frontmatter-only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lib.skill_router import (
    SkillRouter,
    SkillRoutingIndexCache,
    _detect_skill_md_paths,
    _load_profile_projected_skills,
    _parse_frontmatter,
    _parse_routing_patterns_block,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = PROJECT_ROOT / "manifests" / "skill-routing-coverage.yaml"
COMPACT_CATALOG = PROJECT_ROOT / "skills" / "CATALOG-COMPACT.md"


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _unrouted_allowlist() -> set[str]:
    return {str(row["skill"]) for row in _manifest().get("unrouted_skill_allowlist", [])}


def _profile_names() -> list[str]:
    return sorted(_manifest().get("profile_routing", {}).get("profiles", {}))


def _write_skill(project: Path, name: str, *, pattern: str, body: str = "") -> None:
    skill_dir = project / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_dir.joinpath("SKILL.md").write_text(
        f"""---
name: {name}
description: Test skill {name}.
audience: both
routing_patterns:
  - pattern: "{pattern}"
    confidence: 0.91
---

# {name}

{body}
""",
        encoding="utf-8",
    )


def _write_catalog(project: Path, names: list[str]) -> None:
    catalog = project / "skills" / "CATALOG.md"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    rows = ["| Skill | Description |", "|---|---|"]
    rows.extend(f"| {name} | Test skill |" for name in names)
    catalog.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_manifest(project: Path, *, profile: str, projected_skills: list[str]) -> None:
    manifest = project / "manifests" / "skill-routing-coverage.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "skill-routing-coverage.v1",
                "profile_routing": {
                    "profiles": {
                        profile: {
                            "projected_skills": projected_skills,
                            "min_routeable_percent": 100,
                        }
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_new_skills_require_routing_metadata() -> None:
    """A skill cannot silently join the backlog unless manifest-classified.

    Existing debt is explicit in ``unrouted_skill_allowlist``. Any future
    SKILL.md outside that list must be routeable, declare ``routing_patterns``,
    or carry an explicit ``routing.class`` rationale.
    """
    allowlisted = _unrouted_allowlist()
    routeable = SkillRouter(project_root=PROJECT_ROOT).get_primary_routing_skills()
    offenders: list[str] = []

    for skill_name, skill_md in sorted(_detect_skill_md_paths(PROJECT_ROOT).items()):
        if skill_name in allowlisted:
            continue
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        frontmatter = _parse_frontmatter(text)
        has_patterns = _parse_routing_patterns_block(skill_md) is not None
        routing = frontmatter.get("routing")
        has_classification = isinstance(routing, dict) and bool(routing.get("class"))
        is_routeable = skill_name in routeable
        if not has_patterns and not has_classification and not is_routeable:
            offenders.append(f"{skill_name} ({skill_md.relative_to(PROJECT_ROOT)})")

    assert offenders == []


@pytest.mark.parametrize("profile", _profile_names())
def test_projected_skills_are_routeable_by_profile(profile: str) -> None:
    """Every skill projected into a profile must be routeable in that profile."""
    projected = _load_profile_projected_skills(PROJECT_ROOT, profile)
    assert projected, f"profile {profile} must declare projected_skills"
    router = SkillRouter(project_root=PROJECT_ROOT, profile=profile)
    missing = sorted(projected - router.get_primary_routing_skills())
    assert missing == []


@pytest.mark.parametrize("profile", _profile_names())
def test_router_index_excludes_unprojected_skills(profile: str) -> None:
    """Profile-specific router indexes must not leak non-projected skills."""
    projected = _load_profile_projected_skills(PROJECT_ROOT, profile)
    assert projected is not None
    router = SkillRouter(project_root=PROJECT_ROOT, profile=profile)
    leaked = sorted(router.get_primary_routing_skills() - projected)
    assert leaked == []


def test_service_router_cache_invalidates_on_skill_md_checksum(tmp_path: Path) -> None:
    """A long-running service router cache must refresh after SKILL.md edits."""
    _write_skill(tmp_path, "alpha", pattern="alpha intent")
    _write_catalog(tmp_path, ["alpha"])
    _write_manifest(tmp_path, profile="lean", projected_skills=["alpha"])

    cache = SkillRoutingIndexCache()
    first = cache.get_router(project_root=tmp_path, profile="lean")
    assert first.best_match("alpha intent") is not None

    _write_skill(tmp_path, "alpha", pattern="beta intent")
    second = cache.get_router(project_root=tmp_path, profile="lean")

    assert second is not first
    assert second.best_match("alpha intent") is None
    assert second.best_match("beta intent") is not None


def test_lazy_catalog_does_not_load_full_skill_bodies() -> None:
    """The compact catalog must stay frontmatter-only, not a SKILL.md body dump."""
    compact = COMPACT_CATALOG.read_text(encoding="utf-8", errors="replace")
    full_body_sentinels = [
        "This is an **agentic primitive**",
        "## Workflow",
        "## Output expectations",
    ]
    leaked = [sentinel for sentinel in full_body_sentinels if sentinel in compact]

    assert "| adr-tombstone |" in compact
    assert leaked == []
    assert len(compact) < (PROJECT_ROOT / "skills" / "CATALOG.md").stat().st_size


def test_manifest_declares_profile_coverage_floors() -> None:
    """Manifest must expose operator-facing profile coverage floors."""
    manifest = _manifest()
    expected = {
        "lean": 100,
        "standard": 100,
        "strict": 100,
        "lab": 90,
    }
    profiles = manifest.get("profiles", {})

    assert set(profiles) == set(expected)
    for profile, floor in expected.items():
        assert profiles[profile]["min_coverage_percent"] == floor
        assert profile in manifest.get("profile_routing", {}).get("profiles", {})


def test_unrouted_backlog_cannot_grow_silently() -> None:
    """The explicit migration backlog may shrink, but cannot grow without baseline update."""
    manifest = _manifest()
    max_backlog = int(manifest["baseline"]["max_unrouted_skill_count"])
    current_backlog = len(manifest.get("unrouted_skill_allowlist", []))

    assert current_backlog <= max_backlog
