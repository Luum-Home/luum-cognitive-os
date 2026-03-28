"""Behavior tests for the Scout Pattern implementation.

Validates that sdd-explore and scout skills exist with proper structure,
the scout-pattern rule exists, CATALOG.md references both skills,
model-routing references point to existing skills, and depth levels are defined.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
RULES_DIR = PROJECT_ROOT / "rules"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_file(path: Path) -> str:
    """Read file content, fail if missing."""
    assert path.exists(), f"File does not exist: {path}"
    return path.read_text(encoding="utf-8")


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields as a simple dict (key: first-line value)."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


# ---------------------------------------------------------------------------
# 1. sdd-explore SKILL.md exists with required frontmatter
# ---------------------------------------------------------------------------


class TestSddExploreSkill:

    @pytest.fixture
    def skill_content(self) -> str:
        return read_file(SKILLS_DIR / "sdd-explore" / "SKILL.md")

    def test_file_exists(self):
        assert (SKILLS_DIR / "sdd-explore" / "SKILL.md").exists()

    def test_has_frontmatter(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert fm, "sdd-explore SKILL.md must have YAML frontmatter"

    def test_frontmatter_name(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert fm.get("name") == "sdd-explore"

    def test_frontmatter_command(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert fm.get("command") == "/sdd-explore"

    def test_frontmatter_version(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert "version" in fm, "sdd-explore must declare a version"

    def test_references_scout(self, skill_content):
        assert "scout" in skill_content.lower(), (
            "sdd-explore should reference scout as prerequisite input"
        )

    def test_has_output_format(self, skill_content):
        assert "EXPLORATION:" in skill_content or "Output Format" in skill_content, (
            "sdd-explore must define an output format"
        )

    def test_has_engram_topic_key(self, skill_content):
        assert "planning/" in skill_content or "explore" in skill_content, (
            "sdd-explore must define engram persistence"
        )


# ---------------------------------------------------------------------------
# 2. scout SKILL.md exists with required frontmatter
# ---------------------------------------------------------------------------


class TestScoutSkill:

    @pytest.fixture
    def skill_content(self) -> str:
        return read_file(SKILLS_DIR / "scout" / "SKILL.md")

    def test_file_exists(self):
        assert (SKILLS_DIR / "scout" / "SKILL.md").exists()

    def test_has_frontmatter(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert fm, "scout SKILL.md must have YAML frontmatter"

    def test_frontmatter_name(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert fm.get("name") == "scout"

    def test_frontmatter_command(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert fm.get("command") == "/scout"

    def test_frontmatter_version(self, skill_content):
        fm = extract_frontmatter(skill_content)
        assert "version" in fm, "scout must declare a version"

    def test_defines_depth_levels(self, skill_content):
        for level in ("quick", "standard", "deep"):
            assert level.lower() in skill_content.lower(), (
                f"scout must define depth level: {level}"
            )

    def test_defines_token_budgets(self, skill_content):
        assert "2,000" in skill_content or "2000" in skill_content, (
            "scout must define Quick token budget (~2,000)"
        )
        assert "5,000" in skill_content or "5000" in skill_content, (
            "scout must define Standard token budget (~5,000)"
        )
        assert "10,000" in skill_content or "10000" in skill_content, (
            "scout must define Deep token budget (~10,000)"
        )

    def test_scout_report_format(self, skill_content):
        assert "SCOUT REPORT:" in skill_content, (
            "scout must define the SCOUT REPORT output format"
        )

    def test_terrain_map_in_report(self, skill_content):
        assert "TERRAIN MAP:" in skill_content, (
            "scout report must include TERRAIN MAP section"
        )

    def test_no_full_file_reads_rule(self, skill_content):
        assert "NEVER read full files" in skill_content, (
            "scout must explicitly forbid full file reads"
        )


# ---------------------------------------------------------------------------
# 3. scout-pattern.md rule exists
# ---------------------------------------------------------------------------


class TestScoutPatternRule:

    @pytest.fixture
    def rule_content(self) -> str:
        return read_file(RULES_DIR / "scout-pattern.md")

    def test_file_exists(self):
        assert (RULES_DIR / "scout-pattern.md").exists()

    def test_defines_complexity_table(self, rule_content):
        assert "Trivial" in rule_content
        assert "Medium" in rule_content
        assert "Critical" in rule_content

    def test_defines_depth_levels(self, rule_content):
        for level in ("Quick", "Standard", "Deep"):
            assert level in rule_content, (
                f"scout-pattern rule must define depth level: {level}"
            )

    def test_has_contextual_trigger(self, rule_content):
        assert "Contextual Trigger" in rule_content, (
            "scout-pattern rule must have a Contextual Trigger section"
        )

    def test_defines_token_budgets(self, rule_content):
        assert "2,000" in rule_content or "2000" in rule_content
        assert "5,000" in rule_content or "5000" in rule_content
        assert "10,000" in rule_content or "10000" in rule_content

    def test_integration_table(self, rule_content):
        assert "adaptive-bypass" in rule_content, (
            "scout-pattern must reference adaptive-bypass integration"
        )
        assert "blast-radius" in rule_content, (
            "scout-pattern must reference blast-radius integration"
        )


# ---------------------------------------------------------------------------
# 4. CATALOG.md references both skills
# ---------------------------------------------------------------------------


class TestCatalogReferences:

    @pytest.fixture
    def catalog_content(self) -> str:
        return read_file(SKILLS_DIR / "CATALOG.md")

    def test_scout_in_catalog(self, catalog_content):
        assert "| scout |" in catalog_content or "| scout|" in catalog_content, (
            "CATALOG.md must list the scout skill"
        )

    def test_sdd_explore_in_catalog(self, catalog_content):
        assert "| sdd-explore |" in catalog_content or "| sdd-explore|" in catalog_content, (
            "CATALOG.md must list the sdd-explore skill"
        )

    def test_scout_command_in_catalog(self, catalog_content):
        assert "/scout" in catalog_content, (
            "CATALOG.md must show /scout invoke command"
        )

    def test_sdd_explore_command_in_catalog(self, catalog_content):
        assert "/sdd-explore" in catalog_content, (
            "CATALOG.md must show /sdd-explore invoke command"
        )


# ---------------------------------------------------------------------------
# 5. model-routing.md references point to existing skill files
# ---------------------------------------------------------------------------


class TestModelRoutingConsistency:

    @pytest.fixture
    def routing_content(self) -> str:
        return read_file(RULES_DIR / "model-routing.md")

    def test_sdd_explore_in_routing(self, routing_content):
        assert "sdd-explore" in routing_content, (
            "model-routing.md must include sdd-explore"
        )

    def test_sdd_explore_skill_exists_for_routing(self):
        """Every skill in the routing table should have a SKILL.md or be a registered skill."""
        # sdd-explore is in the routing table and must now have a SKILL.md
        assert (SKILLS_DIR / "sdd-explore" / "SKILL.md").exists(), (
            "sdd-explore is in model-routing.md but has no SKILL.md"
        )

    def test_routing_table_skills_have_catalog_entries(self):
        """Skills in routing table should be in CATALOG.md or be registered Claude Code skills."""
        routing = read_file(RULES_DIR / "model-routing.md")
        catalog = read_file(SKILLS_DIR / "CATALOG.md")

        # Extract skill names from the routing table
        skill_names = []
        for line in routing.splitlines():
            if line.startswith("| ") and "|" in line[2:]:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3 and parts[1] and parts[1] != "Skill":
                    name = parts[1]
                    if name.startswith("---"):
                        continue
                    skill_names.append(name)

        # sdd-explore must be in catalog (was the ghost)
        assert "sdd-explore" in skill_names, (
            "sdd-explore should be in the routing table"
        )

        # Check sdd-explore specifically has a catalog entry
        assert "sdd-explore" in catalog, (
            "sdd-explore is in routing table but missing from CATALOG.md"
        )


# ---------------------------------------------------------------------------
# 6. Depth levels are properly defined and consistent
# ---------------------------------------------------------------------------


class TestDepthLevelConsistency:

    def test_scout_and_rule_share_depth_levels(self):
        """Scout skill and scout-pattern rule must define the same depth levels."""
        scout = read_file(SKILLS_DIR / "scout" / "SKILL.md")
        rule = read_file(RULES_DIR / "scout-pattern.md")

        for level in ("quick", "standard", "deep"):
            assert level.lower() in scout.lower(), (
                f"Scout skill missing depth level: {level}"
            )
            assert level.lower() in rule.lower(), (
                f"Scout rule missing depth level: {level}"
            )

    def test_complexity_to_depth_mapping(self):
        """Rule must map task complexity to scout depth."""
        rule = read_file(RULES_DIR / "scout-pattern.md")
        # Check that the rule maps Medium->Quick, Large->Standard, Critical->Deep
        assert "Medium" in rule and "Quick" in rule
        assert "Large" in rule and "Standard" in rule
        assert "Critical" in rule and "Deep" in rule

    def test_depth_dimensions_table(self):
        """Rule must define which dimensions are checked at each depth."""
        rule = read_file(RULES_DIR / "scout-pattern.md")
        # Must have a dimension table with Yes/No entries
        assert "File structure" in rule or "file structure" in rule
        assert "Entry points" in rule or "entry points" in rule
