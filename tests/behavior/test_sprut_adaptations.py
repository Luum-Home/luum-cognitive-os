"""Behavior tests for Sprut Agent Kit adaptations.

Validates that the audit-website and persistent-agent skills exist with
correct frontmatter, expected content sections, and scoring systems.
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill(skill_name: str) -> str:
    """Read a SKILL.md file and return its full text."""
    path = PROJECT_ROOT / "skills" / skill_name / "SKILL.md"
    assert path.exists(), f"Skill file not found: {path}"
    return path.read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    if not text.startswith("---"):
        pytest.fail("SKILL.md does not start with YAML frontmatter delimiter")
    parts = text.split("---", 2)
    assert len(parts) >= 3, "SKILL.md frontmatter is not properly delimited"
    return yaml.safe_load(parts[1])


# ---------------------------------------------------------------------------
# audit-website tests
# ---------------------------------------------------------------------------


class TestAuditWebsiteSkill:
    """Tests for the audit-website skill."""

    @pytest.fixture(autouse=True)
    def _load_skill(self) -> None:
        self.text = _read_skill("audit-website")
        self.fm = _parse_frontmatter(self.text)

    def test_frontmatter_name(self) -> None:
        assert self.fm["name"] == "audit-website"

    def test_frontmatter_author(self) -> None:
        assert self.fm["metadata"]["author"] == "luum"

    def test_frontmatter_user_invocable(self) -> None:
        assert self.fm["user-invocable"] is True

    def test_frontmatter_version(self) -> None:
        assert "version" in self.fm
        assert self.fm["version"] == "1.0.0"

    def test_has_seo_category(self) -> None:
        assert "SEO" in self.text or "seo" in self.text.lower()
        # Check for specific SEO checkpoints
        assert "title tag" in self.text.lower()
        assert "meta description" in self.text.lower()
        assert "canonical" in self.text.lower()
        assert "sitemap" in self.text.lower()
        assert "robots.txt" in self.text.lower()

    def test_has_performance_category(self) -> None:
        assert "Performance" in self.text
        assert "TTFB" in self.text
        assert "LCP" in self.text
        assert "CLS" in self.text

    def test_has_security_category(self) -> None:
        assert "Security" in self.text
        assert "HTTPS" in self.text
        assert "security headers" in self.text.lower()

    def test_has_content_ux_category(self) -> None:
        assert "Content/UX" in self.text
        assert "mobile responsive" in self.text.lower()
        assert "font size" in self.text.lower()

    def test_has_accessibility_category(self) -> None:
        assert "Accessibility" in self.text
        assert "ARIA" in self.text
        assert "keyboard" in self.text.lower()

    def test_has_schema_org_category(self) -> None:
        assert "Schema.org" in self.text
        assert "BreadcrumbList" in self.text
        assert "Organization" in self.text

    def test_all_six_categories_present(self) -> None:
        categories = [
            "SEO",
            "Performance",
            "Security",
            "Content/UX",
            "Accessibility",
            "Schema.org",
        ]
        for cat in categories:
            assert cat in self.text, f"Category '{cat}' not found in skill"

    def test_scoring_system_present(self) -> None:
        text_lower = self.text.lower()
        assert "pass" in text_lower
        assert "fail" in text_lower
        assert "n/a" in text_lower or "n-a" in text_lower
        # Grade thresholds
        assert "excellent" in text_lower
        assert "good" in text_lower
        assert "needs work" in text_lower
        assert "critical" in text_lower

    def test_scoring_formula(self) -> None:
        # Verify the scoring formula is documented
        assert "category_score" in self.text or "passed" in self.text.lower()
        assert "100" in self.text  # percentage


# ---------------------------------------------------------------------------
# persistent-agent tests
# ---------------------------------------------------------------------------


class TestPersistentAgentSkill:
    """Tests for the persistent-agent skill."""

    @pytest.fixture(autouse=True)
    def _load_skill(self) -> None:
        self.text = _read_skill("persistent-agent")
        self.fm = _parse_frontmatter(self.text)

    def test_frontmatter_name(self) -> None:
        assert self.fm["name"] == "persistent-agent"

    def test_frontmatter_author(self) -> None:
        assert self.fm["metadata"]["author"] == "luum"

    def test_frontmatter_user_invocable(self) -> None:
        assert self.fm["user-invocable"] is True

    def test_frontmatter_version(self) -> None:
        assert "version" in self.fm
        assert self.fm["version"] == "1.0.0"

    def test_describes_data_directory_structure(self) -> None:
        # Must describe the data/ directory with profile.md and events/log.md
        assert "data/" in self.text
        assert "profile.md" in self.text
        assert "events/" in self.text
        assert "log.md" in self.text

    def test_describes_skill_md_in_structure(self) -> None:
        assert "SKILL.md" in self.text

    def test_auto_fixation_checklist_present(self) -> None:
        text_lower = self.text.lower()
        assert "auto-fixation" in text_lower or "auto fixation" in text_lower

    def test_auto_fixation_four_questions(self) -> None:
        text_lower = self.text.lower()
        assert "new knowledge" in text_lower
        assert "correct" in text_lower  # "Did the user correct me?"
        assert "pattern" in text_lower  # "Did I discover a pattern?"
        assert "error" in text_lower  # "Did I make an error?"

    def test_invocation_format(self) -> None:
        assert "/create-persistent-agent" in self.text

    def test_domain_flag(self) -> None:
        assert "--domain" in self.text
