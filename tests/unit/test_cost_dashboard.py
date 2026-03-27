"""Unit tests for lib/cost_dashboard.py

Validates cost computation, session/daily/monthly reporting, efficiency
metrics, optimization suggestions, formatted output, and event recording.

Author: luum
"""

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from lib.cost_dashboard import (
    MODEL_PRICES,
    CostDashboard,
    SessionCostReport,
    record_cost_event,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_events(path: Path, events: list) -> None:
    """Write a list of event dicts as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def _make_event(
    model: str = "sonnet",
    tokens_in: int = 1000,
    tokens_out: int = 500,
    cost: float = 0.0105,
    action: str = "sdd-apply",
    success: bool = True,
    timestamp: str = "",
) -> dict:
    """Create a cost event dict for testing."""
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp": timestamp,
        "agent": action,
        "model": model,
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "estimated_cost_usd": cost,
        "success": success,
    }


# ---------------------------------------------------------------------------
# get_session_cost
# ---------------------------------------------------------------------------


class TestGetSessionCost:
    """Tests for CostDashboard.get_session_cost()."""

    def test_no_data_returns_zeroes(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_session_cost()
        assert result["total_usd"] == 0.0
        assert result["tokens_in"] == 0
        assert result["tokens_out"] == 0
        assert result["model_breakdown"] == {}
        assert result["call_count"] == 0

    def test_with_events_returns_correct_total(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [
            _make_event(model="sonnet", tokens_in=1000, tokens_out=500, cost=0.0105),
            _make_event(model="opus", tokens_in=2000, tokens_out=1000, cost=0.105),
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_session_cost()
        assert result["total_usd"] == pytest.approx(0.1155, abs=0.001)
        assert result["tokens_in"] == 3000
        assert result["tokens_out"] == 1500
        assert result["call_count"] == 2

    def test_budget_remaining_pct(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        # Write event with today's date
        events = [_make_event(cost=5.0)]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics), daily_budget=10.0)
        result = dash.get_session_cost()
        assert result["budget_remaining_pct"] == pytest.approx(50.0, abs=1.0)


# ---------------------------------------------------------------------------
# estimate_action_cost
# ---------------------------------------------------------------------------


class TestEstimateActionCost:
    """Tests for CostDashboard.estimate_action_cost()."""

    def test_opus_estimate(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        cost = dash.estimate_action_cost("opus", estimated_tokens=10000)
        # 6000 in * 15/1M + 4000 out * 75/1M = 0.09 + 0.30 = 0.39
        assert cost == pytest.approx(0.39, abs=0.01)

    def test_sonnet_estimate(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        cost = dash.estimate_action_cost("sonnet", estimated_tokens=10000)
        # 6000 * 3/1M + 4000 * 15/1M = 0.018 + 0.06 = 0.078
        assert cost == pytest.approx(0.078, abs=0.005)

    def test_haiku_estimate(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        cost = dash.estimate_action_cost("haiku", estimated_tokens=10000)
        # 6000 * 0.25/1M + 4000 * 1.25/1M = 0.0015 + 0.005 = 0.0065
        assert cost == pytest.approx(0.0065, abs=0.001)

    def test_unknown_model_uses_sonnet_prices(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        cost = dash.estimate_action_cost("unknown-model", estimated_tokens=10000)
        sonnet_cost = dash.estimate_action_cost("sonnet", estimated_tokens=10000)
        assert cost == sonnet_cost


# ---------------------------------------------------------------------------
# get_efficiency_metrics
# ---------------------------------------------------------------------------


class TestGetEfficiencyMetrics:
    """Tests for CostDashboard.get_efficiency_metrics()."""

    def test_empty_metrics_returns_zeroes(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_efficiency_metrics()
        assert result["useful_tokens_pct"] == 0.0
        assert result["wasted_tokens_pct"] == 0.0
        assert result["overhead_tokens_pct"] == 0.0

    def test_with_events_calculates_efficiency(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [
            _make_event(tokens_in=5000, tokens_out=3000, success=True),
            _make_event(tokens_in=2000, tokens_out=1000, success=False),
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_efficiency_metrics()
        assert result["useful_tokens_pct"] > 0
        assert result["wasted_tokens_pct"] > 0
        assert result["overhead_tokens_pct"] > 0
        total = (
            result["useful_tokens_pct"]
            + result["overhead_tokens_pct"]
            + result["wasted_tokens_pct"]
        )
        # Should be approximately 100% (rounding may cause slight deviation)
        assert total == pytest.approx(100.0, abs=5.0)


# ---------------------------------------------------------------------------
# get_optimization_suggestions
# ---------------------------------------------------------------------------


class TestGetOptimizationSuggestions:
    """Tests for CostDashboard.get_optimization_suggestions()."""

    def test_detects_opus_waste(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [
            _make_event(model="opus", tokens_in=10000, tokens_out=5000, cost=0.525)
            for _ in range(5)
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        suggestions = dash.get_optimization_suggestions()
        assert any("sonnet instead of opus" in s for s in suggestions)

    def test_detects_over_reads(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        # High output-to-input ratio
        events = [
            _make_event(tokens_in=100, tokens_out=5000, cost=0.01)
            for _ in range(5)
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        suggestions = dash.get_optimization_suggestions()
        assert any("output-to-input ratio" in s for s in suggestions)

    def test_no_suggestions_on_empty(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        suggestions = dash.get_optimization_suggestions()
        assert suggestions == []


# ---------------------------------------------------------------------------
# format_compact_status
# ---------------------------------------------------------------------------


class TestFormatCompactStatus:
    """Tests for CostDashboard.format_compact_status()."""

    def test_returns_one_line_string(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [_make_event(model="sonnet", cost=1.47)]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.format_compact_status()
        assert isinstance(result, str)
        assert "$" in result
        assert "tokens" in result
        assert "budget" in result

    def test_empty_data_still_returns_string(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.format_compact_status()
        assert isinstance(result, str)
        assert "$0.00" in result


# ---------------------------------------------------------------------------
# format_session_report
# ---------------------------------------------------------------------------


class TestFormatSessionReport:
    """Tests for CostDashboard.format_session_report()."""

    def test_has_required_sections(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [
            _make_event(model="sonnet", cost=0.50),
            _make_event(model="opus", cost=1.80),
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        report = dash.format_session_report()
        assert "SESSION COST REPORT" in report
        assert "Total Cost:" in report
        assert "Model Breakdown:" in report
        assert "Efficiency:" in report


# ---------------------------------------------------------------------------
# record_cost_event
# ---------------------------------------------------------------------------


class TestRecordCostEvent:
    """Tests for record_cost_event()."""

    def test_creates_jsonl_entry(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        record_cost_event(
            model="sonnet",
            tokens_in=1000,
            tokens_out=500,
            action="test-action",
            success=True,
            metrics_path=str(metrics),
        )
        assert metrics.exists()
        with open(metrics, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["model"] == "sonnet"
        assert event["input_tokens"] == 1000
        assert event["output_tokens"] == 500
        assert event["agent"] == "test-action"
        assert event["success"] is True
        assert "estimated_cost_usd" in event
        assert "timestamp" in event

    def test_appends_to_existing(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        record_cost_event("sonnet", 100, 50, "a1", metrics_path=str(metrics))
        record_cost_event("opus", 200, 100, "a2", metrics_path=str(metrics))
        with open(metrics, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_creates_parent_dirs(self, tmp_path):
        metrics = tmp_path / "deep" / "nested" / "cost.jsonl"
        record_cost_event("haiku", 50, 25, "test", metrics_path=str(metrics))
        assert metrics.exists()


# ---------------------------------------------------------------------------
# get_daily_cost
# ---------------------------------------------------------------------------


class TestGetDailyCost:
    """Tests for CostDashboard.get_daily_cost()."""

    def test_filters_by_date(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        today = date.today()
        events = [
            _make_event(cost=1.0, timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat()),
            _make_event(cost=2.0),  # today
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))

        result_today = dash.get_daily_cost(today)
        assert result_today["total_usd"] == pytest.approx(2.0, abs=0.01)

        result_old = dash.get_daily_cost(date(2025, 1, 1))
        assert result_old["total_usd"] == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# model_breakdown sums
# ---------------------------------------------------------------------------


class TestModelBreakdown:
    """Tests for model breakdown accuracy."""

    def test_model_breakdown_sums_correctly(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [
            _make_event(model="sonnet", cost=0.10),
            _make_event(model="sonnet", cost=0.20),
            _make_event(model="opus", cost=0.50),
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_session_cost()
        assert result["model_breakdown"]["sonnet"] == pytest.approx(0.30, abs=0.01)
        assert result["model_breakdown"]["opus"] == pytest.approx(0.50, abs=0.01)


# ---------------------------------------------------------------------------
# cost_per_task
# ---------------------------------------------------------------------------


class TestCostPerTask:
    """Tests for cost per task calculation via efficiency metrics."""

    def test_cost_per_file_changed(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [
            _make_event(cost=0.50),
            _make_event(cost=0.50),
        ]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_efficiency_metrics()
        # 2 events, total $1.00 -> cost_per_file_changed = $0.50
        assert result["cost_per_file_changed"] == pytest.approx(0.50, abs=0.01)


# ---------------------------------------------------------------------------
# monthly projection
# ---------------------------------------------------------------------------


class TestMonthlyProjection:
    """Tests for monthly cost projection."""

    def test_monthly_cost_returns_projection(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        events = [_make_event(cost=1.0)]
        _write_events(metrics, events)
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_monthly_cost()
        assert "projected_usd" in result
        assert result["projected_usd"] >= result["total_usd"]
        assert result["month"] is not None


# ---------------------------------------------------------------------------
# empty metrics graceful handling
# ---------------------------------------------------------------------------


class TestGracefulHandling:
    """Tests for graceful handling of missing/empty metrics."""

    def test_nonexistent_file(self, tmp_path):
        metrics = tmp_path / "does-not-exist.jsonl"
        dash = CostDashboard(metrics_path=str(metrics))
        # Should not raise
        assert dash.get_session_cost()["total_usd"] == 0.0
        assert dash.get_daily_cost()["total_usd"] == 0.0
        assert dash.get_monthly_cost()["total_usd"] == 0.0
        assert dash.get_efficiency_metrics()["useful_tokens_pct"] == 0.0
        assert dash.get_optimization_suggestions() == []

    def test_empty_file(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        metrics.write_text("")
        dash = CostDashboard(metrics_path=str(metrics))
        assert dash.get_session_cost()["total_usd"] == 0.0

    def test_malformed_json_lines_skipped(self, tmp_path):
        metrics = tmp_path / "cost-events.jsonl"
        metrics.write_text(
            '{"model":"sonnet","input_tokens":100,"output_tokens":50,"estimated_cost_usd":0.01,"timestamp":"2026-03-27T00:00:00+00:00"}\n'
            "not-json\n"
            '{"model":"opus","input_tokens":200,"output_tokens":100,"estimated_cost_usd":0.02,"timestamp":"2026-03-27T00:00:00+00:00"}\n'
        )
        dash = CostDashboard(metrics_path=str(metrics))
        result = dash.get_session_cost()
        # Should have 2 valid events, skipping the malformed line
        assert result["call_count"] == 2


# ---------------------------------------------------------------------------
# SessionCostReport dataclass
# ---------------------------------------------------------------------------


class TestSessionCostReport:
    """Tests for the SessionCostReport dataclass."""

    def test_dataclass_creation(self):
        report = SessionCostReport(
            session_id="test-123",
            start_time="2026-03-27T00:00:00Z",
            duration_minutes=45.0,
            total_cost_usd=2.34,
            tokens_in=45000,
            tokens_out=15000,
        )
        assert report.session_id == "test-123"
        assert report.total_cost_usd == 2.34
        assert report.model_breakdown == {}
        assert report.efficiency_score == 0.0
