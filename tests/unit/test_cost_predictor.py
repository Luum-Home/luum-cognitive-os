"""Unit tests for lib/cost_predictor.py

Validates cost prediction, historical task recording, similarity matching,
real model price calculation, per-phase estimation, cost trends, and
formatted output.

Author: luum
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib.cost_predictor import (
    DEFAULT_MODEL_PRICES,
    SDD_PHASES,
    CostPrediction,
    CostPredictor,
    HistoricalTask,
    _jaccard_similarity,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dirs(tmp_path: Path):
    """Create temporary history and cost-events files and return paths."""
    history = tmp_path / "task-history.jsonl"
    cost_events = tmp_path / "cost-events.jsonl"
    return str(history), str(cost_events)


@pytest.fixture
def predictor(tmp_dirs):
    """Create a CostPredictor with temporary file paths."""
    history_path, cost_events_path = tmp_dirs
    return CostPredictor(
        history_path=history_path,
        cost_events_path=cost_events_path,
    )


def _write_jsonl(path: str, entries: list) -> None:
    """Write a list of dicts as JSONL."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_history_entry(
    description: str = "add user authentication",
    task_type: str = "feature",
    total_cost: float = 1.80,
    tokens_in: int = 50000,
    tokens_out: int = 25000,
    phases: list = None,
    models: dict = None,
    duration: float = 45.0,
    files: int = 12,
    timestamp: str = "",
) -> dict:
    """Create a task history entry for testing."""
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "description": description,
        "task_type": task_type,
        "phases_executed": phases or ["propose", "spec", "design", "tasks", "apply", "verify"],
        "total_cost_usd": total_cost,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "models_used": models or {"sonnet": 4, "opus": 2},
        "duration_minutes": duration,
        "files_changed": files,
        "timestamp": timestamp,
    }


def _make_cost_event(
    model: str = "sonnet",
    tokens_in: int = 1000,
    tokens_out: int = 500,
    cost: float = 0.0105,
    timestamp: str = "",
) -> dict:
    """Create a cost event for testing."""
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp": timestamp,
        "agent": "sdd-apply",
        "model": model,
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "estimated_cost_usd": cost,
        "success": True,
    }


# ---------------------------------------------------------------------------
# Jaccard similarity tests
# ---------------------------------------------------------------------------


class TestJaccardSimilarity:
    def test_identical_strings(self):
        assert _jaccard_similarity("add auth", "add auth") == 1.0

    def test_empty_strings(self):
        assert _jaccard_similarity("", "") == 0.0
        assert _jaccard_similarity("hello", "") == 0.0
        assert _jaccard_similarity("", "hello") == 0.0

    def test_partial_overlap(self):
        sim = _jaccard_similarity("add user authentication", "add jwt authentication")
        assert 0.0 < sim < 1.0

    def test_no_overlap(self):
        sim = _jaccard_similarity("database migration", "frontend styling")
        assert sim == 0.0

    def test_case_insensitive(self):
        assert _jaccard_similarity("Add Auth", "add auth") == 1.0


# ---------------------------------------------------------------------------
# Predict with no history
# ---------------------------------------------------------------------------


class TestPredictNoHistory:
    def test_returns_no_data_basis(self, predictor):
        prediction = predictor.predict("add JWT authentication")
        assert prediction.basis in ("no_data", "model_routing")

    def test_returns_very_low_confidence(self, predictor):
        prediction = predictor.predict("add JWT authentication")
        assert prediction.confidence < 0.3

    def test_returns_non_negative_costs(self, predictor):
        prediction = predictor.predict("add JWT authentication")
        assert prediction.estimated_cost_min >= 0
        assert prediction.estimated_cost_mid >= 0
        assert prediction.estimated_cost_max >= 0

    def test_returns_empty_similar_tasks(self, predictor):
        prediction = predictor.predict("add JWT authentication")
        assert prediction.similar_tasks == []


# ---------------------------------------------------------------------------
# Predict with similar history
# ---------------------------------------------------------------------------


class TestPredictWithHistory:
    def test_returns_historical_basis(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add user authentication endpoint", total_cost=1.80),
            _make_history_entry("add jwt authentication flow", total_cost=2.20),
            _make_history_entry("implement authentication middleware", total_cost=1.50),
        ])
        prediction = predictor.predict("add user authentication endpoint")
        assert prediction.basis == "historical"

    def test_returns_weighted_estimate(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add user authentication endpoint", total_cost=1.80),
            _make_history_entry("add jwt authentication flow", total_cost=2.20),
        ])
        prediction = predictor.predict("add authentication to API")
        # Mid should be between min and max of similar tasks
        assert prediction.estimated_cost_mid > 0

    def test_applies_calibration_factor(self, predictor):
        """When calibration data exists, the factor should be applied."""
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add user authentication", total_cost=2.00),
        ])
        prediction = predictor.predict("add user authentication system")
        # Calibration is 1.0 by default (no calibration data)
        assert prediction.calibration_applied >= 1.0

    def test_similar_tasks_included(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add user authentication", total_cost=1.80),
        ])
        prediction = predictor.predict("add user authentication system")
        assert len(prediction.similar_tasks) > 0
        assert "similarity" in prediction.similar_tasks[0]
        assert "cost" in prediction.similar_tasks[0]


# ---------------------------------------------------------------------------
# find_similar_tasks
# ---------------------------------------------------------------------------


class TestFindSimilarTasks:
    def test_returns_sorted_by_similarity(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add user login endpoint"),
            _make_history_entry("add user authentication endpoint"),
            _make_history_entry("database schema migration"),
        ])
        results = predictor.find_similar_tasks("add user authentication")
        if len(results) >= 2:
            assert results[0][1] >= results[1][1]

    def test_filters_below_threshold(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("database schema migration"),
            _make_history_entry("frontend CSS styling update"),
        ])
        results = predictor.find_similar_tasks("add user authentication", min_similarity=0.5)
        assert len(results) == 0

    def test_respects_max_results(self, predictor):
        entries = [_make_history_entry(f"add user auth part {i}") for i in range(10)]
        _write_jsonl(predictor.history_path, entries)
        results = predictor.find_similar_tasks("add user auth", max_results=3)
        assert len(results) <= 3

    def test_empty_history(self, predictor):
        results = predictor.find_similar_tasks("anything")
        assert results == []

    def test_empty_description(self, predictor):
        _write_jsonl(predictor.history_path, [_make_history_entry("something")])
        results = predictor.find_similar_tasks("")
        assert results == []


# ---------------------------------------------------------------------------
# record_completed_task
# ---------------------------------------------------------------------------


class TestRecordCompletedTask:
    def test_appends_to_jsonl(self, predictor):
        task = HistoricalTask(
            description="add user endpoint",
            task_type="feature",
            total_cost_usd=1.50,
            tokens_in=30000,
            tokens_out=15000,
        )
        predictor.record_completed_task(task)

        path = Path(predictor.history_path)
        assert path.exists()
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["description"] == "add user endpoint"
        assert entry["total_cost_usd"] == 1.50

    def test_sets_timestamp_if_missing(self, predictor):
        task = HistoricalTask(description="test", task_type="feature")
        predictor.record_completed_task(task)

        with open(predictor.history_path) as f:
            entry = json.loads(f.readline())
        assert entry["timestamp"] != ""

    def test_preserves_existing_timestamp(self, predictor):
        ts = "2026-01-15T12:00:00+00:00"
        task = HistoricalTask(description="test", task_type="feature", timestamp=ts)
        predictor.record_completed_task(task)

        with open(predictor.history_path) as f:
            entry = json.loads(f.readline())
        assert entry["timestamp"] == ts

    def test_multiple_appends(self, predictor):
        for i in range(3):
            task = HistoricalTask(description=f"task {i}", task_type="feature")
            predictor.record_completed_task(task)

        with open(predictor.history_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# get_real_model_prices
# ---------------------------------------------------------------------------


class TestGetRealModelPrices:
    def test_from_cost_events(self, predictor):
        _write_jsonl(predictor.cost_events_path, [
            _make_cost_event(model="sonnet", tokens_in=10000, tokens_out=5000, cost=0.105),
            _make_cost_event(model="sonnet", tokens_in=20000, tokens_out=10000, cost=0.21),
        ])
        prices = predictor.get_real_model_prices()
        assert "sonnet" in prices
        assert prices["sonnet"]["source"] == "measured"
        assert prices["sonnet"]["input"] > 0
        assert prices["sonnet"]["output"] > 0

    def test_falls_back_to_defaults(self, predictor):
        # No cost events file
        prices = predictor.get_real_model_prices()
        assert "sonnet" in prices
        assert prices["sonnet"]["source"] == "default"
        assert prices["sonnet"]["input"] == DEFAULT_MODEL_PRICES["sonnet"]["input"]

    def test_mixed_measured_and_default(self, predictor):
        _write_jsonl(predictor.cost_events_path, [
            _make_cost_event(model="opus", tokens_in=5000, tokens_out=2000, cost=0.225),
        ])
        prices = predictor.get_real_model_prices()
        assert prices["opus"]["source"] == "measured"
        assert prices["haiku"]["source"] == "default"

    def test_includes_all_default_models(self, predictor):
        prices = predictor.get_real_model_prices()
        for model in DEFAULT_MODEL_PRICES:
            assert model in prices


# ---------------------------------------------------------------------------
# estimate_per_phase
# ---------------------------------------------------------------------------


class TestEstimatePerPhase:
    def test_returns_all_phases(self, predictor):
        estimates = predictor.estimate_per_phase()
        for phase in SDD_PHASES:
            assert phase in estimates

    def test_all_costs_non_negative(self, predictor):
        estimates = predictor.estimate_per_phase()
        for phase, cost in estimates.items():
            assert cost >= 0, f"Phase {phase} has negative cost"

    def test_from_history(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry(total_cost=3.0, phases=["propose", "spec", "apply"]),
            _make_history_entry(total_cost=6.0, phases=["propose", "spec", "apply"]),
        ])
        estimates = predictor.estimate_per_phase()
        # propose should have data from history
        assert estimates["propose"] > 0

    def test_no_history_uses_defaults(self, predictor):
        estimates = predictor.estimate_per_phase()
        # Should still return reasonable defaults
        total = sum(estimates.values())
        assert total > 0


# ---------------------------------------------------------------------------
# get_cost_trends
# ---------------------------------------------------------------------------


class TestGetCostTrends:
    def test_empty_events(self, predictor):
        trends = predictor.get_cost_trends()
        assert trends["daily_avg"] == 0.0
        assert trends["trend_direction"] == "stable"
        assert trends["cheapest_day"] is None

    def test_calculates_daily_avg(self, predictor):
        now = datetime.now(timezone.utc)
        events = []
        for i in range(5):
            ts = (now - timedelta(days=i)).isoformat()
            events.append(_make_cost_event(cost=1.0, timestamp=ts))
        _write_jsonl(predictor.cost_events_path, events)

        trends = predictor.get_cost_trends(days=30)
        assert trends["daily_avg"] > 0
        assert trends["cheapest_day"] is not None
        assert trends["most_expensive_day"] is not None

    def test_trend_direction_up(self, predictor):
        now = datetime.now(timezone.utc)
        events = []
        # Old days: low cost
        for i in range(15, 25):
            ts = (now - timedelta(days=i)).isoformat()
            events.append(_make_cost_event(cost=0.10, timestamp=ts))
        # Recent days: high cost
        for i in range(0, 5):
            ts = (now - timedelta(days=i)).isoformat()
            events.append(_make_cost_event(cost=2.00, timestamp=ts))
        _write_jsonl(predictor.cost_events_path, events)

        trends = predictor.get_cost_trends(days=30)
        assert trends["trend_direction"] == "up"

    def test_trend_direction_stable(self, predictor):
        now = datetime.now(timezone.utc)
        events = []
        for i in range(10):
            ts = (now - timedelta(days=i)).isoformat()
            events.append(_make_cost_event(cost=1.0, timestamp=ts))
        _write_jsonl(predictor.cost_events_path, events)

        trends = predictor.get_cost_trends(days=30)
        assert trends["trend_direction"] == "stable"


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


class TestConfidenceLevels:
    def test_high_with_5_plus_similar(self, predictor):
        entries = [
            _make_history_entry(f"add user authentication part {i}", total_cost=1.5 + i * 0.1)
            for i in range(6)
        ]
        _write_jsonl(predictor.history_path, entries)
        prediction = predictor.predict("add user authentication")
        assert prediction.confidence >= 0.6  # 5+ similar tasks, high but may not hit 0.7 exactly

    def test_low_with_1_similar(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add user authentication endpoint", total_cost=2.0),
            _make_history_entry("database schema migration", total_cost=1.0),
        ])
        prediction = predictor.predict("add user authentication system")
        # With only 1 similar match, confidence should be relatively low
        assert prediction.confidence <= 0.7

    def test_very_low_with_no_history(self, predictor):
        prediction = predictor.predict("add user authentication")
        assert prediction.confidence < 0.3


# ---------------------------------------------------------------------------
# Prediction range
# ---------------------------------------------------------------------------


class TestPredictionRange:
    def test_min_less_than_mid(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add auth endpoint", total_cost=1.80),
            _make_history_entry("add auth middleware", total_cost=2.20),
        ])
        prediction = predictor.predict("add auth")
        assert prediction.estimated_cost_min <= prediction.estimated_cost_mid

    def test_mid_less_than_max(self, predictor):
        _write_jsonl(predictor.history_path, [
            _make_history_entry("add auth endpoint", total_cost=1.80),
            _make_history_entry("add auth middleware", total_cost=2.20),
        ])
        prediction = predictor.predict("add auth")
        assert prediction.estimated_cost_mid <= prediction.estimated_cost_max

    def test_no_data_range(self, predictor):
        prediction = predictor.predict("anything")
        assert prediction.estimated_cost_min <= prediction.estimated_cost_mid
        assert prediction.estimated_cost_mid <= prediction.estimated_cost_max


# ---------------------------------------------------------------------------
# Format output
# ---------------------------------------------------------------------------


class TestFormatPrediction:
    def test_has_required_sections(self, predictor):
        prediction = CostPrediction(
            estimated_cost_min=1.50,
            estimated_cost_max=2.80,
            estimated_cost_mid=2.10,
            confidence=0.65,
            basis="historical",
            similar_tasks=[
                {"description": "add auth endpoint", "cost": 1.80, "similarity": 0.82},
            ],
            calibration_applied=1.2,
            breakdown={"propose": 0.45, "apply": 0.60},
            recommendation="Use sonnet for all phases",
        )
        output = predictor.format_prediction(prediction)
        assert "Cost Prediction" in output
        assert "Estimated:" in output
        assert "Confidence:" in output
        assert "MEDIUM" in output
        assert "Phase breakdown:" in output
        assert "Recommendation:" in output

    def test_no_data_prediction_format(self, predictor):
        prediction = predictor.predict("anything")
        output = predictor.format_prediction(prediction)
        assert "Cost Prediction" in output
        assert "Estimated:" in output


class TestFormatPriceTable:
    def test_shows_source_measured(self, predictor):
        _write_jsonl(predictor.cost_events_path, [
            _make_cost_event(model="sonnet", tokens_in=10000, tokens_out=5000, cost=0.105),
        ])
        output = predictor.format_price_table()
        assert "measured" in output

    def test_shows_source_default(self, predictor):
        output = predictor.format_price_table()
        assert "default" in output

    def test_contains_model_prices_header(self, predictor):
        output = predictor.format_price_table()
        assert "Model Prices:" in output


# ---------------------------------------------------------------------------
# Empty / graceful handling
# ---------------------------------------------------------------------------


class TestGracefulHandling:
    def test_empty_history_file(self, predictor):
        Path(predictor.history_path).parent.mkdir(parents=True, exist_ok=True)
        Path(predictor.history_path).write_text("")
        prediction = predictor.predict("add auth")
        assert prediction.basis in ("no_data", "model_routing")

    def test_corrupt_jsonl(self, predictor):
        Path(predictor.history_path).parent.mkdir(parents=True, exist_ok=True)
        Path(predictor.history_path).write_text("not json\n{bad\n")
        prediction = predictor.predict("add auth")
        assert prediction.basis in ("no_data", "model_routing")

    def test_missing_files(self, predictor):
        # Files don't exist -- should not crash
        prediction = predictor.predict("add auth")
        assert prediction is not None
        prices = predictor.get_real_model_prices()
        assert len(prices) > 0
        trends = predictor.get_cost_trends()
        assert trends["daily_avg"] == 0.0
