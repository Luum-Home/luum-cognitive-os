"""Unit tests for lib/cognitive_load_monitor.py

Validates cognitive load monitoring: snapshot recording, baseline computation,
degradation detection (context saturation, instruction drift, hallucination
spike, tool confusion, compound), health scoring, reporting, and persistence.

Python 3.9+ compatible.
"""

import json
from pathlib import Path

import pytest

from lib.cognitive_load_monitor import (
    CognitiveLoadMonitor,
    CognitiveSnapshot,
    _BASELINE_WINDOW,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def monitor() -> CognitiveLoadMonitor:
    """Return a fresh CognitiveLoadMonitor."""
    return CognitiveLoadMonitor()


@pytest.fixture()
def monitor_with_baseline() -> CognitiveLoadMonitor:
    """Return a monitor with an established baseline (5 healthy snapshots)."""
    m = CognitiveLoadMonitor()
    for i in range(1, _BASELINE_WINDOW + 1):
        m.record_snapshot(
            tool_call_number=i,
            output_length=1000,
            task_complexity="medium",
            preamble_compliance=0.95,
            hallucination_count=0,
            instruction_following=0.95,
            tool_call_success=1.0,
            timestamp=1000.0 + i,
        )
    return m


def _record_n_healthy(m: CognitiveLoadMonitor, start: int, count: int) -> None:
    """Record N healthy snapshots starting from tool_call_number=start."""
    for i in range(count):
        m.record_snapshot(
            tool_call_number=start + i,
            output_length=1000,
            task_complexity="medium",
            preamble_compliance=0.95,
            hallucination_count=0,
            instruction_following=0.95,
            tool_call_success=1.0,
            timestamp=2000.0 + i,
        )


# ---------------------------------------------------------------------------
# test_record_snapshot
# ---------------------------------------------------------------------------


class TestRecordSnapshot:
    def test_creates_valid_snapshot(self, monitor: CognitiveLoadMonitor) -> None:
        snap = monitor.record_snapshot(
            tool_call_number=1,
            output_length=500,
            task_complexity="small",
            preamble_compliance=0.9,
            hallucination_count=0,
            instruction_following=1.0,
            tool_call_success=1.0,
        )
        assert isinstance(snap, CognitiveSnapshot)
        assert snap.tool_call_number == 1
        assert snap.output_length == 500
        assert snap.task_complexity == "small"
        assert snap.preamble_compliance == 0.9
        assert snap.hallucination_count == 0
        assert snap.instruction_following == 1.0
        assert snap.tool_call_success == 1.0
        assert 0 <= snap.response_quality_score <= 100
        assert snap.context_usage_pct >= 0

    def test_snapshot_added_to_list(self, monitor: CognitiveLoadMonitor) -> None:
        monitor.record_snapshot(
            tool_call_number=1, output_length=500, task_complexity="small"
        )
        assert len(monitor.snapshots) == 1

    def test_custom_timestamp(self, monitor: CognitiveLoadMonitor) -> None:
        snap = monitor.record_snapshot(
            tool_call_number=1,
            output_length=500,
            task_complexity="small",
            timestamp=12345.0,
        )
        assert snap.timestamp == 12345.0

    def test_max_snapshots_enforced(self) -> None:
        m = CognitiveLoadMonitor(max_snapshots=10)
        for i in range(20):
            m.record_snapshot(
                tool_call_number=i, output_length=500, task_complexity="small"
            )
        assert len(m.snapshots) == 10


# ---------------------------------------------------------------------------
# test_baseline_from_first_5
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_baseline_computed_from_first_5(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        assert monitor_with_baseline.baseline_quality is not None
        # All 5 snapshots are healthy with high scores
        assert monitor_with_baseline.baseline_quality > 80

    def test_no_baseline_with_fewer_snapshots(
        self, monitor: CognitiveLoadMonitor
    ) -> None:
        for i in range(1, _BASELINE_WINDOW):
            monitor.record_snapshot(
                tool_call_number=i, output_length=500, task_complexity="small"
            )
        assert monitor.baseline_quality is None

    def test_baseline_output_length_set(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        assert monitor_with_baseline._baseline_output_length is not None
        assert monitor_with_baseline._baseline_output_length == 1000.0

    def test_baseline_hallucination_rate_set(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        assert monitor_with_baseline._baseline_hallucination_rate is not None
        assert monitor_with_baseline._baseline_hallucination_rate == 0.0


# ---------------------------------------------------------------------------
# test_detect_context_saturation
# ---------------------------------------------------------------------------


class TestContextSaturation:
    def test_output_length_drop_triggers_signal(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        # Record 5 snapshots with significantly shorter output (>30% drop)
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=300,  # 70% drop from 1000 baseline
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=1.0,
                timestamp=3000.0 + i,
            )
        result = monitor_with_baseline.detect_degradation()
        assert result is not None
        signal_types = [s["type"] for s in result["signals"]]
        assert "context_saturation" in signal_types

    def test_no_signal_when_output_stable(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        result = monitor_with_baseline.detect_degradation()
        # No degradation because output is same as baseline
        assert result is None


# ---------------------------------------------------------------------------
# test_detect_instruction_drift
# ---------------------------------------------------------------------------


class TestInstructionDrift:
    def test_low_preamble_compliance_triggers_signal(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.4,  # below 70% threshold
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=1.0,
                timestamp=3000.0 + i,
            )
        result = monitor_with_baseline.detect_degradation()
        assert result is not None
        signal_types = [s["type"] for s in result["signals"]]
        assert "instruction_drift" in signal_types


# ---------------------------------------------------------------------------
# test_detect_hallucination_spike
# ---------------------------------------------------------------------------


class TestHallucinationSpike:
    def test_increasing_hallucinations_triggers_signal(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=3,  # 3 per call vs 0 baseline
                instruction_following=0.95,
                tool_call_success=1.0,
                timestamp=3000.0 + i,
            )
        result = monitor_with_baseline.detect_degradation()
        assert result is not None
        signal_types = [s["type"] for s in result["signals"]]
        assert "hallucination_spike" in signal_types


# ---------------------------------------------------------------------------
# test_detect_tool_confusion
# ---------------------------------------------------------------------------


class TestToolConfusion:
    def test_low_tool_success_triggers_signal(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=0.5,  # below 80% threshold
                timestamp=3000.0 + i,
            )
        result = monitor_with_baseline.detect_degradation()
        assert result is not None
        signal_types = [s["type"] for s in result["signals"]]
        assert "tool_confusion" in signal_types


# ---------------------------------------------------------------------------
# test_detect_compound_degradation
# ---------------------------------------------------------------------------


class TestCompoundDegradation:
    def test_three_plus_signals_trigger_compound(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        # Trigger 3+ signals: short output, low preamble, hallucinations
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=300,  # context_saturation
                task_complexity="medium",
                preamble_compliance=0.3,  # instruction_drift
                hallucination_count=5,  # hallucination_spike
                instruction_following=0.5,
                tool_call_success=0.5,  # tool_confusion
                timestamp=3000.0 + i,
            )
        result = monitor_with_baseline.detect_degradation()
        assert result is not None
        assert result["type"] == "compound_degradation"
        assert result["severity"] == "alert"
        assert len(result["signals"]) >= 3


# ---------------------------------------------------------------------------
# test_no_degradation_when_healthy
# ---------------------------------------------------------------------------


class TestNoDegradation:
    def test_healthy_snapshots_produce_no_degradation(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        result = monitor_with_baseline.detect_degradation()
        assert result is None

    def test_no_degradation_without_baseline(
        self, monitor: CognitiveLoadMonitor
    ) -> None:
        # Only 3 snapshots, baseline not established
        for i in range(3):
            monitor.record_snapshot(
                tool_call_number=i, output_length=500, task_complexity="small"
            )
        assert monitor.detect_degradation() is None


# ---------------------------------------------------------------------------
# test_health_score_degrades_with_signals
# ---------------------------------------------------------------------------


class TestHealthScore:
    def test_healthy_score_is_high(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        score = monitor_with_baseline.cognitive_health_score()
        assert score >= 80

    def test_score_drops_with_poor_metrics(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=100,
                task_complexity="medium",
                preamble_compliance=0.3,
                hallucination_count=5,
                instruction_following=0.3,
                tool_call_success=0.3,
                timestamp=3000.0 + i,
            )
        score = monitor_with_baseline.cognitive_health_score()
        assert score < 60

    def test_empty_monitor_returns_100(self, monitor: CognitiveLoadMonitor) -> None:
        assert monitor.cognitive_health_score() == 100.0


# ---------------------------------------------------------------------------
# test_should_save_and_split
# ---------------------------------------------------------------------------


class TestSaveAndSplit:
    def test_true_when_health_below_threshold(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        # Drive health score below 60
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=100,
                task_complexity="medium",
                preamble_compliance=0.2,
                hallucination_count=5,
                instruction_following=0.2,
                tool_call_success=0.2,
                timestamp=3000.0 + i,
            )
        assert monitor_with_baseline.should_save_and_split() is True

    def test_false_when_healthy(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        assert monitor_with_baseline.should_save_and_split() is False


# ---------------------------------------------------------------------------
# test_format_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    def test_report_contains_health_score(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        report = monitor_with_baseline.format_health_report()
        assert "Cognitive Health:" in report
        assert "/100" in report

    def test_report_contains_baseline(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        report = monitor_with_baseline.format_health_report()
        assert "Baseline" in report
        assert "Current" in report
        assert "Trend" in report

    def test_report_contains_signals(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        report = monitor_with_baseline.format_health_report()
        assert "Signals:" in report

    def test_report_contains_context_usage(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        _record_n_healthy(monitor_with_baseline, 10, 5)
        report = monitor_with_baseline.format_health_report()
        assert "Context usage:" in report

    def test_report_contains_recommendation_when_degraded(
        self, monitor_with_baseline: CognitiveLoadMonitor
    ) -> None:
        for i in range(5):
            monitor_with_baseline.record_snapshot(
                tool_call_number=10 + i,
                output_length=300,
                task_complexity="medium",
                preamble_compliance=0.3,
                hallucination_count=5,
                instruction_following=0.5,
                tool_call_success=0.5,
                timestamp=3000.0 + i,
            )
        report = monitor_with_baseline.format_health_report()
        assert "Recommendation:" in report


# ---------------------------------------------------------------------------
# test_estimate_context_usage
# ---------------------------------------------------------------------------


class TestEstimateContextUsage:
    def test_zero_calls_is_zero(self, monitor: CognitiveLoadMonitor) -> None:
        assert monitor.estimate_context_usage(0) == 0.0

    def test_reasonable_midrange(self, monitor: CognitiveLoadMonitor) -> None:
        # 100 calls * 750 avg tokens = 75000 tokens in 1M window = 7.5%
        pct = monitor.estimate_context_usage(100)
        assert 5.0 <= pct <= 15.0

    def test_caps_at_100(self, monitor: CognitiveLoadMonitor) -> None:
        pct = monitor.estimate_context_usage(100000)
        assert pct == 100.0

    def test_smaller_window_gives_higher_pct(self) -> None:
        m = CognitiveLoadMonitor(context_window=100_000)
        pct = m.estimate_context_usage(100)
        # 100 * 750 = 75000 in 100K window = 75%
        assert pct > 50.0


# ---------------------------------------------------------------------------
# test_save_metrics
# ---------------------------------------------------------------------------


class TestSaveMetrics:
    def test_writes_jsonl_file(
        self, monitor_with_baseline: CognitiveLoadMonitor, tmp_path: Path
    ) -> None:
        output_file = tmp_path / "cognitive-load.jsonl"
        monitor_with_baseline.save_metrics(str(output_file))

        assert output_file.exists()
        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == _BASELINE_WINDOW

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "tool_call_number" in data
            assert "response_quality_score" in data
            assert "context_usage_pct" in data

    def test_creates_parent_dirs(
        self, monitor_with_baseline: CognitiveLoadMonitor, tmp_path: Path
    ) -> None:
        output_file = tmp_path / "nested" / "dir" / "metrics.jsonl"
        monitor_with_baseline.save_metrics(str(output_file))
        assert output_file.exists()

    def test_appends_to_existing(
        self, monitor: CognitiveLoadMonitor, tmp_path: Path
    ) -> None:
        output_file = tmp_path / "cognitive-load.jsonl"
        # Write initial data
        output_file.write_text('{"existing": true}\n')

        monitor.record_snapshot(
            tool_call_number=1, output_length=500, task_complexity="small"
        )
        monitor.save_metrics(str(output_file))

        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == 2  # existing + new
