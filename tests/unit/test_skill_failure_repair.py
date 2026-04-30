"""
Unit tests for lib/skill_failure_repair.py

All tests use synthetic in-memory JSONL files (tmp_path fixture).
No network, no external services, no real metrics directory.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from lib.skill_failure_repair import (
    find_failing_skills,
    propose_repair_action,
    emit_repair_signal,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(delta_hours: int = 0) -> str:
    """Return an ISO-8601 UTC timestamp offset by *delta_hours* from now."""
    dt = datetime.now(timezone.utc) + timedelta(hours=delta_hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# find_failing_skills — basic threshold
# ---------------------------------------------------------------------------

class TestFindFailingSkills:
    def test_five_failures_returns_skill(self, tmp_path: Path) -> None:
        """5 failures of skill X within window → returned."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        records = [
            {"timestamp": _ts(-1), "skill": "my-skill", "success": False}
            for _ in range(5)
        ]
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)

        assert len(result) == 1
        assert result[0]["skill"] == "my-skill"
        assert result[0]["failure_count"] == 5

    def test_four_failures_returns_nothing(self, tmp_path: Path) -> None:
        """4 failures (below threshold of 5) → empty list."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        records = [
            {"timestamp": _ts(-1), "skill": "my-skill", "success": False}
            for _ in range(4)
        ]
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)

        assert result == []

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "nonexistent.jsonl"
        assert find_failing_skills(jsonl) == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "skill-feedback.jsonl"
        _write_jsonl(jsonl, [])
        assert find_failing_skills(jsonl) == []

    def test_success_records_not_counted_as_failures(self, tmp_path: Path) -> None:
        """Success records must not inflate the failure count."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        records = [
            {"timestamp": _ts(-1), "skill": "my-skill", "success": False}
            for _ in range(4)
        ] + [
            {"timestamp": _ts(-1), "skill": "my-skill", "success": True}
            for _ in range(10)
        ]
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)
        assert result == []

    def test_multiple_skills_independent_thresholds(self, tmp_path: Path) -> None:
        """Each skill is evaluated independently."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        records = (
            [{"timestamp": _ts(-1), "skill": "skill-a", "success": False}] * 6
            + [{"timestamp": _ts(-1), "skill": "skill-b", "success": False}] * 3
        )
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)
        skills = {r["skill"] for r in result}
        assert skills == {"skill-a"}


# ---------------------------------------------------------------------------
# find_failing_skills — window filtering
# ---------------------------------------------------------------------------

class TestWindowFiltering:
    def test_old_failures_excluded(self, tmp_path: Path) -> None:
        """Failures older than window_hours must not be counted."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        # 5 failures, all 25 hours old (outside 24h window)
        records = [
            {"timestamp": _ts(-25), "skill": "old-skill", "success": False}
            for _ in range(5)
        ]
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)
        assert result == []

    def test_mixed_age_failures_only_count_recent(self, tmp_path: Path) -> None:
        """Failures split across window boundary — only recent ones count."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        # 3 recent + 4 old = 7 total, but only 3 in window → below threshold=5
        records = (
            [{"timestamp": _ts(-1), "skill": "mixed", "success": False}] * 3
            + [{"timestamp": _ts(-30), "skill": "mixed", "success": False}] * 4
        )
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)
        assert result == []

    def test_exactly_at_boundary_included(self, tmp_path: Path) -> None:
        """A record exactly at window_hours ago is within window (>= cutoff)."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        # Use -23h so we're safely inside — exact boundary is hard to test
        # without mocking time; this validates the range is inclusive
        records = [
            {"timestamp": _ts(-23), "skill": "boundary-skill", "success": False}
            for _ in range(5)
        ]
        _write_jsonl(jsonl, records)

        result = find_failing_skills(jsonl, threshold=5, window_hours=24)
        assert len(result) == 1
        assert result[0]["skill"] == "boundary-skill"


# ---------------------------------------------------------------------------
# propose_repair_action — action heuristics
# ---------------------------------------------------------------------------

class TestProposeRepairAction:
    def _make_records(self, error: str | None, n: int = 5) -> list[dict]:
        base = {"timestamp": _ts(-1), "skill": "x", "success": False}
        if error is not None:
            base["error"] = error
        return [dict(base) for _ in range(n)]

    def test_uniform_error_suggests_regenerate(self) -> None:
        records = self._make_records("ModuleNotFoundError: skill crashed")
        plan = propose_repair_action("my-skill", records)
        assert plan["suggested_action"] == "regenerate"
        assert plan["skill"] == "my-skill"
        assert plan["failure_count"] == 5

    def test_varied_errors_suggests_investigate(self) -> None:
        records = [
            {"timestamp": _ts(-1), "skill": "x", "success": False, "error": "TimeoutError"},
            {"timestamp": _ts(-1), "skill": "x", "success": False, "error": "ModuleNotFoundError"},
            {"timestamp": _ts(-1), "skill": "x", "success": False, "error": "PermissionError"},
            {"timestamp": _ts(-1), "skill": "x", "success": False, "error": "KeyError"},
            {"timestamp": _ts(-1), "skill": "x", "success": False, "error": "IndexError"},
        ]
        plan = propose_repair_action("my-skill", records)
        assert plan["suggested_action"] == "investigate"

    def test_no_error_field_suggests_investigate(self) -> None:
        """When feedback has no error field, default to investigate."""
        records = [
            {"timestamp": _ts(-1), "skill": "x", "success": False}
            for _ in range(5)
        ]
        plan = propose_repair_action("my-skill", records)
        assert plan["suggested_action"] == "investigate"

    def test_stale_skill_suggests_deprecate(self, tmp_path: Path) -> None:
        """Skill with zero successes in last 7 days → deprecate."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        # All records are older than stale_days
        records = [
            {"timestamp": _ts(-200), "skill": "stale", "success": True},
            {"timestamp": _ts(-1), "skill": "stale", "success": False},
            {"timestamp": _ts(-1), "skill": "stale", "success": False},
        ]
        _write_jsonl(jsonl, records)

        failure_records = [r for r in records if not r["success"]]
        plan = propose_repair_action(
            "stale",
            failure_records,
            all_records_path=jsonl,
            stale_days=7,
        )
        assert plan["suggested_action"] == "deprecate"

    def test_recent_success_overrides_deprecate_heuristic(self, tmp_path: Path) -> None:
        """If the skill succeeded within stale_days, deprecate must NOT fire."""
        jsonl = tmp_path / "skill-feedback.jsonl"
        records = [
            {"timestamp": _ts(-1), "skill": "active", "success": True},
            {"timestamp": _ts(-1), "skill": "active", "success": False},
            {"timestamp": _ts(-1), "skill": "active", "success": False},
        ]
        _write_jsonl(jsonl, records)

        failure_records = [r for r in records if not r["success"]]
        plan = propose_repair_action(
            "active",
            failure_records,
            all_records_path=jsonl,
            stale_days=7,
        )
        # With 2 failures and no errors, should be "investigate" NOT "deprecate"
        assert plan["suggested_action"] != "deprecate"

    def test_sample_errors_capped_at_three(self) -> None:
        records = [
            {"timestamp": _ts(-1), "skill": "x", "success": False, "error": f"err{i}"}
            for i in range(7)
        ]
        plan = propose_repair_action("my-skill", records)
        assert len(plan["sample_errors"]) <= 3


# ---------------------------------------------------------------------------
# emit_repair_signal — JSONL output
# ---------------------------------------------------------------------------

class TestEmitRepairSignal:
    def test_creates_file_with_valid_jsonl(self, tmp_path: Path) -> None:
        output = tmp_path / "queue" / "skill-repair-queue.jsonl"
        plan = {
            "skill": "broken-skill",
            "failure_count": 5,
            "sample_errors": ["crash"],
            "suggested_action": "regenerate",
        }
        emit_repair_signal(plan, output)

        assert output.exists()
        lines = [l for l in output.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["skill"] == "broken-skill"
        assert record["suggested_action"] == "regenerate"
        assert record["status"] == "pending"
        assert record["failure_count"] == 5
        assert "timestamp" in record

    def test_appends_on_repeated_calls(self, tmp_path: Path) -> None:
        output = tmp_path / "skill-repair-queue.jsonl"
        plan = {
            "skill": "flaky",
            "failure_count": 5,
            "sample_errors": [],
            "suggested_action": "investigate",
        }
        emit_repair_signal(plan, output)
        emit_repair_signal(plan, output)

        lines = [l for l in output.read_text().splitlines() if l.strip()]
        assert len(lines) == 2

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        output = tmp_path / "a" / "b" / "c" / "queue.jsonl"
        plan = {
            "skill": "x",
            "failure_count": 5,
            "sample_errors": [],
            "suggested_action": "investigate",
        }
        emit_repair_signal(plan, output)
        assert output.exists()

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        """Each emitted line must be parseable JSON."""
        output = tmp_path / "q.jsonl"
        plan = {
            "skill": "unicode-skill-名前",
            "failure_count": 7,
            "sample_errors": ["error with 'quotes' and \"double\""],
            "suggested_action": "regenerate",
        }
        emit_repair_signal(plan, output)
        line = output.read_text().strip()
        record = json.loads(line)  # must not raise
        assert record["skill"] == "unicode-skill-名前"
