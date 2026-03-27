"""Unit tests for lib/estimation_calibrator.py

Validates estimate recording, actual recording, accuracy computation,
calibration factor calculation, calibration application, and reporting.

Python 3.9+ compatible.
"""

import json
from pathlib import Path

import pytest

from lib.estimation_calibrator import (
    VALID_COMPLEXITIES,
    _compute_accuracy,
    _compute_files_accuracy,
    apply_calibration,
    format_calibration_report,
    get_calibration_factor,
    record_actual,
    record_estimate,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def metrics_dir(tmp_path: Path) -> str:
    """Create a temporary metrics directory and return its path as string."""
    d = tmp_path / "metrics"
    d.mkdir()
    return str(d)


def _read_jsonl(metrics_dir: str) -> list:
    """Read all lines from the estimations JSONL file."""
    path = Path(metrics_dir) / "estimations.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _write_estimate_and_actual(
    metrics_dir: str,
    task_id: str,
    agent: str,
    est_min: float,
    est_max: float,
    est_files: int,
    actual_hours: float,
    actual_files: int,
    retries: int = 0,
    bugs: int = 0,
) -> None:
    """Helper: write an estimate + actual pair."""
    record_estimate(
        task_id=task_id,
        agent=agent,
        estimates={
            "complexity": "medium",
            "effort_hours_min": est_min,
            "effort_hours_max": est_max,
            "risk": "medium",
            "files_estimate": est_files,
        },
        metrics_dir=metrics_dir,
    )
    record_actual(
        task_id=task_id,
        actuals={
            "actual_hours": actual_hours,
            "actual_files": actual_files,
            "retries": retries,
            "bugs_found": bugs,
        },
        metrics_dir=metrics_dir,
    )


# ---------------------------------------------------------------------------
# Test: record_estimate
# ---------------------------------------------------------------------------


class TestRecordEstimate:
    def test_creates_jsonl_entry(self, metrics_dir: str) -> None:
        """record_estimate creates a JSONL entry with correct fields."""
        record_estimate(
            task_id="task-1",
            agent="test-agent",
            estimates={
                "complexity": "medium",
                "effort_hours_min": 2.0,
                "effort_hours_max": 5.0,
                "risk": "high",
                "files_estimate": 10,
            },
            metrics_dir=metrics_dir,
        )
        entries = _read_jsonl(metrics_dir)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["type"] == "estimate"
        assert entry["task_id"] == "task-1"
        assert entry["agent"] == "test-agent"
        assert entry["complexity"] == "medium"
        assert entry["effort_hours_min"] == 2.0
        assert entry["effort_hours_max"] == 5.0
        assert entry["risk"] == "high"
        assert entry["files_estimate"] == 10
        assert "timestamp" in entry

    def test_invalid_complexity_defaults_to_medium(self, metrics_dir: str) -> None:
        """Invalid complexity values are normalized to 'medium'."""
        record_estimate(
            task_id="task-2",
            agent="test-agent",
            estimates={"complexity": "enormous"},
            metrics_dir=metrics_dir,
        )
        entries = _read_jsonl(metrics_dir)
        assert entries[0]["complexity"] == "medium"

    def test_missing_fields_default_to_zero(self, metrics_dir: str) -> None:
        """Missing estimate fields default to zero/medium."""
        record_estimate(
            task_id="task-3",
            agent="test-agent",
            estimates={},
            metrics_dir=metrics_dir,
        )
        entry = _read_jsonl(metrics_dir)[0]
        assert entry["effort_hours_min"] == 0.0
        assert entry["effort_hours_max"] == 0.0
        assert entry["files_estimate"] == 0
        assert entry["risk"] == "medium"

    def test_valid_complexities_accepted(self, metrics_dir: str) -> None:
        """All valid complexity levels are accepted."""
        for complexity in VALID_COMPLEXITIES:
            record_estimate(
                task_id=f"task-{complexity}",
                agent="test-agent",
                estimates={"complexity": complexity},
                metrics_dir=metrics_dir,
            )
        entries = _read_jsonl(metrics_dir)
        complexities = [e["complexity"] for e in entries]
        assert complexities == list(VALID_COMPLEXITIES)


# ---------------------------------------------------------------------------
# Test: record_actual
# ---------------------------------------------------------------------------


class TestRecordActual:
    def test_matches_task_id(self, metrics_dir: str) -> None:
        """record_actual correctly matches an existing estimate by task_id."""
        record_estimate(
            task_id="task-match",
            agent="agent-a",
            estimates={"effort_hours_min": 2, "effort_hours_max": 4, "files_estimate": 5},
            metrics_dir=metrics_dir,
        )
        record_actual(
            task_id="task-match",
            actuals={"actual_hours": 3, "actual_files": 5, "retries": 0, "bugs_found": 0},
            metrics_dir=metrics_dir,
        )
        entries = _read_jsonl(metrics_dir)
        actual = [e for e in entries if e["type"] == "actual"][0]
        assert actual["task_id"] == "task-match"
        assert actual["agent"] == "agent-a"
        assert actual["had_estimate"] is True

    def test_no_matching_estimate(self, metrics_dir: str) -> None:
        """record_actual handles missing estimate gracefully."""
        record_actual(
            task_id="task-orphan",
            actuals={"actual_hours": 3, "actual_files": 5, "retries": 1, "bugs_found": 2},
            metrics_dir=metrics_dir,
        )
        entries = _read_jsonl(metrics_dir)
        actual = entries[0]
        assert actual["had_estimate"] is False
        assert actual["agent"] == "unknown"


# ---------------------------------------------------------------------------
# Test: accuracy computation
# ---------------------------------------------------------------------------


class TestAccuracyComputation:
    def test_perfect_accuracy(self) -> None:
        """Actual within range returns 1.0."""
        assert _compute_accuracy(2.0, 6.0, 4.0) == 1.0

    def test_exact_min_boundary(self) -> None:
        """Actual at min boundary returns 1.0."""
        assert _compute_accuracy(3.0, 7.0, 3.0) == 1.0

    def test_exact_max_boundary(self) -> None:
        """Actual at max boundary returns 1.0."""
        assert _compute_accuracy(3.0, 7.0, 7.0) == 1.0

    def test_underestimation(self) -> None:
        """Actual exceeds max: accuracy < 1.0 (underestimation)."""
        acc = _compute_accuracy(2.0, 4.0, 9.0)
        # midpoint=3, actual=9, ratio=3/9=0.333
        assert abs(acc - (3.0 / 9.0)) < 0.001

    def test_overestimation(self) -> None:
        """Actual below min: accuracy > 1.0 (overestimation)."""
        acc = _compute_accuracy(10.0, 20.0, 5.0)
        # midpoint=15, actual=5, ratio=15/5=3.0
        assert abs(acc - 3.0) < 0.001

    def test_zero_actual_returns_zero(self) -> None:
        """Zero actual hours returns 0.0 (cannot compute)."""
        assert _compute_accuracy(2.0, 4.0, 0.0) == 0.0

    def test_zero_estimate_returns_zero(self) -> None:
        """Zero estimated hours returns 0.0."""
        assert _compute_accuracy(0.0, 0.0, 5.0) == 0.0

    def test_files_accuracy_perfect(self) -> None:
        """Estimated files equals actual files returns 1.0."""
        assert _compute_files_accuracy(5, 5) == 1.0

    def test_files_accuracy_underestimate(self) -> None:
        """Estimated 5, actual 15 = 0.333 (underestimation)."""
        acc = _compute_files_accuracy(5, 15)
        assert abs(acc - (5.0 / 15.0)) < 0.001

    def test_files_accuracy_overestimate(self) -> None:
        """Estimated 20, actual 5 = 4.0 (overestimation)."""
        acc = _compute_files_accuracy(20, 5)
        assert abs(acc - 4.0) < 0.001

    def test_files_accuracy_zero_actual(self) -> None:
        """Zero actual files with nonzero estimate returns 0.0."""
        assert _compute_files_accuracy(5, 0) == 0.0

    def test_files_accuracy_both_zero(self) -> None:
        """Both zero returns 1.0 (trivially correct)."""
        assert _compute_files_accuracy(0, 0) == 1.0

    def test_files_accuracy_zero_estimate_nonzero_actual(self) -> None:
        """Estimated 0 but actual > 0 returns 0.0 (total miss)."""
        assert _compute_files_accuracy(0, 10) == 0.0


# ---------------------------------------------------------------------------
# Test: calibration factor
# ---------------------------------------------------------------------------


class TestCalibrationFactor:
    def test_no_history_returns_neutral(self, metrics_dir: str) -> None:
        """No historical data returns neutral factors (1.0)."""
        factors = get_calibration_factor("agent-x", metrics_dir)
        assert factors["complexity_bias"] == 1.0
        assert factors["effort_bias"] == 1.0
        assert factors["files_bias"] == 1.0
        assert factors["risk_bias"] == 1.0
        assert factors["sample_size"] == 0
        assert factors["confidence"] == "none"

    def test_calibration_from_history(self, metrics_dir: str) -> None:
        """Calibration factors are computed from historical data."""
        # Create 5 entries where agent consistently underestimates files
        for i in range(5):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"task-{i}",
                agent="under-estimator",
                est_min=1,
                est_max=3,
                est_files=5,
                actual_hours=2,
                actual_files=10,  # Always double the estimate
            )
        factors = get_calibration_factor("under-estimator", metrics_dir)
        assert factors["files_bias"] > 1.0  # Should inflate file estimates
        assert factors["sample_size"] == 5
        assert factors["confidence"] == "low"

    def test_multiple_agents_independent(self, metrics_dir: str) -> None:
        """Different agents have independent calibration factors."""
        for i in range(3):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"a-{i}",
                agent="agent-accurate",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=3,
                actual_files=5,
            )
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"b-{i}",
                agent="agent-inaccurate",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=10,
                actual_files=20,
            )
        f_accurate = get_calibration_factor("agent-accurate", metrics_dir)
        f_inaccurate = get_calibration_factor("agent-inaccurate", metrics_dir)
        # Inaccurate agent should have higher bias than accurate one
        assert f_inaccurate["effort_bias"] > f_accurate["effort_bias"]
        assert f_inaccurate["files_bias"] > f_accurate["files_bias"]

    def test_confidence_levels(self, metrics_dir: str) -> None:
        """Confidence increases with sample size."""
        for i in range(25):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"conf-{i}",
                agent="conf-agent",
                est_min=1,
                est_max=3,
                est_files=5,
                actual_hours=2,
                actual_files=5,
            )
        factors = get_calibration_factor("conf-agent", metrics_dir)
        assert factors["confidence"] == "high"
        assert factors["sample_size"] == 25

    def test_risk_bias_from_retries(self, metrics_dir: str) -> None:
        """Many retries increase risk bias."""
        for i in range(5):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"risky-{i}",
                agent="risky-agent",
                est_min=1,
                est_max=3,
                est_files=5,
                actual_hours=2,
                actual_files=5,
                retries=3,
                bugs=2,
            )
        factors = get_calibration_factor("risky-agent", metrics_dir)
        assert factors["risk_bias"] > 1.0


# ---------------------------------------------------------------------------
# Test: apply_calibration
# ---------------------------------------------------------------------------


class TestApplyCalibration:
    def test_insufficient_data_returns_uncalibrated(self, metrics_dir: str) -> None:
        """With < 10 data points, calibration is not applied."""
        for i in range(5):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"few-{i}",
                agent="few-agent",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=3,
                actual_files=5,
            )
        estimate = {
            "effort_hours_min": 2,
            "effort_hours_max": 4,
            "files_estimate": 5,
            "risk": "medium",
        }
        result = apply_calibration(estimate, "few-agent", metrics_dir)
        assert result["calibration_applied"] is False
        assert "Insufficient data" in result["calibration_note"]

    def test_calibration_adjusts_estimate(self, metrics_dir: str) -> None:
        """With 10+ data points, calibration adjusts the estimate."""
        # Agent consistently underestimates by 2x
        for i in range(12):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"cal-{i}",
                agent="cal-agent",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=6,  # 2x the midpoint
                actual_files=10,  # 2x the estimate
            )
        estimate = {
            "effort_hours_min": 2,
            "effort_hours_max": 4,
            "files_estimate": 5,
            "risk": "medium",
        }
        result = apply_calibration(estimate, "cal-agent", metrics_dir)
        assert result["calibration_applied"] is True
        assert result["effort_hours_min"] > 2  # Should be inflated
        assert result["effort_hours_max"] > 4  # Should be inflated
        assert result["files_estimate"] > 5  # Should be inflated

    def test_calibration_preserves_range(self, metrics_dir: str) -> None:
        """Calibration adjusts both min and max proportionally."""
        for i in range(12):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"range-{i}",
                agent="range-agent",
                est_min=2,
                est_max=8,
                est_files=10,
                actual_hours=10,
                actual_files=20,
            )
        estimate = {
            "effort_hours_min": 2,
            "effort_hours_max": 8,
            "files_estimate": 10,
            "risk": "low",
        }
        result = apply_calibration(estimate, "range-agent", metrics_dir)
        # Both min and max should be multiplied by the same factor
        original_ratio = 8 / 2  # 4x range
        new_ratio = result["effort_hours_max"] / result["effort_hours_min"]
        assert abs(new_ratio - original_ratio) < 0.1  # Range preserved

    def test_risk_upgrade_on_high_bias(self, metrics_dir: str) -> None:
        """High risk bias upgrades the risk level."""
        for i in range(12):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"riskup-{i}",
                agent="riskup-agent",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=3,
                actual_files=5,
                retries=5,  # Many retries = high risk bias
                bugs=3,
            )
        estimate = {"effort_hours_min": 2, "effort_hours_max": 4, "files_estimate": 5, "risk": "low"}
        result = apply_calibration(estimate, "riskup-agent", metrics_dir)
        # Risk should be upgraded from low to medium (or higher)
        assert result["risk"] in ("medium", "high", "critical")


# ---------------------------------------------------------------------------
# Test: format_calibration_report
# ---------------------------------------------------------------------------


class TestCalibrationReport:
    def test_report_with_no_data(self, metrics_dir: str) -> None:
        """Report with no data shows zero data points."""
        report = format_calibration_report("empty-agent", metrics_dir)
        assert "empty-agent" in report
        assert "0" in report
        assert "none" in report

    def test_report_with_data(self, metrics_dir: str) -> None:
        """Report with data includes bias factors and accuracy."""
        for i in range(5):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"rep-{i}",
                agent="rep-agent",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=3,
                actual_files=7,
            )
        report = format_calibration_report("rep-agent", metrics_dir)
        assert "rep-agent" in report
        assert "5" in report  # sample size
        assert "Effort" in report
        assert "Files" in report
        assert "Risk" in report

    def test_report_includes_needs_more_data(self, metrics_dir: str) -> None:
        """Report with < 10 data points shows 'need more data' message."""
        for i in range(3):
            _write_estimate_and_actual(
                metrics_dir,
                task_id=f"need-{i}",
                agent="need-agent",
                est_min=2,
                est_max=4,
                est_files=5,
                actual_hours=3,
                actual_files=5,
            )
        report = format_calibration_report("need-agent", metrics_dir)
        assert "more data points" in report


# ---------------------------------------------------------------------------
# Test: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_metrics_dir(self, metrics_dir: str) -> None:
        """Functions work with empty metrics directory."""
        factors = get_calibration_factor("nobody", metrics_dir)
        assert factors["sample_size"] == 0
        report = format_calibration_report("nobody", metrics_dir)
        assert "nobody" in report

    def test_nonexistent_metrics_dir(self, tmp_path: Path) -> None:
        """Functions work with nonexistent metrics directory."""
        nonexistent = str(tmp_path / "does_not_exist")
        factors = get_calibration_factor("nobody", nonexistent)
        assert factors["sample_size"] == 0

    def test_multiple_estimates_appended(self, metrics_dir: str) -> None:
        """Multiple record_estimate calls append to the same file."""
        for i in range(3):
            record_estimate(
                task_id=f"multi-{i}",
                agent="multi-agent",
                estimates={"complexity": "small", "files_estimate": i + 1},
                metrics_dir=metrics_dir,
            )
        entries = _read_jsonl(metrics_dir)
        assert len(entries) == 3
        assert all(e["type"] == "estimate" for e in entries)
