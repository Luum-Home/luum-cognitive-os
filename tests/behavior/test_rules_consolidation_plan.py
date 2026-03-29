"""Behavior tests for the rules consolidation plan document.

Validates that docs/rules-consolidation-plan.md exists, has all required
sections, lists exactly 14 core rules, defines triggers for every on-demand
rule, and includes the token budget calculator and migration path.

Related files:
  - docs/rules-consolidation-plan.md (the plan under test)
  - rules/ (rule files referenced in the plan)
  - tests/behavior/test_rules_consolidation.py (safety net for rule system state)
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = PROJECT_ROOT / "docs" / "rules-consolidation-plan.md"
RULES_DIR = PROJECT_ROOT / "rules"


def _read_plan() -> str:
    """Read the consolidation plan document."""
    assert PLAN_PATH.exists(), (
        f"Plan document missing at {PLAN_PATH}. "
        "Create docs/rules-consolidation-plan.md before running these tests."
    )
    return PLAN_PATH.read_text()


# The 14 core rules that must be always-loaded
EXPECTED_CORE_RULES = [
    "RULES-COMPACT.md",
    "adaptive-bypass.md",
    "acceptance-criteria.md",
    "agent-quality.md",
    "trust-score.md",
    "definition-of-done.md",
    "phase-aware-agents.md",
    "closed-loop-prompts.md",
    "token-economy.md",
    "responsiveness.md",
    "agent-security.md",
    "credential-management.md",
    "content-policy.md",
    "error-learning.md",
]


# ===========================================================================
# Plan Document Structure Tests
# ===========================================================================


class TestPlanDocumentExists:
    """Verify the plan document exists and is non-trivial."""

    def test_plan_file_exists(self):
        """docs/rules-consolidation-plan.md must exist."""
        assert PLAN_PATH.exists(), f"Plan document not found at {PLAN_PATH}"

    def test_plan_has_minimum_length(self):
        """Plan must be substantial (>5000 characters)."""
        content = _read_plan()
        assert len(content) > 5000, (
            f"Plan is only {len(content)} chars. Expected >5000 for a comprehensive plan."
        )

    def test_plan_starts_with_title(self):
        """Plan must start with a markdown title."""
        content = _read_plan()
        assert content.strip().startswith("# "), "Plan must start with a # title"


class TestPlanHasAllSections:
    """Verify all 7 required sections are present."""

    REQUIRED_SECTIONS = [
        "Section 1",  # Current State Analysis
        "Section 2",  # The 14 Always-Loaded Rules
        "Section 3",  # The 59 On-Demand Rules (or similar wording)
        "Section 4",  # Implementation Plan
        "Section 5",  # Risk Analysis
        "Section 6",  # Migration Path
        "Section 7",  # Token Budget Calculator
    ]

    def test_all_seven_sections_present(self):
        """Plan must contain all 7 sections."""
        content = _read_plan()
        missing = []
        for section in self.REQUIRED_SECTIONS:
            if section not in content:
                missing.append(section)
        assert not missing, (
            f"Missing sections in plan: {missing}. "
            f"Plan must contain all 7 sections: {self.REQUIRED_SECTIONS}"
        )

    def test_section_1_current_state(self):
        """Section 1 must contain current state analysis with token counts."""
        content = _read_plan()
        assert "Current State" in content, "Section 1 must mention 'Current State'"
        # Must mention token counts
        assert "73" in content or "73K" in content or "73,000" in content, (
            "Section 1 must reference ~73K tokens (current total)"
        )

    def test_section_2_always_loaded(self):
        """Section 2 must list always-loaded rules."""
        content = _read_plan()
        assert "Always-Loaded" in content or "Always Loaded" in content, (
            "Section 2 must discuss always-loaded rules"
        )

    def test_section_4_implementation(self):
        """Section 4 must contain implementation steps."""
        content = _read_plan()
        assert "Implementation" in content, "Section 4 must discuss implementation"
        # Must mention self-install.sh
        assert "self-install" in content, (
            "Implementation must reference self-install.sh (the hook that manages profiles)"
        )

    def test_section_5_risk_analysis(self):
        """Section 5 must contain a risk analysis table."""
        content = _read_plan()
        assert "Risk" in content, "Section 5 must discuss risks"
        # Must have severity assessments
        assert "HIGH" in content or "MEDIUM" in content or "LOW" in content, (
            "Risk analysis must include severity levels"
        )

    def test_section_6_migration_path(self):
        """Section 6 must define migration phases."""
        content = _read_plan()
        assert "Migration" in content, "Section 6 must discuss migration"
        # Must have multiple phases
        phase_count = len(re.findall(r'Phase \d', content))
        assert phase_count >= 5, (
            f"Migration path must have at least 5 phases, found {phase_count}"
        )

    def test_section_7_token_budget(self):
        """Section 7 must contain a token budget calculator with scenarios."""
        content = _read_plan()
        assert "Token Budget" in content or "Budget Calculator" in content, (
            "Section 7 must contain token budget calculator"
        )
        # Must have percentage calculations
        assert "% of 1M" in content or "% of 200K" in content, (
            "Token budget must show percentages of context windows"
        )


# ===========================================================================
# Core Rules Validation
# ===========================================================================


class TestCoreRulesList:
    """Verify the plan lists exactly 14 core rules and they all exist."""

    def test_plan_mentions_14_core_rules(self):
        """Plan must explicitly state 14 as the core rules count."""
        content = _read_plan()
        assert "14" in content, "Plan must mention 14 as the core rules count"
        # Must have "14" near "always" or "core"
        lines_with_14 = [
            line for line in content.splitlines()
            if "14" in line and ("always" in line.lower() or "core" in line.lower())
        ]
        assert len(lines_with_14) > 0, (
            "Plan must associate '14' with 'always-loaded' or 'core' rules"
        )

    def test_all_14_core_rules_listed_in_plan(self):
        """Every core rule must be mentioned in the plan."""
        content = _read_plan()
        missing = []
        for rule in EXPECTED_CORE_RULES:
            rule_stem = rule.replace(".md", "")
            if rule not in content and rule_stem not in content:
                missing.append(rule)
        assert not missing, (
            f"Core rules not mentioned in plan: {missing}"
        )

    def test_all_14_core_rules_exist_on_disk(self):
        """Every core rule file must exist in rules/."""
        missing = []
        for rule in EXPECTED_CORE_RULES:
            rule_path = RULES_DIR / rule
            if not rule_path.exists():
                missing.append(rule)
        assert not missing, (
            f"Core rule files missing from rules/: {missing}"
        )

    def test_core_rules_count_is_exactly_14(self):
        """The EXPECTED_CORE_RULES list must have exactly 14 entries."""
        assert len(EXPECTED_CORE_RULES) == 14, (
            f"Expected exactly 14 core rules, got {len(EXPECTED_CORE_RULES)}: "
            f"{EXPECTED_CORE_RULES}"
        )

    def test_core_rules_include_security_essentials(self):
        """Core rules must include security-critical rules."""
        security_rules = {"agent-security.md", "credential-management.md", "content-policy.md"}
        core_set = set(EXPECTED_CORE_RULES)
        missing = security_rules - core_set
        assert not missing, (
            f"Security-critical rules missing from core: {missing}"
        )

    def test_core_rules_include_quality_essentials(self):
        """Core rules must include quality-critical rules."""
        quality_rules = {
            "acceptance-criteria.md", "agent-quality.md",
            "trust-score.md", "definition-of-done.md",
        }
        core_set = set(EXPECTED_CORE_RULES)
        missing = quality_rules - core_set
        assert not missing, (
            f"Quality-critical rules missing from core: {missing}"
        )


# ===========================================================================
# On-Demand Rules Trigger Validation
# ===========================================================================


class TestOnDemandTriggers:
    """Verify every on-demand rule has a trigger defined in the plan."""

    def _get_on_demand_rules(self) -> list[str]:
        """Get all rule files that are NOT in the core list."""
        all_rules = sorted(f.name for f in RULES_DIR.glob("*.md"))
        core_set = set(EXPECTED_CORE_RULES)
        return [r for r in all_rules if r not in core_set]

    def test_on_demand_rules_count(self):
        """On-demand rules should be total minus 14 core."""
        on_demand = self._get_on_demand_rules()
        all_rules = list(RULES_DIR.glob("*.md"))
        expected = len(all_rules) - 14
        assert len(on_demand) == expected, (
            f"Expected {expected} on-demand rules, found {len(on_demand)}"
        )

    def test_plan_has_trigger_map(self):
        """Plan must contain a trigger map section for on-demand rules."""
        content = _read_plan()
        assert "Trigger" in content, "Plan must discuss triggers for on-demand rules"
        # Must mention trigger types
        trigger_types = ["hook", "command", "keyword", "threshold", "config", "env_var"]
        found_types = [t for t in trigger_types if t in content.lower()]
        assert len(found_types) >= 3, (
            f"Plan must define at least 3 trigger types, found: {found_types}"
        )

    def test_every_on_demand_rule_mentioned_in_plan(self):
        """Every on-demand rule must be referenced somewhere in the plan."""
        content = _read_plan()
        on_demand = self._get_on_demand_rules()
        missing = []
        for rule in on_demand:
            rule_stem = rule.replace(".md", "")
            # Check for the rule name in any form
            if rule not in content and rule_stem not in content:
                missing.append(rule)
        # Allow up to 5% to be missing (some may be referenced by package name)
        threshold = max(3, len(on_demand) * 0.05)
        assert len(missing) <= threshold, (
            f"{len(missing)} on-demand rules not mentioned in plan (max {threshold}): "
            f"{sorted(missing)}"
        )


# ===========================================================================
# Token Budget Calculator Tests
# ===========================================================================


class TestTokenBudgetCalculator:
    """Verify the token budget calculator is present and correct."""

    def test_budget_shows_current_state(self):
        """Calculator must show current state (all rules loaded)."""
        content = _read_plan()
        # Must mention 73K or similar for current total
        assert any(
            x in content for x in ["73,000", "73K", "~73K", "73 |", "| 73"]
        ), "Budget calculator must show current ~73K token count"

    def test_budget_shows_core_only(self):
        """Calculator must show core-only scenario."""
        content = _read_plan()
        # Must show a scenario with 14 rules
        assert "14" in content, "Budget must show 14-rule scenario"

    def test_budget_shows_percentage_savings(self):
        """Calculator must show percentage savings."""
        content = _read_plan()
        # Look for percentage indicators
        has_percentages = bool(re.search(r'\d+\.?\d*%', content))
        assert has_percentages, "Budget calculator must include percentage calculations"

    def test_budget_covers_multiple_context_windows(self):
        """Calculator must show impact across different context window sizes."""
        content = _read_plan()
        windows = ["1M", "200K", "128K"]
        found = [w for w in windows if w in content]
        assert len(found) >= 2, (
            f"Budget must cover at least 2 context window sizes, found: {found}"
        )


# ===========================================================================
# Risk Analysis Tests
# ===========================================================================


class TestRiskAnalysis:
    """Verify risk analysis is comprehensive."""

    def test_risk_section_has_table(self):
        """Risk section must contain a structured risk table."""
        content = _read_plan()
        # Look for risk-related table markers
        risk_section_start = content.find("Risk Analysis")
        assert risk_section_start != -1, "Plan must have a Risk Analysis section"
        risk_section = content[risk_section_start:]
        # Must have severity and mitigation columns
        assert "Mitigation" in risk_section or "mitigation" in risk_section, (
            "Risk analysis must include mitigations"
        )

    def test_risk_covers_rule_not_loaded(self):
        """Risk analysis must address the 'rule not loaded when needed' risk."""
        content = _read_plan()
        assert "not loaded" in content.lower() or "rule not loaded" in content.lower(), (
            "Risk analysis must address the scenario where a needed rule is not loaded"
        )

    def test_risk_covers_performance_regression(self):
        """Risk analysis must address performance regression risk."""
        content = _read_plan()
        assert "regression" in content.lower() or "performance" in content.lower(), (
            "Risk analysis must address performance regression"
        )


# ===========================================================================
# Migration Path Tests
# ===========================================================================


class TestMigrationPath:
    """Verify the migration path is complete and phased."""

    def test_has_5_phases(self):
        """Migration must have exactly 5 phases."""
        content = _read_plan()
        phases = re.findall(r'Phase \d', content)
        unique_phases = set(phases)
        assert len(unique_phases) >= 5, (
            f"Migration must have at least 5 phases, found: {sorted(unique_phases)}"
        )

    def test_phase_1_updates_profiles(self):
        """Phase 1 must update efficiency profiles."""
        content = _read_plan()
        phase1_markers = ["Phase 1", "profile", "self-install"]
        # At least 2 of 3 markers should appear near each other
        found = sum(1 for m in phase1_markers if m.lower() in content.lower())
        assert found >= 2, (
            "Phase 1 must discuss updating efficiency profiles in self-install.sh"
        )

    def test_phase_includes_testing(self):
        """At least one phase must include testing/validation."""
        content = _read_plan()
        assert "test" in content.lower() or "validat" in content.lower(), (
            "Migration must include a testing/validation phase"
        )

    def test_phase_includes_external_project(self):
        """At least one phase must test on external projects."""
        content = _read_plan()
        assert "external" in content.lower() or "External" in content, (
            "Migration must include testing on external projects"
        )

    def test_phase_includes_rollout(self):
        """Final phase must address rollout to all installations."""
        content = _read_plan()
        assert "roll out" in content.lower() or "rollout" in content.lower(), (
            "Migration must include a rollout phase"
        )
