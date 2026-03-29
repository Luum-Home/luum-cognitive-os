"""Behavior tests for the Skill Routing Table in rules/skill-management.md.

Validates that:
- The routing table section exists in the rule file
- All skills referenced in the routing table are registered in CATALOG.md
- All skills referenced have corresponding skill directories
- The routing table has sufficient coverage (at least 10 entries)
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def skill_management_content() -> str:
    """Read the full content of rules/skill-management.md."""
    path = PROJECT_ROOT / "rules" / "skill-management.md"
    if not path.exists():
        pytest.skip("rules/skill-management.md not found")
    return path.read_text()


@pytest.fixture
def catalog_content() -> str:
    """Read the full content of skills/CATALOG.md."""
    path = PROJECT_ROOT / "skills" / "CATALOG.md"
    if not path.exists():
        pytest.skip("skills/CATALOG.md not found")
    return path.read_text()


@pytest.fixture
def skill_directories() -> set:
    """Return the set of skill directory names under skills/."""
    skills_dir = PROJECT_ROOT / "skills"
    if not skills_dir.exists():
        pytest.skip("skills/ directory not found")
    return {
        d.name for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    }


def _extract_routing_table_skills(content: str) -> list:
    """Extract all `/skill-name` references from the Skill Routing Table section."""
    # Find the section
    section_match = re.search(
        r"## Skill Routing Table\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not section_match:
        return []

    section = section_match.group(1)
    # Extract all `/skill-name` patterns from the table rows
    skills = re.findall(r"`/([a-z][a-z0-9-]*)`", section)
    return skills


def _extract_catalog_invocations(content: str) -> set:
    """Extract all invocation commands from CATALOG.md."""
    # Matches both `/skill-name` and `_auto_` patterns in the Invoke column
    return set(re.findall(r"`/([a-z][a-z0-9-]*)`", content))


class TestSkillRoutingTablePresence:
    """Verify the routing table section exists and has content."""

    def test_routing_table_section_exists(self, skill_management_content):
        """rules/skill-management.md must contain a 'Skill Routing Table' section."""
        assert "## Skill Routing Table" in skill_management_content

    def test_routing_table_has_markdown_table(self, skill_management_content):
        """The routing table section must contain a markdown table."""
        section_match = re.search(
            r"## Skill Routing Table\s*\n(.*?)(?=\n## |\Z)",
            skill_management_content,
            re.DOTALL,
        )
        assert section_match is not None
        section = section_match.group(1)
        # A markdown table has pipes and a separator row
        assert "|" in section
        assert "---" in section

    def test_routing_table_has_at_least_10_entries(self, skill_management_content):
        """The routing table must have at least 10 task-type entries."""
        skills = _extract_routing_table_skills(skill_management_content)
        # Each table row has at least one skill reference; count unique rows
        # by counting unique skills (some rows have 2 skills)
        assert len(skills) >= 10, (
            f"Routing table has {len(skills)} skill references, expected >= 10"
        )


class TestSkillRoutingTableCatalogAlignment:
    """Verify that routing table skills exist in the catalog."""

    def test_all_routing_skills_in_catalog(
        self, skill_management_content, catalog_content
    ):
        """Every skill in the routing table should be listed in CATALOG.md."""
        routing_skills = _extract_routing_table_skills(skill_management_content)
        catalog_skills = _extract_catalog_invocations(catalog_content)

        # Meta-commands handled by the orchestrator or SDD phases,
        # not individually listed in the catalog
        meta_commands = {"sdd-new", "sdd-verify", "skill-creator"}

        # Some skills in routing table use shortened names; also check
        # _auto_ triggered skills by name in catalog text
        missing = []
        for skill in routing_skills:
            if skill in meta_commands:
                continue
            if skill not in catalog_skills:
                # Check if the skill name appears anywhere in the catalog
                if skill not in catalog_content:
                    missing.append(skill)

        assert not missing, (
            f"Skills in routing table but NOT in CATALOG.md: {missing}"
        )


class TestSkillRoutingTableDirectories:
    """Verify that routing table skills have corresponding directories."""

    # Invoke name -> directory name mapping for skills whose invoke command
    # differs from their directory name in skills/.
    INVOKE_TO_DIR = {
        "coverage-report": "coverage-enforcement",
        "cost-predict": "cost-predictor",
        "issue-to-pr": "issue-pipeline",
        "squad-report": "squad-manager",
        "batch-run": "batch-runner",
        "jupyter-exec": "jupyter-execute",
        "create-persistent-agent": "persistent-agent",
        "simulate": "simulation-arena",
        "estimation-report": "estimation-report",
        "sessions": "session-manager",
        "checkpoint": "devbox-checkpoint",
        "private": "private-mode",
    }

    def test_routing_skills_have_directories(
        self, skill_management_content, skill_directories
    ):
        """Every skill in the routing table should have a skills/ directory."""
        routing_skills = _extract_routing_table_skills(skill_management_content)

        # Meta-commands handled by the orchestrator or SDD phases
        # that live under .claude/skills/ as phase skills, not standalone dirs.
        meta_commands = {"sdd-new", "sdd-verify", "skill-creator"}

        # Skills listed in CATALOG.md but implemented as lib modules
        # rather than standalone SKILL.md directories.
        lib_only_skills = {"cost-predict", "estimation-report"}

        excluded = meta_commands | lib_only_skills

        missing = []
        for skill in routing_skills:
            if skill in excluded:
                continue
            # Resolve invoke name to directory name
            dir_name = self.INVOKE_TO_DIR.get(skill, skill)
            if dir_name not in skill_directories:
                # Try without prefix for auto-triggered skills
                hyphenated = dir_name.replace("_", "-")
                if hyphenated not in skill_directories:
                    missing.append(f"{skill} (checked: {dir_name})")

        assert not missing, (
            f"Skills in routing table without a skills/ directory: {missing}"
        )
