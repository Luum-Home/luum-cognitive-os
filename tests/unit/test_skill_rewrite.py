"""Unit tests for skill-rewrite detection.

Tests ConsequenceEngine.get_skills_needing_rewrite() which surfaces skills
that have failed >= threshold times within a rolling time window.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


# Make sure lib is on the path regardless of working directory
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.consequence_engine import ConsequenceEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _failure_record(skill: str, task_type: str = "test-task", hours_ago: float = 1.0) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return {
        "record_type": "performance",
        "agent_or_skill": skill,
        "task_type": task_type,
        "trust_score": 30.0,
        "success": False,
        "cost_usd": 0.01,
        "tokens_used": 500,
        "retries": 0,
        "timestamp": ts.isoformat(),
    }


def _success_record(skill: str, task_type: str = "test-task", hours_ago: float = 1.0) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return {
        "record_type": "performance",
        "agent_or_skill": skill,
        "task_type": task_type,
        "trust_score": 90.0,
        "success": True,
        "cost_usd": 0.01,
        "tokens_used": 500,
        "retries": 0,
        "timestamp": ts.isoformat(),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetSkillsNeedingRewrite:

    def test_detects_skill_needing_rewrite(self, tmp_path):
        """3+ failures in 24h triggers a rewrite suggestion."""
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            _failure_record("sdd-apply", hours_ago=0.5),
            _failure_record("sdd-apply", hours_ago=1.0),
            _failure_record("sdd-apply", hours_ago=2.0),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)

        assert len(results) == 1
        assert results[0]["skill_name"] == "sdd-apply"
        assert results[0]["failure_count"] == 3
        assert "/optimize-skill sdd-apply" in results[0]["suggested_action"]

    def test_ignores_old_failures(self, tmp_path):
        """Failures older than the time window are not counted."""
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            # Two within the 24h window
            _failure_record("old-skill", hours_ago=0.5),
            _failure_record("old-skill", hours_ago=1.0),
            # One outside the 24h window
            _failure_record("old-skill", hours_ago=25.0),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)

        # Only 2 failures inside window — below threshold of 3
        assert results == []

    def test_ignores_skills_below_threshold(self, tmp_path):
        """2 failures do not trigger a rewrite with threshold=3."""
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            _failure_record("sdd-spec", hours_ago=0.5),
            _failure_record("sdd-spec", hours_ago=1.0),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)

        assert results == []

    def test_returns_failure_context(self, tmp_path):
        """Result includes last_error taken from task_type of most recent failure."""
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            _failure_record("sdd-verify", task_type="build_error", hours_ago=3.0),
            _failure_record("sdd-verify", task_type="test_failure", hours_ago=2.0),
            _failure_record("sdd-verify", task_type="lint_error", hours_ago=0.5),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)

        assert len(results) == 1
        # Most recent failure is lint_error (0.5h ago)
        assert results[0]["last_error"] == "lint_error"

    def test_multiple_skills_needing_rewrite(self, tmp_path):
        """Multiple failing skills are all returned, sorted by failure_count."""
        history = tmp_path / "consequence-history.jsonl"
        records = (
            [_failure_record("skill-a", hours_ago=i * 0.5) for i in range(1, 6)]  # 5 failures
            + [_failure_record("skill-b", hours_ago=i * 0.5) for i in range(1, 4)]  # 3 failures
            + [_failure_record("skill-c", hours_ago=0.5)]  # 1 failure (below threshold)
        )
        _write_records(history, records)

        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)

        assert len(results) == 2
        # skill-a has 5 failures, skill-b has 3 → sorted descending
        assert results[0]["skill_name"] == "skill-a"
        assert results[0]["failure_count"] == 5
        assert results[1]["skill_name"] == "skill-b"
        assert results[1]["failure_count"] == 3

    def test_success_records_not_counted_as_failures(self, tmp_path):
        """Success records do not inflate the failure count."""
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            _failure_record("mixed-skill", hours_ago=1.0),
            _success_record("mixed-skill", hours_ago=0.8),
            _failure_record("mixed-skill", hours_ago=0.5),
            _success_record("mixed-skill", hours_ago=0.2),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        # Only 2 failures → below threshold of 3
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)
        assert results == []

    def test_phase_aware_output_recon_vs_prod(self, tmp_path):
        """Verify the suggested_action field is present for both phases.

        Phase-specific *output wording* is handled by completion-gate.sh,
        not by get_skills_needing_rewrite itself. The method always returns
        the same structured data. This test confirms the data is correct so
        the hook can apply the correct label.
        """
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            _failure_record("optimize-skill", hours_ago=0.5),
            _failure_record("optimize-skill", hours_ago=1.0),
            _failure_record("optimize-skill", hours_ago=2.0),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)

        assert len(results) == 1
        skill = results[0]
        # Data is the same regardless of phase; hook applies the label
        assert skill["skill_name"] == "optimize-skill"
        assert skill["failure_count"] == 3
        assert "suggested_action" in skill
        assert "/optimize-skill" in skill["suggested_action"]

    def test_empty_history_returns_empty_list(self, tmp_path):
        """An empty or missing history file returns no suggestions."""
        history = tmp_path / "consequence-history.jsonl"
        # Don't write the file at all
        engine = ConsequenceEngine(history_path=str(history))
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=3, hours=24)
        assert results == []

    def test_custom_threshold_and_hours(self, tmp_path):
        """Custom threshold and window are respected."""
        history = tmp_path / "consequence-history.jsonl"
        _write_records(history, [
            _failure_record("fast-skill", hours_ago=0.3),
            _failure_record("fast-skill", hours_ago=0.6),
        ])

        engine = ConsequenceEngine(history_path=str(history))
        # threshold=2, hours=1 → 2 failures in 1h window → should trigger
        results = engine.get_skills_needing_rewrite(str(tmp_path), threshold=2, hours=1)
        assert len(results) == 1
        assert results[0]["skill_name"] == "fast-skill"
        assert results[0]["failure_count"] == 2
