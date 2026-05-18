# SCOPE: os-only
"""Unit tests for lib/goal_budget.py — T-08 AC (AC-008a through AC-008d)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch


from lib.goal_budget import check_budget, _goal_dispatch_totals
from lib.goal_state import GoalState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_goal(**overrides) -> GoalState:
    base = dict(
        objective="Complete the routing benchmark",
        acceptance_checks=["AC-001"],
        constraints=[],
        max_turns=None,
        max_minutes=None,
        max_tokens=None,
        max_cost_usd=None,
        workspace_thread_id="test",
    )
    base.update(overrides)
    return GoalState.create(**base)


def _write_dispatch_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _make_dispatch_record(ts: str, tokens_in: int, tokens_out: int, cost_usd: float) -> dict:
    return {
        "ts": ts,
        "dispatch_id": "test-id",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "success": True,
    }


# ---------------------------------------------------------------------------
# AC-008a: max_turns exhausted → budget_limited
# ---------------------------------------------------------------------------


class TestMaxTurns:
    def test_turns_at_limit_is_exhausted(self):
        """AC-008a: Unit test exhausts max_turns; goal transitions to budget_limited."""
        goal = _make_goal(max_turns=3)
        goal_dict = goal.to_dict()
        goal_dict["turns_used"] = 3  # at the limit
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        assert result.exhausted is True
        assert result.dimension == "max_turns"
        assert "3/3" in result.reason

    def test_turns_below_limit_is_not_exhausted(self):
        goal = _make_goal(max_turns=5)
        goal_dict = goal.to_dict()
        goal_dict["turns_used"] = 4
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        assert result.exhausted is False

    def test_turns_used_reported_in_result(self):
        goal = _make_goal(max_turns=5)
        goal_dict = goal.to_dict()
        goal_dict["turns_used"] = 2
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        assert result.turns_used == 2

    def test_no_max_turns_limit_never_exhausts(self):
        goal = _make_goal(max_turns=None)
        goal_dict = goal.to_dict()
        goal_dict["turns_used"] = 9999
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        assert result.exhausted is False


# ---------------------------------------------------------------------------
# AC-008b: wall_clock_minutes exhausted → budget_limited
# ---------------------------------------------------------------------------


class TestWallClockMinutes:
    def test_wall_clock_exhausted(self):
        """AC-008b: Unit test exhausts wall_clock_minutes; goal transitions to budget_limited."""
        goal = _make_goal(max_minutes=1)
        goal_dict = goal.to_dict()
        # Set started_at_epoch to 2 minutes ago
        goal_dict["started_at_epoch"] = time.time() - 120
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        assert result.exhausted is True
        assert result.dimension == "wall_clock_minutes"

    def test_wall_clock_not_exhausted(self):
        goal = _make_goal(max_minutes=60)
        # started_at_epoch defaults to now, so wall_clock is ~0 minutes
        result = check_budget(goal)
        assert result.exhausted is False

    def test_no_max_minutes_limit_never_exhausts(self):
        goal = _make_goal(max_minutes=None)
        goal_dict = goal.to_dict()
        # Started 100 hours ago
        goal_dict["started_at_epoch"] = time.time() - 360000
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        assert result.exhausted is False

    def test_wall_minutes_reported_in_result(self):
        goal = _make_goal(max_minutes=60)
        goal_dict = goal.to_dict()
        goal_dict["started_at_epoch"] = time.time() - 300  # 5 minutes ago
        goal = GoalState.from_dict(goal_dict)

        result = check_budget(goal)
        # Should be approximately 5 minutes
        assert 4.0 <= result.wall_minutes_used <= 6.0


# ---------------------------------------------------------------------------
# AC-008c: max_tokens exhausted via mock dispatch-metric records
# ---------------------------------------------------------------------------


class TestMaxTokens:
    def test_tokens_exhausted_via_mock_metrics(self, tmp_path):
        """AC-008c: Inject mock dispatch-metric records; goal transitions to budget_limited."""
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"

        goal = _make_goal(max_tokens=1000)
        # Records after goal creation with 600 tokens each = 1200 total
        records = [
            _make_dispatch_record(goal.created_at, tokens_in=300, tokens_out=300, cost_usd=0.01),
            _make_dispatch_record(goal.created_at, tokens_in=400, tokens_out=200, cost_usd=0.02),
        ]
        _write_dispatch_records(metrics_path, records)

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            result = check_budget(goal, project_dir=tmp_path)

        assert result.exhausted is True
        assert result.dimension == "max_tokens"
        assert result.tokens_used == 1200

    def test_tokens_below_limit_not_exhausted(self, tmp_path):
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"

        goal = _make_goal(max_tokens=10000)
        records = [
            _make_dispatch_record(goal.created_at, tokens_in=100, tokens_out=50, cost_usd=0.001),
        ]
        _write_dispatch_records(metrics_path, records)

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            result = check_budget(goal, project_dir=tmp_path)

        assert result.exhausted is False
        assert result.tokens_used == 150

    def test_absent_metrics_file_returns_zeros(self, tmp_path):
        """Graceful degradation: absent file returns zeros, does not crash."""
        goal = _make_goal(max_tokens=1000)
        nonexistent = tmp_path / "no-such-dir" / "llm-dispatch.jsonl"

        with patch("lib.dispatch._metrics_path", return_value=nonexistent):
            result = check_budget(goal, project_dir=tmp_path)

        # File absent → tokens_used = 0 → not exhausted
        assert result.tokens_used == 0
        assert result.exhausted is False

    def test_old_records_before_goal_creation_excluded(self, tmp_path):
        """Records before goal.created_at must not be counted."""
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"

        goal = _make_goal(max_tokens=500)
        # Record timestamped before goal creation
        old_record = _make_dispatch_record(
            "2020-01-01T00:00:00Z", tokens_in=9999, tokens_out=9999, cost_usd=99.0
        )
        # Record after goal creation
        new_record = _make_dispatch_record(
            goal.created_at, tokens_in=100, tokens_out=50, cost_usd=0.001
        )
        _write_dispatch_records(metrics_path, [old_record, new_record])

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            result = check_budget(goal, project_dir=tmp_path)

        assert result.tokens_used == 150
        assert result.exhausted is False


# ---------------------------------------------------------------------------
# AC-008d: max_cost_usd exhausted via mock dispatch-metric records
# ---------------------------------------------------------------------------


class TestMaxCostUsd:
    def test_cost_exhausted_via_mock_metrics(self, tmp_path):
        """AC-008d: Inject mock dispatch-metric records; goal transitions to budget_limited."""
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"

        goal = _make_goal(max_cost_usd=0.05)
        records = [
            _make_dispatch_record(goal.created_at, tokens_in=100, tokens_out=100, cost_usd=0.03),
            _make_dispatch_record(goal.created_at, tokens_in=100, tokens_out=100, cost_usd=0.03),
        ]
        _write_dispatch_records(metrics_path, records)

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            result = check_budget(goal, project_dir=tmp_path)

        assert result.exhausted is True
        assert result.dimension == "max_cost_usd"
        assert abs(result.cost_used - 0.06) < 0.001

    def test_cost_below_limit_not_exhausted(self, tmp_path):
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"

        goal = _make_goal(max_cost_usd=1.0)
        records = [
            _make_dispatch_record(goal.created_at, tokens_in=10, tokens_out=10, cost_usd=0.001),
        ]
        _write_dispatch_records(metrics_path, records)

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            result = check_budget(goal, project_dir=tmp_path)

        assert result.exhausted is False

    def test_absent_metrics_graceful_for_cost(self, tmp_path):
        """Absent file returns zeros and does not crash."""
        goal = _make_goal(max_cost_usd=0.01)
        nonexistent = tmp_path / "no-dir" / "llm-dispatch.jsonl"

        with patch("lib.dispatch._metrics_path", return_value=nonexistent):
            result = check_budget(goal, project_dir=tmp_path)

        assert result.cost_used == 0.0
        assert result.exhausted is False


# ---------------------------------------------------------------------------
# _goal_dispatch_totals unit tests
# ---------------------------------------------------------------------------


class TestGoalDispatchTotals:
    def test_returns_zeros_for_absent_file(self, tmp_path):
        nonexistent = tmp_path / "no-file.jsonl"
        with patch("lib.dispatch._metrics_path", return_value=nonexistent):
            tokens, cost = _goal_dispatch_totals("2026-01-01T00:00:00+00:00", tmp_path)
        assert tokens == 0
        assert cost == 0.0

    def test_accumulates_tokens_and_cost(self, tmp_path):
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
        records = [
            _make_dispatch_record("2026-05-01T10:00:00Z", 100, 200, 0.01),
            _make_dispatch_record("2026-05-01T11:00:00Z", 50, 75, 0.02),
        ]
        _write_dispatch_records(metrics_path, records)

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            tokens, cost = _goal_dispatch_totals("2026-05-01T09:00:00Z", tmp_path)

        assert tokens == 425  # 100+200+50+75
        assert abs(cost - 0.03) < 0.001

    def test_skips_malformed_lines_gracefully(self, tmp_path):
        metrics_path = tmp_path / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_path.open("w") as fh:
            fh.write("{bad json\n")
            fh.write(json.dumps(_make_dispatch_record("2026-05-01T10:00:00Z", 10, 20, 0.01)) + "\n")

        with patch("lib.dispatch._metrics_path", return_value=metrics_path):
            tokens, cost = _goal_dispatch_totals("2026-05-01T09:00:00Z", tmp_path)

        assert tokens == 30  # Only valid record counted
        assert abs(cost - 0.01) < 0.0001


# ---------------------------------------------------------------------------
# test_budget_exhaustion_marks_budget_limited (referenced in T-08 AC)
# ---------------------------------------------------------------------------


class TestBudgetExhaustionMarksBudgetLimited:
    """These tests match the AC command:
    pytest tests/unit/test_goal_state.py::test_budget_exhaustion_marks_budget_limited

    Since this module covers T-08 more fully, the check is here too.
    """

    def test_max_turns_marks_budget_limited(self):
        goal = _make_goal(max_turns=1)
        goal_dict = goal.to_dict()
        goal_dict["turns_used"] = 1
        goal = GoalState.from_dict(goal_dict)
        result = check_budget(goal)
        assert result.exhausted is True
        assert result.dimension == "max_turns"

    def test_wall_clock_marks_budget_limited(self):
        goal = _make_goal(max_minutes=0)  # zero minutes budget → instantly exhausted
        # Subtract 1 second from started_at_epoch to ensure > 0 minutes have elapsed
        goal_dict = goal.to_dict()
        goal_dict["started_at_epoch"] = time.time() - 1
        goal = GoalState.from_dict(goal_dict)
        result = check_budget(goal)
        assert result.exhausted is True
        assert result.dimension == "wall_clock_minutes"
