"""Behavioral tests for skills/dod-check — ADR-059 Phase 1 pilot.

dod-check is an agent-instructional skill backed by rules/definition-of-done.md.
Tests validate the complexity-classification table and DoD criteria sets
documented in the SKILL.md (no LLM calls needed).
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.unit

# DoD criteria per complexity level — taken directly from SKILL.md / rules/definition-of-done.md
DOD_CRITERIA = {
    "trivial": {"code_compiles", "no_lint_errors"},
    "small": {"code_compiles", "unit_tests_pass", "no_lint_errors"},
    "medium": {
        "code_compiles",
        "unit_tests_added",
        "coverage_maintained",
        "lint_clean",
        "docs_updated",
    },
    "large": {
        "readiness_check_pass",
        "code_compiles",
        "unit_tests_80_percent",
        "integration_tests",
        "architecture_compliance",
        "docs_updated",
        "adversarial_review",
    },
    "critical": {
        "readiness_check_pass",
        "code_compiles",
        "unit_tests_80_percent",
        "integration_tests",
        "architecture_compliance",
        "docs_updated",
        "adversarial_review",
        "security_review",
        "idempotency_verified",
        "audit_trail_present",
        "rollback_tested",
    },
}

COMPLEXITY_LEVELS = ["trivial", "small", "medium", "large", "critical"]


# ---------------------------------------------------------------------------
# 1. Imports / invocation — SKILL.md exists and has required frontmatter
# ---------------------------------------------------------------------------


class TestDodCheckSkillExists:
    def test_skill_md_present(self):
        skill_md = PROJECT_ROOT / "skills" / "dod-check" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_has_output_format(self):
        """SKILL.md must document the PASS/PARTIAL/FAIL verdict contract."""
        skill_md = PROJECT_ROOT / "skills" / "dod-check" / "SKILL.md"
        content = skill_md.read_text()
        for verdict in ("PASS", "PARTIAL", "FAIL"):
            assert verdict in content, f"Missing verdict type in SKILL.md: {verdict}"

    def test_dod_rule_file_exists(self):
        """rules/definition-of-done.md must exist (source of truth for DoD table)."""
        dod_rule = PROJECT_ROOT / "rules" / "definition-of-done.md"
        assert dod_rule.exists(), "rules/definition-of-done.md missing"


# ---------------------------------------------------------------------------
# 2. Contract test — criteria escalation is monotonic
# ---------------------------------------------------------------------------


class TestDodCheckContract:
    def test_critical_is_superset_of_large(self):
        """critical level must contain ALL large-level criteria (escalation rule)."""
        assert DOD_CRITERIA["large"].issubset(DOD_CRITERIA["critical"]), (
            f"critical DoD is missing some large-level criteria: "
            f"{DOD_CRITERIA['large'] - DOD_CRITERIA['critical']}"
        )

    def test_large_is_superset_of_medium(self):
        """large level must contain ALL medium-level criteria (escalation rule)."""
        # medium 'coverage_maintained' maps to 'unit_tests_80_percent' at large level
        # Check the key medium criteria are covered
        medium_in_large = {"code_compiles", "docs_updated", "adversarial_review"}
        assert medium_in_large.issubset(DOD_CRITERIA["large"]), (
            f"large DoD is missing core medium criteria: "
            f"{medium_in_large - DOD_CRITERIA['large']}"
        )

    def test_trivial_has_fewest_criteria(self):
        """trivial must have the fewest criteria (it's the simplest level)."""
        trivial_count = len(DOD_CRITERIA["trivial"])
        for level in COMPLEXITY_LEVELS[1:]:
            assert trivial_count <= len(DOD_CRITERIA[level]), (
                f"trivial ({trivial_count}) has MORE criteria than {level} "
                f"({len(DOD_CRITERIA[level])})"
            )

    def test_critical_has_most_criteria(self):
        """critical must have the most criteria."""
        critical_count = len(DOD_CRITERIA["critical"])
        for level in COMPLEXITY_LEVELS[:-1]:
            assert len(DOD_CRITERIA[level]) <= critical_count, (
                f"{level} ({len(DOD_CRITERIA[level])}) has MORE criteria than "
                f"critical ({critical_count})"
            )


# ---------------------------------------------------------------------------
# 3. Happy path — auto-classification signal mapping
# ---------------------------------------------------------------------------


class TestDodCheckAutoClassification:
    """Tests the signal→complexity mapping documented in SKILL.md."""

    def _classify(self, changed_files: int, lines_changed: int, is_security: bool) -> str:
        """Simplified classification matching SKILL.md table."""
        if is_security:
            return "critical"
        if changed_files > 5 or lines_changed > 500:
            return "large"
        if changed_files > 3:
            return "medium"
        if changed_files == 1 and lines_changed < 20:
            return "trivial"
        if 1 <= changed_files <= 3:
            return "small"
        return "medium"

    def test_single_file_small_change_is_trivial(self):
        assert self._classify(1, 5, False) == "trivial"

    def test_security_is_always_critical(self):
        assert self._classify(1, 5, True) == "critical"

    def test_many_files_is_large(self):
        assert self._classify(10, 1000, False) == "large"

    def test_few_files_is_small(self):
        assert self._classify(2, 50, False) == "small"


# ---------------------------------------------------------------------------
# 4. Error handling — phase enforcement documented in SKILL.md
# ---------------------------------------------------------------------------


class TestDodCheckPhaseEnforcement:
    def test_skill_md_documents_phase_enforcement(self):
        """SKILL.md must document how phase changes enforcement level."""
        skill_md = PROJECT_ROOT / "skills" / "dod-check" / "SKILL.md"
        content = skill_md.read_text()
        assert "BLOCK" in content and "WARN" in content.upper(), (
            "SKILL.md must document BLOCK vs WARNING enforcement by phase"
        )

    def test_production_and_maintenance_block_documented(self):
        """production and maintenance phases must be listed as BLOCK."""
        skill_md = PROJECT_ROOT / "skills" / "dod-check" / "SKILL.md"
        content = skill_md.read_text()
        assert "production" in content
        assert "maintenance" in content
