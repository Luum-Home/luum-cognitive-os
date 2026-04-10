"""Behavior tests for the release-os skill.

Validates that the release-os skill exists, has the correct structure,
and is properly classified as os-dev audience.

Related: skills/release-os/SKILL.md
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_PATH = PROJECT_ROOT / "skills" / "release-os" / "SKILL.md"


class TestReleaseOsSkillExists:
    """The release-os skill must exist and be properly structured."""

    def test_skill_file_exists(self):
        """skills/release-os/SKILL.md must exist."""
        assert SKILL_PATH.exists(), (
            f"release-os skill not found at {SKILL_PATH}"
        )

    def test_skill_is_not_empty(self):
        """The skill file must have content."""
        content = SKILL_PATH.read_text()
        assert len(content) > 100, (
            "release-os SKILL.md is too short to be a real skill"
        )


class TestReleaseOsFrontmatter:
    """The release-os skill must have correct frontmatter."""

    @pytest.fixture(scope="class")
    def content(self) -> str:
        return SKILL_PATH.read_text()

    @pytest.fixture(scope="class")
    def frontmatter(self, content: str) -> str:
        """Extract frontmatter text."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[1]
        return ""

    def test_has_frontmatter(self, frontmatter: str):
        """Must have YAML frontmatter."""
        assert frontmatter, "release-os SKILL.md missing YAML frontmatter"

    def test_audience_is_os_dev(self, frontmatter: str):
        """Must be classified as os-dev audience (or os shorthand)."""
        assert "audience: os-dev" in frontmatter or "audience: os" in frontmatter, (
            "release-os must have audience: os-dev or audience: os"
        )

    def test_has_name(self, frontmatter: str):
        """Must have a name field."""
        assert "name: release-os" in frontmatter, (
            "release-os must have name: release-os in frontmatter"
        )

    def test_has_command(self, frontmatter: str):
        """Must have a command field."""
        assert "command:" in frontmatter or "invoke:" in frontmatter, (
            "release-os must have a command or invoke field"
        )


class TestReleaseOsContent:
    """The release-os skill must have required sections."""

    @pytest.fixture(scope="class")
    def content(self) -> str:
        return SKILL_PATH.read_text()

    def test_references_version_file(self, content: str):
        """Must reference the VERSION file."""
        assert "VERSION" in content, (
            "release-os must reference the VERSION file"
        )

    def test_references_changelog(self, content: str):
        """Must reference CHANGELOG.md."""
        assert "CHANGELOG" in content, (
            "release-os must reference CHANGELOG.md"
        )

    def test_references_git_tag(self, content: str):
        """Must reference git tag creation."""
        assert "git tag" in content, (
            "release-os must include git tag creation"
        )

    def test_has_validation_section(self, content: str):
        """Must have a pre-validation or prerequisites section."""
        content_lower = content.lower()
        assert any(term in content_lower for term in [
            "validation", "prerequisite", "pre-release", "safety",
        ]), "release-os must have a validation/prerequisites section"

    def test_has_process_steps(self, content: str):
        """Must have numbered process steps."""
        step_pattern = re.compile(r"###\s+Step\s+\d+")
        steps = step_pattern.findall(content)
        assert len(steps) >= 3, (
            f"release-os must have at least 3 process steps, found {len(steps)}"
        )

    def test_never_auto_pushes(self, content: str):
        """Must explicitly state it never auto-pushes."""
        content_lower = content.lower()
        assert "never" in content_lower and "push" in content_lower, (
            "release-os must explicitly state it never auto-pushes"
        )
