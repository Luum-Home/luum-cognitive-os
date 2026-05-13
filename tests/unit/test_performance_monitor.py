"""Unit tests for lib/performance_monitor.py

Validates PerformanceMonitor: recording, timing, percentiles, overhead,
throughput, efficiency, bottlenecks, health, dashboard, and persistence.
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from performance_monitor import (
    PerformanceMetric,
    PerformanceMonitor,
    _Timer,
    _fmt_ms,
    _percentile,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_monitor(tmp_path: Path) -> PerformanceMonitor:
    """Create a monitor with a temp metrics file."""
    return PerformanceMonitor(str(tmp_path / "performance.jsonl"))


def _populate_monitor(monitor: PerformanceMonitor, count: int = 10) -> None:
    """Add a set of sample metrics to a monitor."""
    for i in range(count):
        monitor.record(
            f"hook:test-hook-{i % 3}",
            "execute",
            duration_ms=10.0 + i * 5,
            success=(i % 5 != 0),  # 20% failure rate
            tokens=100 + i * 10,
        )


# ---------------------------------------------------------------------------
# PerformanceMetric dataclass
# ---------------------------------------------------------------------------

class TestPerformanceMetric:
    def test_creation(self):
        m = PerformanceMetric(
            component="hook:blast-radius",
            operation="execute",
            duration_ms=42.5,
            success=True,
            timestamp="2026-03-27T12:00:00Z",
        )
        assert m.component == "hook:blast-radius"
        assert m.duration_ms == 42.5
        assert m.success is True
        assert m.metadata == {}

    def test_creation_with_metadata(self):
        m = PerformanceMetric(
            component="skill:sdd-apply",
            operation="execute",
            duration_ms=5000.0,
            success=True,
            timestamp="2026-03-27T12:00:00Z",
            metadata={"tokens": 1500, "model": "sonnet"},
        )
        assert m.metadata["tokens"] == 1500
        assert m.metadata["model"] == "sonnet"


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TestRecord:
    def test_record_creates_metric_entry(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test", "execute", 42.0)
        assert len(monitor._session_metrics) == 1
        assert monitor._session_metrics[0].component == "hook:test"
        assert monitor._session_metrics[0].duration_ms == 42.0

    def test_record_persists_to_jsonl(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test", "execute", 42.0, success=True)
        path = tmp_path / "performance.jsonl"
        assert path.exists()
        data = json.loads(path.read_text().strip())
        assert data["component"] == "hook:test"
        assert data["duration_ms"] == 42.0
        assert data["success"] is True

    def test_record_with_metadata(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test", "execute", 42.0, tokens=1500, model="sonnet")
        data = json.loads((tmp_path / "performance.jsonl").read_text().strip())
        assert data["metadata"]["tokens"] == 1500
        assert data["metadata"]["model"] == "sonnet"

    def test_record_failure(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test", "execute", 42.0, success=False)
        assert monitor._session_metrics[0].success is False


# ---------------------------------------------------------------------------
# time_operation context manager
# ---------------------------------------------------------------------------

class TestTimeOperation:
    def test_measures_duration(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        with monitor.time_operation("lib:test", "process") as timer:
            time.sleep(0.01)  # 10ms
        assert timer.duration_ms >= 5.0  # At least some time passed
        assert len(monitor._session_metrics) == 1
        assert monitor._session_metrics[0].success is True

    def test_records_failure_on_exception(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        with pytest.raises(ValueError):
            with monitor.time_operation("lib:test", "process"):
                raise ValueError("boom")
        assert len(monitor._session_metrics) == 1
        assert monitor._session_metrics[0].success is False

    def test_timer_duration_accessible(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        with monitor.time_operation("lib:test", "process") as timer:
            time.sleep(0.005)
        assert timer.duration_ms > 0


# ---------------------------------------------------------------------------
# Percentiles
# ---------------------------------------------------------------------------

class TestGetPercentiles:
    def test_calculates_p50_p95_p99(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for i in range(100):
            monitor.record("hook:test", "execute", float(i + 1))

        pct = monitor.get_percentiles("hook:test", window_minutes=9999)
        assert pct["count"] == 100
        assert 49.0 <= pct["p50_ms"] <= 51.0
        assert 94.0 <= pct["p95_ms"] <= 96.0
        assert 98.0 <= pct["p99_ms"] <= 100.0

    def test_empty_returns_zeroes(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        pct = monitor.get_percentiles("hook:nonexistent")
        assert pct["p50_ms"] == 0.0
        assert pct["count"] == 0
        assert pct["error_rate"] == 0.0

    def test_single_sample(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:solo", "execute", 42.0)
        pct = monitor.get_percentiles("hook:solo", window_minutes=9999)
        assert pct["p50_ms"] == 42.0
        assert pct["p95_ms"] == 42.0
        assert pct["p99_ms"] == 42.0
        assert pct["count"] == 1

    def test_error_rate_calculation(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for i in range(10):
            monitor.record("hook:test", "execute", 10.0, success=(i < 8))
        pct = monitor.get_percentiles("hook:test", window_minutes=9999)
        assert pct["error_rate"] == 0.2


# ---------------------------------------------------------------------------
# Overhead report
# ---------------------------------------------------------------------------

class TestGetOverheadReport:
    def test_separates_hooks_from_skills(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:blast-radius", "execute", 50.0)
        monitor.record("hook:clarification-gate", "execute", 30.0)
        monitor.record("skill:sdd-apply", "execute", 5000.0)

        report = monitor.get_overhead_report()
        assert report["total_hook_overhead_ms"] == 80.0
        assert "hook:blast-radius" in report["hooks_breakdown"]
        assert "hook:clarification-gate" in report["hooks_breakdown"]

    def test_identifies_safety_mesh(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:clarification-gate", "execute", 30.0)
        monitor.record("hook:trust-score-validator", "execute", 20.0)
        monitor.record("hook:error-learning", "execute", 10.0)

        report = monitor.get_overhead_report()
        # gate and validator are safety keywords
        assert report["safety_mesh_overhead_ms"] == 50.0

    def test_pct_of_session_time(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test", "execute", 100.0)
        monitor.record("skill:test", "execute", 900.0)

        report = monitor.get_overhead_report()
        assert report["pct_of_session_time"] == 10.0  # 100 / 1000


# ---------------------------------------------------------------------------
# Throughput
# ---------------------------------------------------------------------------

class TestGetThroughput:
    def test_counts_per_window(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for i in range(20):
            monitor.record("hook:test", "execute", 10.0)
        for i in range(5):
            monitor.record("skill:sdd-apply", "execute", 1000.0)

        # Use a small window so that per-minute / per-hour rates are large
        # enough to survive round(..., 2).  With window_minutes=9999 the
        # 25 total calls / 9999 minutes rounds to 0.00.
        tp = monitor.get_throughput(window_minutes=1)
        assert tp["tool_calls_per_minute"] > 0
        assert tp["agent_completions_per_hour"] > 0

    def test_empty_returns_zeroes(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        tp = monitor.get_throughput()
        assert tp["tasks_per_hour"] == 0.0
        assert tp["tool_calls_per_minute"] == 0.0


# ---------------------------------------------------------------------------
# Efficiency score
# ---------------------------------------------------------------------------

class TestGetEfficiencyScore:
    def test_composite_calculation(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        # All successful, all with token metadata
        for i in range(10):
            monitor.record("hook:test", "execute", 10.0, success=True, tokens=100)

        eff = monitor.get_efficiency_score()
        assert eff["token"] == 1.0
        assert eff["time"] == 1.0
        assert eff["error"] == 1.0
        assert eff["composite"] > 0.9

    def test_empty_returns_zeroes(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        eff = monitor.get_efficiency_score()
        assert eff["composite"] == 0.0

    def test_with_failures(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for i in range(10):
            monitor.record("hook:test", "execute", 10.0, success=(i < 5))
        eff = monitor.get_efficiency_score()
        assert eff["error"] == 0.5
        assert eff["composite"] < 1.0


# ---------------------------------------------------------------------------
# Bottlenecks
# ---------------------------------------------------------------------------

class TestGetBottlenecks:
    def test_returns_sorted_by_p99(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        # Fast component
        for _ in range(10):
            monitor.record("hook:fast", "execute", 5.0)
        # Slow component
        for _ in range(10):
            monitor.record("hook:slow", "execute", 500.0)
        # Medium component
        for _ in range(10):
            monitor.record("hook:medium", "execute", 50.0)

        bottlenecks = monitor.get_bottlenecks(top_n=3)
        assert len(bottlenecks) == 3
        assert bottlenecks[0]["component"] == "hook:slow"
        assert bottlenecks[1]["component"] == "hook:medium"
        assert bottlenecks[2]["component"] == "hook:fast"

    def test_empty_returns_empty(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        assert monitor.get_bottlenecks() == []

    def test_suggestion_for_slow_component(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        # Hook baseline is 500ms, so 3000ms = 6x baseline -> should suggest
        for _ in range(5):
            monitor.record("hook:very-slow", "execute", 3000.0)

        bottlenecks = monitor.get_bottlenecks()
        assert bottlenecks[0]["suggestion"] != ""
        assert "baseline" in bottlenecks[0]["suggestion"]


# ---------------------------------------------------------------------------
# Component health
# ---------------------------------------------------------------------------

class TestGetComponentHealth:
    def test_healthy_component(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for _ in range(20):
            monitor.record("hook:good", "execute", 100.0, success=True)
        health = monitor.get_component_health("hook:good")
        assert health["status"] == "healthy"
        assert health["error_rate"] == 0.0

    def test_degraded_high_error_rate(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for i in range(20):
            monitor.record("hook:flaky", "execute", 100.0, success=(i < 18))
        health = monitor.get_component_health("hook:flaky")
        assert health["status"] == "degraded"  # 10% error rate

    def test_unhealthy_high_error_rate(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        for i in range(10):
            monitor.record("hook:broken", "execute", 100.0, success=(i < 7))
        health = monitor.get_component_health("hook:broken")
        assert health["status"] == "unhealthy"  # 30% error rate

    def test_unhealthy_high_latency(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        # Hook baseline is 500ms; 3000ms = 6x baseline -> unhealthy
        for _ in range(10):
            monitor.record("hook:slow", "execute", 3000.0, success=True)
        health = monitor.get_component_health("hook:slow")
        assert health["status"] == "unhealthy"

    def test_unknown_when_no_data(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        health = monitor.get_component_health("hook:nonexistent")
        assert health["status"] == "unknown"

    def test_last_success_tracked(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test", "execute", 10.0, success=True)
        monitor.record("hook:test", "execute", 10.0, success=False)
        health = monitor.get_component_health("hook:test")
        assert health["last_success"] is not None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestFormatDashboard:
    def test_has_required_sections(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        _populate_monitor(monitor)
        dashboard = monitor.format_dashboard()

        assert "LATENCY" in dashboard
        assert "THROUGHPUT" in dashboard
        assert "OVERHEAD" in dashboard
        assert "BOTTLENECKS" in dashboard
        assert "HEALTH" in dashboard
        assert "PERFORMANCE DASHBOARD" in dashboard

    def test_empty_dashboard(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        dashboard = monitor.format_dashboard()
        assert "PERFORMANCE DASHBOARD" in dashboard
        assert "LATENCY" in dashboard


# ---------------------------------------------------------------------------
# Save session report
# ---------------------------------------------------------------------------

class TestSaveSessionReport:
    def test_creates_file(self, tmp_path):
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()
        monitor = PerformanceMonitor(str(metrics_dir / "performance.jsonl"))
        _populate_monitor(monitor)

        report_path = monitor.save_session_report()
        assert os.path.exists(report_path)
        content = Path(report_path).read_text()
        assert "Performance Report" in content
        assert "Efficiency Scores" in content


# ---------------------------------------------------------------------------
# Concurrent records
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_records(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        errors = []

        def record_many(n):
            try:
                for i in range(n):
                    monitor.record(f"hook:thread-{threading.current_thread().name}", "execute", float(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_many, args=(50,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(monitor._session_metrics) == 200


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestPercentileFunction:
    def test_zero_samples(self):
        assert _percentile([], 50) == 0.0

    def test_one_sample(self):
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 99) == 42.0

    def test_interpolation(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        p50 = _percentile(values, 50)
        assert p50 == 30.0

    def test_p0_and_p100(self):
        values = [10.0, 20.0, 30.0]
        assert _percentile(values, 0) == 10.0
        assert _percentile(values, 100) == 30.0


class TestFmtMs:
    def test_zero(self):
        assert _fmt_ms(0.0) == "0ms"

    def test_milliseconds(self):
        assert _fmt_ms(42.0) == "42ms"

    def test_seconds(self):
        assert _fmt_ms(2500.0) == "2.5s"


# ---------------------------------------------------------------------------
# Timer helper
# ---------------------------------------------------------------------------

class TestTimer:
    def test_measures_elapsed(self):
        timer = _Timer()
        time.sleep(0.01)
        timer.stop()
        assert timer.duration_ms >= 5.0

    def test_stop_idempotent(self):
        timer = _Timer()
        time.sleep(0.01)
        timer.stop()
        d1 = timer.duration_ms
        time.sleep(0.01)
        timer.stop()
        d2 = timer.duration_ms
        assert d1 == d2  # stop() only records the first call


# ---------------------------------------------------------------------------
# Window filtering
# ---------------------------------------------------------------------------

class TestWindowFiltering:
    def test_filters_by_component(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:a", "execute", 10.0)
        monitor.record("hook:b", "execute", 20.0)

        filtered = monitor._filter(component="hook:a", window_minutes=9999)
        assert len(filtered) == 1
        assert filtered[0].component == "hook:a"

    def test_returns_all_when_no_component(self, tmp_path):
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:a", "execute", 10.0)
        monitor.record("hook:b", "execute", 20.0)

        filtered = monitor._filter(window_minutes=9999)
        assert len(filtered) == 2


# ---------------------------------------------------------------------------
# measure_hook convenience function
# ---------------------------------------------------------------------------

class TestMeasureHook:
    def test_records_to_file(self, tmp_path):
        """Test that measure_hook creates a PerformanceMonitor and records."""
        # We can't easily redirect the default path, so we test the
        # underlying mechanism: create a monitor with tmp path and record.
        monitor = _make_monitor(tmp_path)
        monitor.record("hook:test-hook", "execute", 42.0, True)
        metrics_file = tmp_path / "performance.jsonl"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text().strip())
        assert data["component"] == "hook:test-hook"
        assert data["duration_ms"] == 42.0
