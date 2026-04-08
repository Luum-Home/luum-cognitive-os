"""Behavioral tests for lib/consequence_engine.py.

Covers:
- re_enable_skill() on a skill that was never disabled is a no-op (returns False)
- A skill is DISABLED after 3 consecutive low-score records
- re_enable_skill() clears the disabled streak so the skill is no longer listed
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.consequence_engine import (
    ConsequenceEngine,
    Consequence,
    PerformanceRecord,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    agent: str,
    trust_score: float,
    task_type: str = "general",
    success: bool = True,
) -> PerformanceRecord:
    return PerformanceRecord(
        agent_or_skill=agent,
        task_type=task_type,
        trust_score=trust_score,
        success=success,
        cost_usd=0.01,
        tokens_used=100,
        retries=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _make_engine(tmp_path: Path) -> ConsequenceEngine:
    history = tmp_path / "consequence-history.jsonl"
    return ConsequenceEngine(
        history_path=str(history),
        # Use tight thresholds to make tests fast
        thresholds={
            "promote": 85.0,
            "warn": 60.0,
            "consecutive_fails_to_disable": 3,
            "promote_streak_required": 5,
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReEnableNoop:
    def test_reenable_never_disabled_is_noop(self, tmp_path):
        """re_enable_skill() returns False for a skill that was never disabled."""
        engine = _make_engine(tmp_path)

        result = engine.re_enable_skill("skill-that-never-existed")

        assert result is False, (
            "Expected re_enable_skill to return False for a never-disabled skill, "
            f"got {result!r}"
        )

    def test_reenable_noop_does_not_corrupt_history(self, tmp_path):
        """re_enable_skill() on an unknown skill must not write anything to history."""
        engine = _make_engine(tmp_path)
        history_path = Path(engine.history_path)

        engine.re_enable_skill("ghost-skill")

        # Either the file doesn't exist yet, or it's unchanged from before
        if history_path.exists():
            entries = [l for l in history_path.read_text().splitlines() if l.strip()]
            assert not entries, (
                "History file was written to by a no-op re_enable_skill call"
            )


class TestDisabledAfterThreeConsecutiveFailures:
    def test_disabled_after_3_consecutive_failures(self, tmp_path):
        """Skill must reach DISABLE consequence after 3 consecutive sub-60 scores.

        evaluate() returns the consequence; apply_consequence() persists the
        disable record so that get_disabled_skills() can find it.
        """
        engine = _make_engine(tmp_path)
        agent = "flaky-skill"

        last_action = None
        for _ in range(3):
            record = _make_record(agent, trust_score=40.0)
            last_action = engine.evaluate(record)
            engine.apply_consequence(last_action)

        assert last_action.consequence == Consequence.DISABLE, (
            f"Expected DISABLE after 3 consecutive failures, got "
            f"{last_action.consequence}"
        )

        disabled = engine.get_disabled_skills()
        disabled_names = [d["skill"] for d in disabled]
        assert agent in disabled_names, (
            f"'{agent}' not in disabled skills list: {disabled_names}"
        )

    def test_warn_on_first_failure(self, tmp_path):
        """First sub-60 score must produce WARN, not DISABLE."""
        engine = _make_engine(tmp_path)
        agent = "new-skill"

        record = _make_record(agent, trust_score=45.0)
        action = engine.evaluate(record)

        assert action.consequence == Consequence.WARN, (
            f"Expected WARN on first failure, got {action.consequence}"
        )

    def test_degrade_on_second_consecutive_failure(self, tmp_path):
        """Second consecutive sub-60 score must produce DEGRADE."""
        engine = _make_engine(tmp_path)
        agent = "degrading-skill"

        for _ in range(2):
            record = _make_record(agent, trust_score=50.0)
            action = engine.evaluate(record)

        assert action.consequence == Consequence.DEGRADE, (
            f"Expected DEGRADE on second consecutive failure, got {action.consequence}"
        )


class TestReEnableClearsStreak:
    def test_reenable_clears_streak(self, tmp_path):
        """re_enable_skill() removes a disabled skill from the disabled list."""
        engine = _make_engine(tmp_path)
        agent = "recoverable-skill"

        # Disable the skill via 3 consecutive failures (evaluate + apply)
        for _ in range(3):
            action = engine.evaluate(_make_record(agent, trust_score=30.0))
            engine.apply_consequence(action)

        disabled_before = [d["skill"] for d in engine.get_disabled_skills()]
        assert agent in disabled_before, f"Setup failed: '{agent}' not disabled"

        # Re-enable
        result = engine.re_enable_skill(agent)
        assert result is True, (
            f"re_enable_skill returned False for a known-disabled skill"
        )

        disabled_after = [d["skill"] for d in engine.get_disabled_skills()]
        assert agent not in disabled_after, (
            f"'{agent}' still listed as disabled after re_enable_skill: "
            f"{disabled_after}"
        )

    def test_reenable_allows_new_evaluation(self, tmp_path):
        """After re-enabling, a new high-score record must not immediately re-disable."""
        engine = _make_engine(tmp_path)
        agent = "comeback-skill"

        for _ in range(3):
            action = engine.evaluate(_make_record(agent, trust_score=30.0))
            engine.apply_consequence(action)

        engine.re_enable_skill(agent)

        # A good score should produce MAINTAIN or PROMOTE, not DISABLE
        action = engine.evaluate(_make_record(agent, trust_score=80.0))
        assert action.consequence not in (Consequence.DISABLE, Consequence.WARN), (
            f"Expected MAINTAIN or PROMOTE after re-enable + good score, "
            f"got {action.consequence}"
        )
