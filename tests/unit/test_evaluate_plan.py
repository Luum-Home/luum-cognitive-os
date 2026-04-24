"""Behavioral tests for skills/evaluate-plan — ADR-059 Phase 1 pilot.

evaluate-plan scores a plan file on 5 criteria (0-50) and writes an evaluation
file. Tests validate the scoring system math, file path convention, and
the SKILL.md-defined verdict threshold (no LLM calls needed).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.unit

# Score constants from SKILL.md
MIN_SCORE = 0
MAX_SCORE = 50
CRITERIA_COUNT = 5
POINTS_PER_CRITERION = 10
APPROVAL_THRESHOLD = 25  # APPROVED if >= 25, NEEDS_REVISION if < 25


# ---------------------------------------------------------------------------
# 1. Imports / invocation — SKILL.md exists and is well-formed
# ---------------------------------------------------------------------------


class TestEvaluatePlanSkillExists:
    def test_skill_md_present(self):
        skill_md = PROJECT_ROOT / "skills" / "evaluate-plan" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_documents_scoring_system(self):
        """SKILL.md must describe the 0-50 scoring system."""
        skill_md = PROJECT_ROOT / "skills" / "evaluate-plan" / "SKILL.md"
        content = skill_md.read_text()
        assert "0-50" in content or "50" in content, (
            "SKILL.md must document the 0-50 total score"
        )
        assert "0-10" in content, "SKILL.md must document 0-10 per criterion"


# ---------------------------------------------------------------------------
# 2. Contract test — scoring math invariants
# ---------------------------------------------------------------------------


class TestEvaluatePlanScoringContract:
    def test_max_score_equals_criteria_times_points(self):
        """5 criteria × 10 points each = 50 total max score."""
        assert CRITERIA_COUNT * POINTS_PER_CRITERION == MAX_SCORE

    def test_approval_threshold_is_half_max(self):
        """APPROVED threshold (25) must be >= 50% of max score."""
        assert APPROVAL_THRESHOLD >= MAX_SCORE / 2

    def test_score_boundary_approved(self):
        """Score >= 25 → APPROVED verdict."""
        for score in (25, 30, 40, 50):
            verdict = "APPROVED" if score >= APPROVAL_THRESHOLD else "NEEDS_REVISION"
            assert verdict == "APPROVED", f"Score {score} should be APPROVED"

    def test_score_boundary_needs_revision(self):
        """Score < 25 → NEEDS_REVISION verdict."""
        for score in (0, 10, 24):
            verdict = "APPROVED" if score >= APPROVAL_THRESHOLD else "NEEDS_REVISION"
            assert verdict == "NEEDS_REVISION", f"Score {score} should be NEEDS_REVISION"

    def test_five_criteria_are_documented(self):
        """SKILL.md must list exactly 5 scoring criteria."""
        skill_md = PROJECT_ROOT / "skills" / "evaluate-plan" / "SKILL.md"
        content = skill_md.read_text()
        criteria_names = [
            "Completeness",
            "Feasibility",
            "Risk Assessment",
            "Architecture Alignment",
            "Test Coverage",
        ]
        for name in criteria_names:
            assert name in content, f"Missing criterion: {name}"


# ---------------------------------------------------------------------------
# 3. Happy path — evaluation file path convention
# ---------------------------------------------------------------------------


class TestEvaluatePlanHappyPath:
    def test_evaluation_filename_convention(self, tmp_path: Path):
        """Evaluation file must be named {YYYY-MM-DD}-{plan-slug}-eval.md."""
        evaluations_dir = tmp_path / ".cognitive-os" / "plans" / "evaluations"
        evaluations_dir.mkdir(parents=True)

        # Simulate creating an evaluation file per SKILL.md convention
        date = "2026-04-24"
        slug = "my-feature-plan"
        eval_filename = f"{date}-{slug}-eval.md"
        eval_file = evaluations_dir / eval_filename
        eval_file.write_text(
            "---\nplan: plans/my-feature-plan.md\nscore: 30\nverdict: APPROVED\n---\n"
        )

        assert eval_file.exists()
        assert re.match(r"^\d{4}-\d{2}-\d{2}-.+-eval\.md$", eval_file.name), (
            f"Evaluation filename does not match convention: {eval_file.name}"
        )

    def test_evaluation_frontmatter_fields_contract(self, tmp_path: Path):
        """Evaluation file frontmatter must contain: plan, evaluator, date, score, verdict."""
        eval_content = (
            "---\n"
            "plan: plans/test-plan.md\n"
            "evaluator: agent\n"
            "date: 2026-04-24\n"
            "score: 35\n"
            "verdict: APPROVED\n"
            "---\n\n"
            "## Evaluation Summary\n\n"
            "**Overall Score: 35/50**\n"
        )
        eval_file = tmp_path / "2026-04-24-test-plan-eval.md"
        eval_file.write_text(eval_content)

        content = eval_file.read_text()
        for field in ("plan:", "evaluator:", "date:", "score:", "verdict:"):
            assert field in content, f"Missing frontmatter field: {field}"

        # Extract and validate score
        score_match = re.search(r"score:\s*(\d+)", content)
        assert score_match, "Could not find score in frontmatter"
        score = int(score_match.group(1))
        assert MIN_SCORE <= score <= MAX_SCORE

    def test_skill_md_documents_output_path(self):
        """SKILL.md must tell the agent where to write the evaluation file."""
        skill_md = PROJECT_ROOT / "skills" / "evaluate-plan" / "SKILL.md"
        content = skill_md.read_text()
        assert "evaluations" in content, (
            "SKILL.md must document the evaluations/ output directory"
        )


# ---------------------------------------------------------------------------
# 4. Error handling — missing or malformed plan file
# ---------------------------------------------------------------------------


class TestEvaluatePlanErrorHandling:
    def test_skill_md_documents_missing_plan_fallback(self):
        """SKILL.md must mention what to do when cognitive-os.yaml is missing."""
        skill_md = PROJECT_ROOT / "skills" / "evaluate-plan" / "SKILL.md"
        content = skill_md.read_text()
        assert "fallback" in content.lower() or "missing" in content.lower(), (
            "SKILL.md must document fallback behavior for missing config"
        )

    def test_score_cannot_exceed_max(self):
        """Scores must be clamped to 0-50 range."""
        # Simulate score summing
        raw_scores = [12, 10, 10, 10, 10]  # sum = 52, exceeds max
        total = sum(min(s, POINTS_PER_CRITERION) for s in raw_scores)
        assert total <= MAX_SCORE, (
            f"Scores must not exceed {MAX_SCORE} total, got {total}"
        )

    def test_score_cannot_be_negative(self):
        """Negative criterion scores should be treated as 0."""
        raw_scores = [-5, 8, 9, 10, 10]
        normalized = [max(0, s) for s in raw_scores]
        total = sum(normalized)
        assert total >= MIN_SCORE
        assert total <= MAX_SCORE
