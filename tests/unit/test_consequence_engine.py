"""Unit tests for lib/consequence_engine.py

Validates consequence evaluation logic: promotion streaks, warn/degrade/disable
escalation, apply actions, OKR status, reporting, persistence, and re-enable.

Python 3.9+ compatible.
"""

import json
from pathlib import Path

import pytest

from lib.consequence_engine import (
    Consequence,
    ConsequenceAction,
    ConsequenceEngine,
    PerformanceRecord,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def history_file(tmp_path: Path) -> str:
    """Return path to a temporary consequence-history.jsonl file."""
    return str(tmp_path / "consequence-history.jsonl")


@pytest.fixture()
def engine(history_file: str) -> ConsequenceEngine:
    """Return a ConsequenceEngine pointing at a temp file."""
    return ConsequenceEngine(history_path=history_file)


def _make_record(
    score: float,
    skill: str = "test-skill",
    task_type: str = "general",
    success: bool = True,
    cost: float = 0.05,
    tokens: int = 1000,
    retries: int = 0,
    ts: str = "2026-03-27T12:00:00Z",
) -> PerformanceRecord:
    return PerformanceRecord(
        agent_or_skill=skill,
        task_type=task_type,
        trust_score=score,
        success=success,
        cost_usd=cost,
        tokens_used=tokens,
        retries=retries,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# evaluate: high score -> PROMOTE after streak
# ---------------------------------------------------------------------------

class TestEvaluatePromote:
    def test_promote_after_5_consecutive_high_scores(self, engine: ConsequenceEngine) -> None:
        """5 consecutive scores >= 85 should trigger PROMOTE."""
        for i in range(4):
            engine.evaluate(_make_record(90.0, ts=f"2026-03-27T12:0{i}:00Z"))
        action = engine.evaluate(_make_record(88.0, ts="2026-03-27T12:05:00Z"))
        assert action.consequence == Consequence.PROMOTE

    def test_no_promote_with_insufficient_streak(self, engine: ConsequenceEngine) -> None:
        """3 high scores is not enough for promotion (need 5)."""
        for i in range(2):
            engine.evaluate(_make_record(90.0, ts=f"2026-03-27T12:0{i}:00Z"))
        action = engine.evaluate(_make_record(90.0, ts="2026-03-27T12:03:00Z"))
        assert action.consequence == Consequence.MAINTAIN

    def test_promote_streak_resets_on_low_score(self, engine: ConsequenceEngine) -> None:
        """A low score in the middle resets the promote streak."""
        for i in range(3):
            engine.evaluate(_make_record(90.0, ts=f"2026-03-27T12:0{i}:00Z"))
        engine.evaluate(_make_record(50.0, ts="2026-03-27T12:04:00Z"))
        # Now add 4 more high scores -- still only 4 in a row
        for i in range(4):
            action = engine.evaluate(_make_record(90.0, ts=f"2026-03-27T12:1{i}:00Z"))
        assert action.consequence == Consequence.MAINTAIN


# ---------------------------------------------------------------------------
# evaluate: medium score -> MAINTAIN
# ---------------------------------------------------------------------------

class TestEvaluateMaintain:
    def test_score_in_acceptable_range_returns_maintain(self, engine: ConsequenceEngine) -> None:
        action = engine.evaluate(_make_record(75.0))
        assert action.consequence == Consequence.MAINTAIN

    def test_score_at_warn_boundary_returns_maintain(self, engine: ConsequenceEngine) -> None:
        action = engine.evaluate(_make_record(60.0))
        assert action.consequence == Consequence.MAINTAIN

    def test_high_score_without_streak_returns_maintain(self, engine: ConsequenceEngine) -> None:
        action = engine.evaluate(_make_record(90.0))
        assert action.consequence == Consequence.MAINTAIN


# ---------------------------------------------------------------------------
# evaluate: low score -> WARN / DEGRADE / DISABLE
# ---------------------------------------------------------------------------

class TestEvaluateWarn:
    def test_first_low_score_returns_warn(self, engine: ConsequenceEngine) -> None:
        action = engine.evaluate(_make_record(45.0))
        assert action.consequence == Consequence.WARN

    def test_warn_includes_reason(self, engine: ConsequenceEngine) -> None:
        action = engine.evaluate(_make_record(50.0))
        assert "50%" in action.reason
        assert "60%" in action.reason


class TestEvaluateDegrade:
    def test_second_consecutive_low_returns_degrade(self, engine: ConsequenceEngine) -> None:
        engine.evaluate(_make_record(40.0, ts="2026-03-27T12:00:00Z"))
        action = engine.evaluate(_make_record(45.0, ts="2026-03-27T12:01:00Z"))
        assert action.consequence == Consequence.DEGRADE

    def test_degrade_includes_consecutive_count(self, engine: ConsequenceEngine) -> None:
        engine.evaluate(_make_record(40.0, ts="2026-03-27T12:00:00Z"))
        action = engine.evaluate(_make_record(45.0, ts="2026-03-27T12:01:00Z"))
        assert "2 consecutive" in action.reason


class TestEvaluateDisable:
    def test_third_consecutive_low_returns_disable(self, engine: ConsequenceEngine) -> None:
        engine.evaluate(_make_record(30.0, ts="2026-03-27T12:00:00Z"))
        engine.evaluate(_make_record(40.0, ts="2026-03-27T12:01:00Z"))
        action = engine.evaluate(_make_record(35.0, ts="2026-03-27T12:02:00Z"))
        assert action.consequence == Consequence.DISABLE

    def test_disable_reason_mentions_consecutive(self, engine: ConsequenceEngine) -> None:
        for i in range(2):
            engine.evaluate(_make_record(30.0, ts=f"2026-03-27T12:0{i}:00Z"))
        action = engine.evaluate(_make_record(30.0, ts="2026-03-27T12:03:00Z"))
        assert "3 consecutive" in action.reason


# ---------------------------------------------------------------------------
# apply_consequence
# ---------------------------------------------------------------------------

class TestApplyConsequence:
    def test_promote_saves_snapshot(self, engine: ConsequenceEngine, history_file: str) -> None:
        action = ConsequenceAction(
            target="sdd-verify",
            consequence=Consequence.PROMOTE,
            reason="5 consecutive high scores",
            actions_taken=[],
            timestamp="2026-03-27T12:00:00Z",
        )
        result = engine.apply_consequence(action)
        assert len(result) == 1
        assert "Promoted" in result[0]
        assert "sdd-verify" in result[0]
        # Check promotion record was persisted (MetricEvent shape: event_type contains "promotion")
        lines = Path(history_file).read_text().strip().splitlines()
        promo_lines = [l for l in lines if "promotion" in l]
        assert len(promo_lines) == 1

    def test_degrade_suggests_model_downgrade(self, engine: ConsequenceEngine) -> None:
        action = ConsequenceAction(
            target="opus-task",
            consequence=Consequence.DEGRADE,
            reason="2 consecutive low scores",
            actions_taken=[],
            timestamp="2026-03-27T12:00:00Z",
        )
        result = engine.apply_consequence(action)
        assert len(result) == 1
        assert "Degraded" in result[0]

    def test_disable_adds_to_disabled_list(self, engine: ConsequenceEngine) -> None:
        action = ConsequenceAction(
            target="broken-skill",
            consequence=Consequence.DISABLE,
            reason="3 consecutive failures",
            actions_taken=[],
            timestamp="2026-03-27T12:00:00Z",
        )
        engine.apply_consequence(action)
        disabled = engine.get_disabled_skills()
        assert len(disabled) == 1
        assert disabled[0]["skill"] == "broken-skill"

    def test_warn_returns_warning_message(self, engine: ConsequenceEngine) -> None:
        action = ConsequenceAction(
            target="flaky-skill",
            consequence=Consequence.WARN,
            reason="Score 55% below threshold",
            actions_taken=[],
            timestamp="2026-03-27T12:00:00Z",
        )
        result = engine.apply_consequence(action)
        assert len(result) == 1
        assert "Warning" in result[0]


# ---------------------------------------------------------------------------
# get_disabled_skills and re_enable_skill
# ---------------------------------------------------------------------------

class TestDisabledSkills:
    def test_get_disabled_skills_returns_empty_initially(self, engine: ConsequenceEngine) -> None:
        assert engine.get_disabled_skills() == []

    def test_re_enable_skill_removes_from_disabled(self, engine: ConsequenceEngine) -> None:
        # Disable a skill
        action = ConsequenceAction(
            target="bad-skill",
            consequence=Consequence.DISABLE,
            reason="3 fails",
            actions_taken=[],
            timestamp="2026-03-27T12:00:00Z",
        )
        engine.apply_consequence(action)
        assert len(engine.get_disabled_skills()) == 1
        # Re-enable
        result = engine.re_enable_skill("bad-skill")
        assert result is True
        assert len(engine.get_disabled_skills()) == 0

    def test_re_enable_nonexistent_returns_false(self, engine: ConsequenceEngine) -> None:
        assert engine.re_enable_skill("never-disabled") is False


# ---------------------------------------------------------------------------
# get_promotions
# ---------------------------------------------------------------------------

class TestGetPromotions:
    def test_get_promotions_returns_recent(self, engine: ConsequenceEngine) -> None:
        for i in range(5):
            engine.evaluate(_make_record(90.0, ts=f"2026-03-27T12:0{i}:00Z"))
        # The 5th should trigger a promotion which persists a promotion record
        promotions = engine.get_promotions()
        assert len(promotions) == 0  # evaluate() does not call apply_consequence
        # But if we explicitly apply:
        action = ConsequenceAction(
            target="promoted-skill",
            consequence=Consequence.PROMOTE,
            reason="streak",
            actions_taken=[],
            timestamp="2026-03-27T13:00:00Z",
        )
        engine.apply_consequence(action)
        promotions = engine.get_promotions()
        assert len(promotions) == 1
        assert promotions[0].target == "promoted-skill"


# ---------------------------------------------------------------------------
# get_okr_status
# ---------------------------------------------------------------------------

class TestGetOkrStatus:
    def test_okr_status_calculates_quality(self, engine: ConsequenceEngine) -> None:
        for i in range(5):
            engine.evaluate(_make_record(95.0, ts=f"2026-03-27T12:0{i}:00Z"))
        status = engine.get_okr_status()
        assert status["agent_quality_okr"]["status"] == "ON_TRACK"
        assert "95" in status["agent_quality_okr"]["actual"]

    def test_okr_status_behind_with_low_scores(self, engine: ConsequenceEngine) -> None:
        for i in range(5):
            engine.evaluate(_make_record(50.0, ts=f"2026-03-27T12:0{i}:00Z"))
        status = engine.get_okr_status()
        assert status["agent_quality_okr"]["status"] == "BEHIND"

    def test_okr_empty_history(self, engine: ConsequenceEngine) -> None:
        status = engine.get_okr_status()
        assert status["agent_quality_okr"]["actual"] == "0.0%"


# ---------------------------------------------------------------------------
# format_consequence_report
# ---------------------------------------------------------------------------

class TestFormatConsequenceReport:
    def test_report_has_all_sections(self, engine: ConsequenceEngine) -> None:
        engine.evaluate(_make_record(90.0))
        report = engine.format_consequence_report()
        assert "OKR CONSEQUENCE REPORT" in report
        assert "PROMOTIONS" in report
        assert "WARNINGS" in report
        assert "DISABLED" in report
        assert "DEGRADED" in report
        assert "OKR STATUS" in report

    def test_report_empty_history(self, engine: ConsequenceEngine) -> None:
        report = engine.format_consequence_report()
        assert "OKR CONSEQUENCE REPORT" in report
        assert "(none)" in report


# ---------------------------------------------------------------------------
# save_action persistence
# ---------------------------------------------------------------------------

class TestSaveAction:
    def test_save_action_persists_to_jsonl(self, engine: ConsequenceEngine, history_file: str) -> None:
        action = ConsequenceAction(
            target="my-skill",
            consequence=Consequence.WARN,
            reason="low score",
            actions_taken=["Warning for my-skill"],
            timestamp="2026-03-27T12:00:00Z",
        )
        engine.save_action(action)
        lines = Path(history_file).read_text().strip().splitlines()
        assert len(lines) >= 1
        raw = json.loads(lines[-1])
        # MetricEvent shape: record_type encoded in event_type, payload holds fields
        assert raw.get("schema_version") == 1
        assert "consequence.action" in raw.get("event_type", "")
        payload = raw["payload"]
        assert payload["target"] == "my-skill"
        assert payload["consequence"] == "warn"


# ---------------------------------------------------------------------------
# performance_history filtered by skill
# ---------------------------------------------------------------------------

class TestPerformanceHistory:
    def test_history_filtered_by_skill(self, engine: ConsequenceEngine) -> None:
        engine.evaluate(_make_record(90.0, skill="skill-a", ts="2026-03-27T12:00:00Z"))
        engine.evaluate(_make_record(80.0, skill="skill-b", ts="2026-03-27T12:01:00Z"))
        engine.evaluate(_make_record(85.0, skill="skill-a", ts="2026-03-27T12:02:00Z"))

        history_a = engine.get_performance_history("skill-a")
        assert len(history_a) == 2
        assert all(r.agent_or_skill == "skill-a" for r in history_a)

        history_b = engine.get_performance_history("skill-b")
        assert len(history_b) == 1

    def test_history_respects_last_n(self, engine: ConsequenceEngine) -> None:
        for i in range(20):
            engine.evaluate(_make_record(70.0 + i, ts=f"2026-03-27T12:{i:02d}:00Z"))
        history = engine.get_performance_history("test-skill", last_n=5)
        assert len(history) == 5


# ---------------------------------------------------------------------------
# consecutive detection across mixed scores
# ---------------------------------------------------------------------------

class TestConsecutiveDetection:
    def test_high_score_breaks_consecutive_low(self, engine: ConsequenceEngine) -> None:
        """A high score between two low scores resets consecutive count."""
        engine.evaluate(_make_record(40.0, ts="2026-03-27T12:00:00Z"))
        engine.evaluate(_make_record(80.0, ts="2026-03-27T12:01:00Z"))
        action = engine.evaluate(_make_record(40.0, ts="2026-03-27T12:02:00Z"))
        # Only 1 consecutive low (the last one), not 2
        assert action.consequence == Consequence.WARN


# ---------------------------------------------------------------------------
# thresholds configurable
# ---------------------------------------------------------------------------

class TestConfigurableThresholds:
    def test_custom_promote_threshold(self, history_file: str) -> None:
        engine = ConsequenceEngine(
            history_path=history_file,
            thresholds={"promote": 95.0, "promote_streak_required": 3},
        )
        for i in range(3):
            action = engine.evaluate(_make_record(96.0, ts=f"2026-03-27T12:0{i}:00Z"))
        assert action.consequence == Consequence.PROMOTE

    def test_custom_warn_threshold(self, history_file: str) -> None:
        engine = ConsequenceEngine(
            history_path=history_file,
            thresholds={"warn": 70.0},
        )
        action = engine.evaluate(_make_record(65.0))
        assert action.consequence == Consequence.WARN

    def test_custom_consecutive_fails_to_disable(self, history_file: str) -> None:
        engine = ConsequenceEngine(
            history_path=history_file,
            thresholds={"consecutive_fails_to_disable": 2},
        )
        engine.evaluate(_make_record(30.0, ts="2026-03-27T12:00:00Z"))
        action = engine.evaluate(_make_record(30.0, ts="2026-03-27T12:01:00Z"))
        assert action.consequence == Consequence.DISABLE
