"""Behavior tests for harness audit classification logic.

Migrated from test-harness-audit.sh.
"""

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def classify_hook(total_triggers: int, blocks_repairs: int) -> str:
    """Classify a hook based on activity metrics.

    Returns "ACTIVE" | "LOW-VALUE" | "DORMANT".
    """
    if total_triggers == 0:
        return "DORMANT"
    value_ratio = (blocks_repairs * 100) // total_triggers
    if value_ratio >= 5:
        return "ACTIVE"
    return "LOW-VALUE"


def classify_rule(hook_references: int, violation_count: int) -> str:
    """Classify a rule based on references.

    Returns "ACTIVE" | "PASSIVE" | "ORPHANED".
    """
    if hook_references == 0 and violation_count == 0:
        return "ORPHANED"
    if violation_count > 0:
        return "ACTIVE"
    return "PASSIVE"


def classify_skill(usage_count: int, success_rate: int) -> str:
    """Classify a skill based on usage.

    Returns "ACTIVE" | "UNDERPERFORMING" | "UNUSED".
    """
    if usage_count == 0:
        return "UNUSED"
    if success_rate < 50:
        return "UNDERPERFORMING"
    return "ACTIVE"


# ---------------------------------------------------------------------------
# Tests: Hook classification
# ---------------------------------------------------------------------------


class TestHookClassification:

    def test_dormant(self):
        assert classify_hook(0, 0) == "DORMANT"

    def test_low_value(self):
        assert classify_hook(100, 2) == "LOW-VALUE"

    def test_active_10pct(self):
        assert classify_hook(100, 10) == "ACTIVE"

    def test_active_100pct(self):
        assert classify_hook(50, 50) == "ACTIVE"


# ---------------------------------------------------------------------------
# Tests: Rule classification
# ---------------------------------------------------------------------------


class TestRuleClassification:

    def test_active(self):
        assert classify_rule(3, 5) == "ACTIVE"

    def test_passive(self):
        assert classify_rule(2, 0) == "PASSIVE"

    def test_orphaned(self):
        assert classify_rule(0, 0) == "ORPHANED"


# ---------------------------------------------------------------------------
# Tests: Skill classification
# ---------------------------------------------------------------------------


class TestSkillClassification:

    def test_active(self):
        assert classify_skill(10, 80) == "ACTIVE"

    def test_underperforming(self):
        assert classify_skill(5, 30) == "UNDERPERFORMING"

    def test_unused(self):
        assert classify_skill(0, 0) == "UNUSED"
