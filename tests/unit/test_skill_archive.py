"""Unit tests for lib/skill_archive.py

Validates snapshot recording, best-version selection, archive statistics,
trend detection, underperformance flagging, rollback decisions, and
report formatting.

Python 3.9+ compatible.
"""

import json
from pathlib import Path

import pytest

from lib.skill_archive import (
    SkillArchive,
    SkillArchiveManager,
    SkillSnapshot,
    _content_hash,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def archive_file(tmp_path: Path) -> str:
    """Return path to a temporary archive JSONL file."""
    return str(tmp_path / "skill-archive.jsonl")


@pytest.fixture()
def mgr(archive_file: str) -> SkillArchiveManager:
    """Return a SkillArchiveManager pointing at a temp file."""
    return SkillArchiveManager(archive_path=archive_file)


# ---------------------------------------------------------------------------
# record_execution
# ---------------------------------------------------------------------------

class TestRecordExecution:
    def test_creates_snapshot_with_content_hash(self, mgr: SkillArchiveManager, archive_file: str) -> None:
        snap = mgr.record_execution(
            skill_name="sdd-verify",
            skill_content="# Verify\nCheck stuff",
            trust_score=85.0,
            success=True,
            task="verify auth module",
        )
        assert snap.version == _content_hash("# Verify\nCheck stuff")
        assert snap.skill_name == "sdd-verify"
        assert snap.trust_score == 85.0
        assert snap.success is True
        # File should have exactly one line
        lines = Path(archive_file).read_text().strip().splitlines()
        assert len(lines) == 1

    def test_content_hash_changes_when_content_changes(self, mgr: SkillArchiveManager) -> None:
        s1 = mgr.record_execution("a", "version-1", 80, True, "t")
        s2 = mgr.record_execution("a", "version-2", 80, True, "t")
        assert s1.version != s2.version

    def test_records_tokens_and_cost(self, mgr: SkillArchiveManager) -> None:
        snap = mgr.record_execution(
            "skill-x", "content", 90, True, "task",
            tokens=5000, cost=0.07,
        )
        assert snap.tokens_used == 5000
        assert snap.cost_usd == 0.07

    def test_records_metadata(self, mgr: SkillArchiveManager) -> None:
        snap = mgr.record_execution(
            "skill-x", "content", 90, True, "task",
            metadata={"model": "sonnet"},
        )
        assert snap.metadata == {"model": "sonnet"}


# ---------------------------------------------------------------------------
# get_best_version
# ---------------------------------------------------------------------------

class TestGetBestVersion:
    def test_returns_highest_scoring_success(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 70, True, "t1")
        mgr.record_execution("s", "v2", 95, True, "t2")
        mgr.record_execution("s", "v3", 80, True, "t3")
        best = mgr.get_best_version("s")
        assert best is not None
        assert best.trust_score == 95
        assert best.version == _content_hash("v2")

    def test_ignores_failures(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 99, False, "t1")  # fail
        mgr.record_execution("s", "v2", 60, True, "t2")   # success
        best = mgr.get_best_version("s")
        assert best is not None
        assert best.trust_score == 60

    def test_returns_none_for_empty_archive(self, mgr: SkillArchiveManager) -> None:
        assert mgr.get_best_version("nonexistent") is None

    def test_returns_none_when_all_failures(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 90, False, "t1")
        mgr.record_execution("s", "v2", 85, False, "t2")
        assert mgr.get_best_version("s") is None


# ---------------------------------------------------------------------------
# get_archive
# ---------------------------------------------------------------------------

class TestGetArchive:
    def test_computes_correct_stats(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 80, True, "t1")
        mgr.record_execution("s", "v1", 90, True, "t2")
        mgr.record_execution("s", "v1", 70, False, "t3")
        archive = mgr.get_archive("s")
        assert archive.total_uses == 3
        assert archive.success_rate == pytest.approx(2 / 3)
        assert archive.best_score == 90

    def test_empty_archive(self, mgr: SkillArchiveManager) -> None:
        archive = mgr.get_archive("nonexistent")
        assert archive.total_uses == 0
        assert archive.success_rate == 0.0
        assert archive.best_version is None

    def test_success_rate_all_success(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 80, True, "t1")
        mgr.record_execution("s", "v1", 85, True, "t2")
        archive = mgr.get_archive("s")
        assert archive.success_rate == 1.0

    def test_success_rate_all_failure(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 80, False, "t1")
        mgr.record_execution("s", "v1", 85, False, "t2")
        archive = mgr.get_archive("s")
        assert archive.success_rate == 0.0


# ---------------------------------------------------------------------------
# get_skill_trend
# ---------------------------------------------------------------------------

class TestGetSkillTrend:
    def test_improving_trend(self, mgr: SkillArchiveManager) -> None:
        # Old scores low, recent scores high
        for score in [50, 55, 52, 48, 53, 80, 85, 90, 88, 92]:
            mgr.record_execution("s", "v", score, True, "t")
        trend = mgr.get_skill_trend("s")
        assert trend["trend"] == "improving"
        assert trend["last_5_avg"] > trend["all_time_avg"]

    def test_degrading_trend(self, mgr: SkillArchiveManager) -> None:
        # Old scores high, recent scores low
        for score in [90, 92, 88, 95, 91, 50, 48, 52, 45, 55]:
            mgr.record_execution("s", "v", score, True, "t")
        trend = mgr.get_skill_trend("s")
        assert trend["trend"] == "degrading"
        assert trend["last_5_avg"] < trend["all_time_avg"]

    def test_stable_trend(self, mgr: SkillArchiveManager) -> None:
        for score in [80, 82, 78, 81, 79, 80, 81, 79, 82, 80]:
            mgr.record_execution("s", "v", score, True, "t")
        trend = mgr.get_skill_trend("s")
        assert trend["trend"] == "stable"

    def test_single_execution(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v", 80, True, "t")
        trend = mgr.get_skill_trend("s")
        assert trend["trend"] == "stable"
        assert trend["last_5_avg"] == 80.0

    def test_no_executions(self, mgr: SkillArchiveManager) -> None:
        trend = mgr.get_skill_trend("nonexistent")
        assert trend["trend"] == "stable"
        assert trend["all_time_avg"] == 0.0


# ---------------------------------------------------------------------------
# get_underperforming_skills
# ---------------------------------------------------------------------------

class TestGetUnderperformingSkills:
    def test_filters_below_threshold(self, mgr: SkillArchiveManager) -> None:
        # skill-a: 50% success
        mgr.record_execution("skill-a", "v", 80, True, "t")
        mgr.record_execution("skill-a", "v", 30, False, "t")
        # skill-b: 100% success
        mgr.record_execution("skill-b", "v", 90, True, "t")
        mgr.record_execution("skill-b", "v", 85, True, "t")

        under = mgr.get_underperforming_skills(threshold=0.6)
        assert "skill-a" in under
        assert "skill-b" not in under

    def test_empty_archive(self, mgr: SkillArchiveManager) -> None:
        assert mgr.get_underperforming_skills() == []

    def test_custom_threshold(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v", 80, True, "t")
        mgr.record_execution("s", "v", 30, False, "t")
        # 50% success rate
        assert "s" in mgr.get_underperforming_skills(threshold=0.6)
        assert "s" not in mgr.get_underperforming_skills(threshold=0.4)


# ---------------------------------------------------------------------------
# get_top_skills
# ---------------------------------------------------------------------------

class TestGetTopSkills:
    def test_sorts_by_average_score(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("low", "v", 50, True, "t")
        mgr.record_execution("low", "v", 55, True, "t")
        mgr.record_execution("high", "v", 90, True, "t")
        mgr.record_execution("high", "v", 95, True, "t")
        mgr.record_execution("mid", "v", 70, True, "t")

        top = mgr.get_top_skills(n=3)
        assert len(top) == 3
        assert top[0][0] == "high"
        assert top[1][0] == "mid"
        assert top[2][0] == "low"

    def test_excludes_failures(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v", 99, False, "t")
        mgr.record_execution("s", "v", 60, True, "t")
        top = mgr.get_top_skills()
        assert len(top) == 1
        assert top[0][1] == 60.0

    def test_limits_to_n(self, mgr: SkillArchiveManager) -> None:
        for i in range(20):
            mgr.record_execution(f"skill-{i}", "v", 80 + i, True, "t")
        top = mgr.get_top_skills(n=5)
        assert len(top) == 5


# ---------------------------------------------------------------------------
# should_rollback
# ---------------------------------------------------------------------------

class TestShouldRollback:
    def test_true_when_current_much_worse_than_best(self, mgr: SkillArchiveManager) -> None:
        # Best version scored 95
        mgr.record_execution("s", "old-content", 95, True, "t1")
        # Current version scores 70 (delta=25 > 20)
        mgr.record_execution("s", "new-content", 70, True, "t2")

        should, reason = mgr.should_rollback("s")
        assert should is True
        assert "20" in reason or "delta" in reason.lower() or _content_hash("new-content") in reason

    def test_false_when_current_is_best(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 90, True, "t1")
        mgr.record_execution("s", "v1", 92, True, "t2")
        should, reason = mgr.should_rollback("s")
        assert should is False

    def test_false_for_empty_archive(self, mgr: SkillArchiveManager) -> None:
        should, reason = mgr.should_rollback("nonexistent")
        assert should is False

    def test_true_when_current_has_no_successes(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "old-good", 90, True, "t1")
        mgr.record_execution("s", "new-bad", 20, False, "t2")
        should, reason = mgr.should_rollback("s")
        assert should is True

    def test_false_when_delta_small(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "old", 85, True, "t1")
        mgr.record_execution("s", "new", 80, True, "t2")
        should, _ = mgr.should_rollback("s")
        assert should is False


# ---------------------------------------------------------------------------
# Multiple skills tracked independently
# ---------------------------------------------------------------------------

class TestMultipleSkills:
    def test_independent_tracking(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("alpha", "v1", 90, True, "t")
        mgr.record_execution("beta", "v1", 60, True, "t")
        mgr.record_execution("beta", "v1", 40, False, "t")

        alpha_archive = mgr.get_archive("alpha")
        beta_archive = mgr.get_archive("beta")
        assert alpha_archive.total_uses == 1
        assert beta_archive.total_uses == 2
        assert alpha_archive.success_rate == 1.0
        assert beta_archive.success_rate == 0.5


# ---------------------------------------------------------------------------
# format_archive_report
# ---------------------------------------------------------------------------

class TestFormatArchiveReport:
    def test_single_skill_report_has_sections(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("s", "v1", 85, True, "task-a")
        mgr.record_execution("s", "v1", 90, True, "task-b")
        report = mgr.format_archive_report(skill_name="s")
        assert "SKILL ARCHIVE REPORT: s" in report
        assert "Total uses: 2" in report
        assert "Success rate:" in report
        assert "Trend:" in report
        assert "Best version:" in report

    def test_summary_report_lists_all_skills(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("alpha", "v", 90, True, "t")
        mgr.record_execution("beta", "v", 80, True, "t")
        report = mgr.format_archive_report()
        assert "SKILL ARCHIVE REPORT" in report
        assert "alpha" in report
        assert "beta" in report

    def test_empty_archive_report(self, mgr: SkillArchiveManager) -> None:
        report = mgr.format_archive_report()
        assert "No skill executions" in report

    def test_underperforming_shows_recommendation(self, mgr: SkillArchiveManager) -> None:
        mgr.record_execution("bad-skill", "v", 30, False, "t1")
        mgr.record_execution("bad-skill", "v", 40, False, "t2")
        mgr.record_execution("bad-skill", "v", 50, True, "t3")
        report = mgr.format_archive_report()
        assert "/optimize-skill" in report


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

class TestCostTracking:
    def test_cost_persisted(self, mgr: SkillArchiveManager, archive_file: str) -> None:
        mgr.record_execution("s", "v", 80, True, "t", cost=0.05)
        data = json.loads(Path(archive_file).read_text().strip())
        assert data["cost_usd"] == 0.05
