"""Behavior tests for code-review and pr-review skills.

Validates skill file structure, content requirements, CATALOG.md presence,
and adherence to Cognitive OS skill conventions.
"""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Code Review Skill
# ---------------------------------------------------------------------------


class TestCodeReviewSkill:
    """Verify code-review skill file exists and meets requirements."""

    @pytest.fixture
    def skill_path(self) -> Path:
        return PROJECT_ROOT / "skills" / "code-review" / "SKILL.md"

    @pytest.fixture
    def skill_content(self, skill_path) -> str:
        assert skill_path.exists(), f"Skill file not found: {skill_path}"
        return skill_path.read_text(encoding="utf-8")

    @pytest.fixture
    def frontmatter(self, skill_content) -> dict:
        """Extract YAML frontmatter from skill file."""
        if skill_content.startswith("---"):
            parts = skill_content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1])
        return {}

    def test_skill_file_exists(self, skill_path):
        assert skill_path.exists(), "skills/code-review/SKILL.md must exist"

    def test_has_frontmatter(self, frontmatter):
        assert frontmatter, "Skill must have YAML frontmatter"

    def test_audience_is_project(self, frontmatter):
        assert frontmatter.get("audience") == "project", "Audience must be 'project'"

    def test_has_name(self, frontmatter):
        assert frontmatter.get("name") == "code-review"

    def test_has_version(self, frontmatter):
        assert "version" in frontmatter

    def test_references_adversarial_review(self, skill_content):
        assert "adversarial" in skill_content.lower(), (
            "Skill must reference the adversarial review protocol"
        )

    def test_references_engram(self, skill_content):
        assert "engram" in skill_content.lower(), (
            "Skill must reference engram integration"
        )

    def test_references_mem_search(self, skill_content):
        assert "mem_search" in skill_content, (
            "Skill must reference mem_search for past review context"
        )

    def test_references_mem_save(self, skill_content):
        assert "mem_save" in skill_content, (
            "Skill must reference mem_save for saving findings"
        )

    def test_has_severity_tiers(self, skill_content):
        for tier in ["BLOCKER", "CONCERN", "SUGGESTION", "QUESTION"]:
            assert tier in skill_content, f"Skill must reference severity tier: {tier}"

    def test_has_review_dimensions(self, skill_content):
        for dimension in ["correctness", "security", "performance", "maintainability"]:
            assert dimension.lower() in skill_content.lower(), (
                f"Skill must cover review dimension: {dimension}"
            )

    def test_has_topic_key_pattern(self, skill_content):
        assert "review/" in skill_content, (
            "Skill must define engram topic key pattern with review/ prefix"
        )

    def test_has_invocation(self, skill_content):
        assert "/code-review" in skill_content or "/review" in skill_content

    def test_has_procedure_steps(self, skill_content):
        assert "Step 1" in skill_content or "step 1" in skill_content.lower()

    def test_references_library(self, skill_content):
        assert "code_reviewer" in skill_content, (
            "Skill must reference lib/code_reviewer.py"
        )


# ---------------------------------------------------------------------------
# PR Review Skill
# ---------------------------------------------------------------------------


class TestPRReviewSkill:
    """Verify pr-review skill file exists and meets requirements."""

    @pytest.fixture
    def skill_path(self) -> Path:
        return PROJECT_ROOT / "skills" / "pr-review" / "SKILL.md"

    @pytest.fixture
    def skill_content(self, skill_path) -> str:
        assert skill_path.exists(), f"Skill file not found: {skill_path}"
        return skill_path.read_text(encoding="utf-8")

    @pytest.fixture
    def frontmatter(self, skill_content) -> dict:
        if skill_content.startswith("---"):
            parts = skill_content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1])
        return {}

    def test_skill_file_exists(self, skill_path):
        assert skill_path.exists(), "skills/pr-review/SKILL.md must exist"

    def test_has_frontmatter(self, frontmatter):
        assert frontmatter, "Skill must have YAML frontmatter"

    def test_audience_is_project(self, frontmatter):
        assert frontmatter.get("audience") == "project"

    def test_has_name(self, frontmatter):
        assert frontmatter.get("name") == "pr-review"

    def test_references_base_branch_detection(self, skill_content):
        assert "base" in skill_content.lower() and "branch" in skill_content.lower(), (
            "PR review must reference base branch detection"
        )

    def test_references_diff(self, skill_content):
        assert "diff" in skill_content.lower(), (
            "PR review must reference diff-based review"
        )

    def test_references_passed_failed(self, skill_content):
        assert "PASSED" in skill_content and "FAILED" in skill_content, (
            "PR review must reference PASSED/FAILED status"
        )

    def test_references_code_review_skill(self, skill_content):
        assert "code-review" in skill_content or "code_review" in skill_content, (
            "PR review must reference the code-review skill"
        )

    def test_references_engram(self, skill_content):
        assert "engram" in skill_content.lower()

    def test_references_gga(self, skill_content):
        assert "gga" in skill_content.lower() or "guardian angel" in skill_content.lower(), (
            "PR review should reference GGA inspiration"
        )

    def test_has_invocation(self, skill_content):
        assert "/pr-review" in skill_content

    def test_has_test_verification(self, skill_content):
        """PR review should include test/lint/build verification."""
        assert "test" in skill_content.lower()
        assert "lint" in skill_content.lower()

    def test_has_file_level_comments(self, skill_content):
        assert "file" in skill_content.lower() and "comment" in skill_content.lower(), (
            "PR review should produce file-level comments"
        )


# ---------------------------------------------------------------------------
# CATALOG.md integration
# ---------------------------------------------------------------------------


class TestCatalogIntegration:
    """Verify both skills are listed in CATALOG.md."""

    @pytest.fixture
    def catalog_content(self) -> str:
        catalog_path = PROJECT_ROOT / "skills" / "CATALOG.md"
        assert catalog_path.exists(), "CATALOG.md must exist"
        return catalog_path.read_text(encoding="utf-8")

    def test_code_review_in_catalog(self, catalog_content):
        assert "code-review" in catalog_content, (
            "code-review skill must be listed in CATALOG.md"
        )

    def test_pr_review_in_catalog(self, catalog_content):
        assert "pr-review" in catalog_content, (
            "pr-review skill must be listed in CATALOG.md"
        )


# ---------------------------------------------------------------------------
# Library existence
# ---------------------------------------------------------------------------


class TestLibraryExists:
    """Verify the supporting library exists."""

    def test_code_reviewer_module_exists(self):
        lib_path = PROJECT_ROOT / "lib" / "code_reviewer.py"
        assert lib_path.exists(), "lib/code_reviewer.py must exist"

    def test_code_reviewer_importable(self):
        from lib.code_reviewer import CodeReviewer, ReviewFinding, ReviewReport
        assert CodeReviewer is not None
        assert ReviewFinding is not None
        assert ReviewReport is not None
