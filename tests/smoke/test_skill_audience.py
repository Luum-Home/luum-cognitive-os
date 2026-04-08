"""Behavior tests for the skill audience separation system.

Validates that all SKILL.md files have a valid audience field and that
CATALOG.md reflects the audience classification.

Related: skills/CATALOG.md, all **/SKILL.md files
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VALID_AUDIENCES = {"project", "os-dev", "both"}

# Directories to scan for SKILL.md files
SKILL_DIRS = [
    PROJECT_ROOT / "skills",
    PROJECT_ROOT / "packages",
]


def _find_all_skill_files() -> list[Path]:
    """Find all SKILL.md files in skills/ and packages/."""
    results = []
    for base_dir in SKILL_DIRS:
        if base_dir.exists():
            results.extend(base_dir.rglob("SKILL.md"))
    return sorted(results)


def _extract_frontmatter(path: Path) -> dict[str, str]:
    """Extract YAML frontmatter from a SKILL.md file.

    Handles two frontmatter styles:
    1. Standard: file starts with --- ... ---
    2. Post-header: frontmatter appears after a markdown heading, between --- ... ---
    """
    content = path.read_text()
    # Try standard frontmatter (starts with ---)
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return _parse_yaml_simple(parts[1])
    # Try post-header frontmatter (--- appears later in the file)
    match = re.search(r"\n---\n(.*?)\n---", content, re.DOTALL)
    if match:
        return _parse_yaml_simple(match.group(1))
    return {}


def _parse_yaml_simple(text: str) -> dict[str, str]:
    """Simple YAML-like parser for frontmatter key-value pairs."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("-") and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                result[key] = value
    return result


class TestSkillAudienceField:
    """Every SKILL.md must have a valid audience field."""

    @pytest.fixture(scope="class")
    def all_skill_files(self) -> list[Path]:
        return _find_all_skill_files()

    def test_skill_files_exist(self, all_skill_files: list[Path]):
        """At least some SKILL.md files must exist."""
        assert len(all_skill_files) > 0, "No SKILL.md files found"

    def test_every_skill_has_audience(self, all_skill_files: list[Path]):
        """Every SKILL.md must have an audience field in frontmatter."""
        missing = []
        for path in all_skill_files:
            fm = _extract_frontmatter(path)
            if "audience" not in fm:
                relative = path.relative_to(PROJECT_ROOT)
                missing.append(str(relative))

        assert missing == [], (
            f"SKILL.md files missing audience field:\n"
            + "\n".join(f"  - {p}" for p in missing)
        )

    def test_audience_values_are_valid(self, all_skill_files: list[Path]):
        """Audience field must be one of: project, os-dev, both."""
        invalid = []
        for path in all_skill_files:
            fm = _extract_frontmatter(path)
            audience = fm.get("audience", "")
            if audience and audience not in VALID_AUDIENCES:
                relative = path.relative_to(PROJECT_ROOT)
                invalid.append(f"{relative}: audience={audience!r}")

        assert invalid == [], (
            f"SKILL.md files with invalid audience value:\n"
            + "\n".join(f"  - {p}" for p in invalid)
        )

    def test_os_dev_skills_exist(self, all_skill_files: list[Path]):
        """At least 3 skills must be classified as os-dev."""
        os_dev_count = 0
        for path in all_skill_files:
            fm = _extract_frontmatter(path)
            if fm.get("audience") == "os-dev":
                os_dev_count += 1

        assert os_dev_count >= 3, (
            f"Expected at least 3 os-dev skills, found {os_dev_count}"
        )

    def test_project_skills_are_majority(self, all_skill_files: list[Path]):
        """Project skills should be the majority."""
        project_count = 0
        total = len(all_skill_files)
        for path in all_skill_files:
            fm = _extract_frontmatter(path)
            if fm.get("audience") == "project":
                project_count += 1

        assert project_count > total * 0.4, (
            f"Expected project skills to be majority, "
            f"got {project_count}/{total}"
        )


class TestCatalogAudienceColumn:
    """CATALOG.md must have an Audience column."""

    @pytest.fixture(scope="class")
    def catalog_content(self) -> str:
        catalog_path = PROJECT_ROOT / "skills" / "CATALOG.md"
        assert catalog_path.exists(), "skills/CATALOG.md not found"
        return catalog_path.read_text()

    def test_catalog_has_audience_column(self, catalog_content: str):
        """The skills table must have an Audience column header."""
        assert "| Audience |" in catalog_content or "| Audience|" in catalog_content, (
            "CATALOG.md is missing the Audience column"
        )

    def test_catalog_has_os_dev_entries(self, catalog_content: str):
        """CATALOG.md must contain os-dev audience entries."""
        assert "os-dev" in catalog_content, (
            "CATALOG.md has no os-dev entries"
        )

    def test_catalog_has_project_entries(self, catalog_content: str):
        """CATALOG.md must contain project audience entries."""
        assert "| project |" in catalog_content or "| project|" in catalog_content, (
            "CATALOG.md has no project entries"
        )

    def test_catalog_has_both_entries(self, catalog_content: str):
        """CATALOG.md must contain both audience entries."""
        assert "| both |" in catalog_content or "| both|" in catalog_content, (
            "CATALOG.md has no 'both' entries"
        )

    def test_release_os_in_catalog(self, catalog_content: str):
        """release-os skill must be listed in CATALOG.md."""
        assert "release-os" in catalog_content, (
            "release-os skill not found in CATALOG.md"
        )
