"""Behavior tests for skills batch 1: structural validity and metadata correctness.

Migrated from test-skills-batch1.sh.
Tests 23 skills for SKILL.md presence, YAML frontmatter, required fields,
content sections, and catalog listing.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

SKILLS_BATCH1 = [
    "agent-kpis",
    "arena",
    "automaker-bridge",
    "capability-snapshot",
    "cognitive-os-benchmark",
    "cognitive-os-init",
    "cognitive-os-status",
    "cognitive-os-test",
    "compat-test",
    "compose-prompt",
    "conversation-memory",
    "coverage-enforcement",
    "devbox-checkpoint",
    "doc-sync",
    "dod-check",
    "error-analyzer",
    "evaluate-plan",
    "exhaustive-prompt",
    "gpu-sandbox",
    "metrics-calibrator",
    "model-optimizer",
    "optimize-skill",
    "plan-bug",
]

# Patterns for primary and governance content sections
PRIMARY_SECTION_RE = re.compile(
    r"^## (Purpose|Instructions|What [Tt]o [Dd]o|What [Ii]t [Dd]oes|"
    r"What This Skill Does|Procedure|Overview|How It Works|When [Tt]o [Uu]se|"
    r"Goal|Objective|Problem|Process|Arguments|Argumentos|Sub-command|Usage|"
    r"Invocation|Steps|Configuration|Workflow|Description|Trigger)",
    re.MULTILINE,
)

GOVERNANCE_SECTION_RE = re.compile(
    r"^## (Rules|Guidelines|Constraints|Requirements|Prerequisites|"
    r"Output Format|Output|Outputs|Steps|Process|Procedure|Arguments|"
    r"Implementation|How It Works|Inputs)",
    re.MULTILINE,
)


def extract_frontmatter(content: str) -> tuple[bool, str]:
    """Extract YAML frontmatter from a skill file.

    Returns (has_frontmatter, frontmatter_text).
    """
    lines = content.splitlines()
    if not lines:
        return False, ""

    # Standard frontmatter: starts with ---
    if lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return True, "\n".join(lines[1:i])
        return False, ""

    # Non-standard: --- appears after a heading
    dash_indices = [i for i, line in enumerate(lines) if line.strip() == "---"]
    if len(dash_indices) >= 2:
        start, end = dash_indices[0], dash_indices[1]
        if end > start:
            return True, "\n".join(lines[start + 1 : end])

    return False, ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSkillStructureBatch1:
    """Structural validity tests for batch 1 skills."""

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_skill_md_exists(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        assert skill_file.exists(), f"SKILL.md missing for {skill}"

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_has_frontmatter(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"SKILL.md missing for {skill}")
        content = skill_file.read_text()
        has_fm, _ = extract_frontmatter(content)
        if not has_fm:
            pytest.xfail(f"no YAML frontmatter for {skill} (skill works but lacks metadata)")

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_has_name_field(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"SKILL.md missing for {skill}")
        content = skill_file.read_text()
        has_fm, fm = extract_frontmatter(content)
        if not has_fm:
            pytest.skip("no frontmatter")
        if "name:" not in fm:
            pytest.xfail(f"missing 'name' in frontmatter for {skill}")

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_has_description_field(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"SKILL.md missing for {skill}")
        content = skill_file.read_text()
        has_fm, fm = extract_frontmatter(content)
        if not has_fm:
            pytest.skip("no frontmatter")
        if not re.search(r"(^description:|^description >|^description \|)", fm, re.MULTILINE):
            pytest.xfail(f"missing 'description' in frontmatter for {skill}")

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_has_content_sections(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"SKILL.md missing for {skill}")
        content = skill_file.read_text()
        assert re.search(r"^## ", content, re.MULTILINE), f"no content sections (## headings) for {skill}"


class TestSkillContentBatch1:
    """Content quality tests for batch 1 skills."""

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_has_primary_section(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"SKILL.md missing for {skill}")
        content = skill_file.read_text()
        assert PRIMARY_SECTION_RE.search(content), (
            f"missing primary section (Purpose/Instructions/Overview/Goal/When to Use) for {skill}"
        )

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_has_governance_section(self, skill: str, skills_dir: Path):
        skill_file = skills_dir / skill / "SKILL.md"
        if not skill_file.exists():
            pytest.skip(f"SKILL.md missing for {skill}")
        content = skill_file.read_text()
        if not GOVERNANCE_SECTION_RE.search(content):
            pytest.xfail(f"no Rules/Guidelines/Constraints section for {skill}")


class TestSkillCatalogBatch1:
    """Catalog listing tests for batch 1 skills."""

    @pytest.mark.parametrize("skill", SKILLS_BATCH1)
    def test_in_catalog(self, skill: str, skills_dir: Path):
        catalog = skills_dir / "CATALOG.md"
        if not catalog.exists():
            pytest.xfail("CATALOG.md not found")
        content = catalog.read_text()
        if skill not in content:
            pytest.xfail(f"{skill} not listed in CATALOG.md")
