"""Behavior tests for SuperClaude pattern adaptations.

Tests verify that:
- confidence-check skill exists with correct frontmatter and 5 dimensions
- self-review skill exists with correct frontmatter and 4 questions
- agent-quality.md contains Implementation Completeness section
"""

import os
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PROJECT_ROOT / "skills"
RULES_DIR = PROJECT_ROOT / "rules"


def _load_skill_frontmatter(skill_name: str) -> dict:
    """Load YAML frontmatter from a SKILL.md file."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_path.exists(), f"Skill file not found: {skill_path}"

    content = skill_path.read_text(encoding="utf-8")
    assert content.startswith("---"), f"{skill_name} SKILL.md missing YAML frontmatter"

    # Extract frontmatter between --- markers
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{skill_name} SKILL.md has malformed frontmatter"

    return yaml.safe_load(parts[1])


def _load_skill_body(skill_name: str) -> str:
    """Load the body text (after frontmatter) of a SKILL.md file."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    return parts[2] if len(parts) >= 3 else ""


# ---------------------------------------------------------------------------
# confidence-check skill tests
# ---------------------------------------------------------------------------


class TestConfidenceCheckSkill:
    """Tests for the confidence-check skill."""

    def test_skill_exists(self):
        """confidence-check/SKILL.md must exist."""
        skill_path = SKILLS_DIR / "confidence-check" / "SKILL.md"
        assert skill_path.exists(), "confidence-check/SKILL.md not found"

    def test_frontmatter_has_required_fields(self):
        """Frontmatter must include name, description, version, user-invocable."""
        fm = _load_skill_frontmatter("confidence-check")
        assert fm.get("name") == "confidence-check"
        assert "description" in fm and len(fm["description"]) > 10
        assert "version" in fm
        assert fm.get("user-invocable") is True

    def test_frontmatter_not_auto_generated(self):
        """Skill must not be marked as auto-generated."""
        fm = _load_skill_frontmatter("confidence-check")
        assert fm.get("auto-generated") is False

    def test_has_five_dimensions(self):
        """Skill body must document all 5 confidence dimensions."""
        body = _load_skill_body("confidence-check")
        dimensions = [
            "No Duplicates",
            "Architecture Compliance",
            "Documentation Verified",
            "Prior Art Reviewed",
            "Root Cause Identified",
        ]
        for dim in dimensions:
            assert dim in body, f"Missing confidence dimension: {dim}"

    def test_has_threshold_table(self):
        """Skill must define the three threshold verdicts."""
        body = _load_skill_body("confidence-check")
        assert ">= 90" in body or ">=90" in body or ">= 90" in body, (
            "Missing >= 90 threshold"
        )
        assert "70-89" in body, "Missing 70-89 threshold"
        assert "< 70" in body, "Missing < 70 threshold"

    def test_has_proceed_investigate_halt_verdicts(self):
        """Skill must define PROCEED, INVESTIGATE, and HALT verdicts."""
        body = _load_skill_body("confidence-check")
        assert "PROCEED" in body, "Missing PROCEED verdict"
        assert "INVESTIGATE" in body, "Missing INVESTIGATE verdict"
        assert "HALT" in body, "Missing HALT verdict"

    def test_weights_sum_to_100(self):
        """The 5 dimension weights must sum to 100%."""
        body = _load_skill_body("confidence-check")
        # Check the documented weights
        assert "25%" in body, "Missing 25% weight"
        assert "20%" in body, "Missing 20% weight"
        assert "15%" in body, "Missing 15% weight"

    def test_invocation_documented(self):
        """Skill must document its invocation command."""
        body = _load_skill_body("confidence-check")
        assert "/confidence-check" in body, "Missing invocation command"


# ---------------------------------------------------------------------------
# self-review skill tests
# ---------------------------------------------------------------------------


class TestSelfReviewSkill:
    """Tests for the self-review skill."""

    def test_skill_exists(self):
        """self-review/SKILL.md must exist."""
        skill_path = SKILLS_DIR / "self-review" / "SKILL.md"
        assert skill_path.exists(), "self-review/SKILL.md not found"

    def test_frontmatter_has_required_fields(self):
        """Frontmatter must include name, description, version, user-invocable."""
        fm = _load_skill_frontmatter("self-review")
        assert fm.get("name") == "self-review"
        assert "description" in fm and len(fm["description"]) > 10
        assert "version" in fm
        assert fm.get("user-invocable") is True

    def test_frontmatter_not_auto_generated(self):
        """Skill must not be marked as auto-generated."""
        fm = _load_skill_frontmatter("self-review")
        assert fm.get("auto-generated") is False

    def test_has_four_questions(self):
        """Skill body must document all 4 self-review questions."""
        body = _load_skill_body("self-review")
        questions = [
            "Did I run the tests",
            "Did I handle edge cases",
            "Does this match what was asked",
            "What might I have missed",
        ]
        for q in questions:
            assert q in body, f"Missing self-review question: {q}"

    def test_has_verdict_levels(self):
        """Skill must define PASS, FLAG, and CONCERN verdicts."""
        body = _load_skill_body("self-review")
        assert "PASS" in body, "Missing PASS verdict"
        assert "FLAG" in body, "Missing FLAG verdict"
        assert "CONCERN" in body, "Missing CONCERN verdict"

    def test_has_overall_verdict(self):
        """Skill must define overall verdict logic."""
        body = _load_skill_body("self-review")
        assert "NEEDS ATTENTION" in body, "Missing NEEDS ATTENTION overall verdict"
        assert "REVIEW REQUIRED" in body, "Missing REVIEW REQUIRED overall verdict"

    def test_invocation_documented(self):
        """Skill must document its invocation command."""
        body = _load_skill_body("self-review")
        assert "/self-review" in body, "Missing invocation command"

    def test_mandatory_self_doubt(self):
        """Question 4 must require at least 1 uncertainty."""
        body = _load_skill_body("self-review")
        assert "at least 1 uncertainty" in body.lower() or "must have at least 1" in body.lower(), (
            "Question 4 must enforce mandatory uncertainty listing"
        )


# ---------------------------------------------------------------------------
# agent-quality.md Implementation Completeness section tests
# ---------------------------------------------------------------------------


class TestImplementationCompleteness:
    """Tests for the Implementation Completeness section in agent-quality.md."""

    @pytest.fixture(autouse=True)
    def _load_rule(self):
        """Load agent-quality.md content once."""
        rule_path = RULES_DIR / "agent-quality.md"
        assert rule_path.exists(), "rules/agent-quality.md not found"
        self.content = rule_path.read_text(encoding="utf-8")

    def test_section_exists(self):
        """agent-quality.md must contain an Implementation Completeness section."""
        assert "## Implementation Completeness" in self.content

    def test_no_todo_rule(self):
        """Section must prohibit TODO comments in committed code."""
        assert "TODO" in self.content
        # Verify it mentions the prohibition, not just the word
        assert "No TODO Comments" in self.content or "No TODO comments" in self.content

    def test_no_stub_rule(self):
        """Section must prohibit stub implementations."""
        assert "No Stub Implementations" in self.content or "No stub implementations" in self.content

    def test_no_mock_in_production_rule(self):
        """Section must prohibit mock objects in production code."""
        assert "No Mock Objects in Production" in self.content or "No mock objects in production" in self.content

    def test_no_untracked_future_work_rule(self):
        """Section must prohibit deferred work without tracking."""
        assert "future work" in self.content.lower()
        assert "tracking" in self.content.lower()

    def test_no_commented_out_code_rule(self):
        """Section must prohibit commented-out code blocks."""
        assert "No Commented-Out Code" in self.content or "No commented-out code" in self.content
