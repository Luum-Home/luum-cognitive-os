"""Unit tests for lib/symbiosis_monitor.py

Validates symbiosis health classification, overhead/value measurement,
ratio calculation, report formatting, and JSONL logging.
"""

import json
import time
from pathlib import Path
from typing import Optional

import pytest

from lib.symbiosis_monitor import SymbiosisMonitor, SymbiosisReport, _read_jsonl_last_24h

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_jsonl_entry(extra: Optional[dict] = None) -> str:
    """Create a JSONL entry with a current timestamp."""
    entry = {"timestamp": _iso_now(), "timestamp_epoch": int(time.time())}
    if extra:
        entry.update(extra)
    return json.dumps(entry)


def _setup_project(tmp_path, *, rules_content="# Minimal rules\n", claude_md_content=None):
    """Create a minimal project structure in tmp_path."""
    # Rules
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "RULES-COMPACT.md").write_text(rules_content)

    # Metrics dir
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    # Optional CLAUDE.md
    if claude_md_content is not None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(claude_md_content)

    return metrics_dir


# ---------------------------------------------------------------------------
# classify_health
# ---------------------------------------------------------------------------


class TestClassifyHealth:
    """Tests for SymbiosisMonitor.classify_health()."""

    def test_zero_ratio_is_symbiotic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.0) == "symbiotic"

    def test_below_healthy_threshold_is_symbiotic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.05) == "symbiotic"

    def test_exactly_healthy_threshold_is_symbiotic(self, tmp_path):
        """At exactly 10%, still symbiotic (<=)."""
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.10) == "symbiotic"

    def test_between_thresholds_is_neutral(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.20) == "neutral"

    def test_exactly_parasitic_threshold_is_neutral(self, tmp_path):
        """At exactly 30%, still neutral (<=)."""
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.30) == "neutral"

    def test_above_parasitic_threshold_is_parasitic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.31) == "parasitic"

    def test_high_ratio_is_parasitic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        assert m.classify_health(0.80) == "parasitic"


# ---------------------------------------------------------------------------
# calculate_ratio
# ---------------------------------------------------------------------------


class TestCalculateRatio:
    """Tests for SymbiosisMonitor.calculate_ratio()."""

    def test_zero_everything_returns_zero(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        overhead = {"total_overhead_tokens": 0}
        value = {
            "tasks_completed": 0, "errors_caught": 0,
            "errors_auto_fixed": 0, "skills_used": 0, "memory_saves": 0,
        }
        assert m.calculate_ratio(overhead, value) == 0.0

    def test_high_overhead_low_value_is_parasitic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        overhead = {"total_overhead_tokens": 10000}
        value = {
            "tasks_completed": 0, "errors_caught": 0,
            "errors_auto_fixed": 0, "skills_used": 1, "memory_saves": 0,
        }
        # useful = 2000, total = 12000, ratio = 10000/12000 ~ 0.833
        ratio = m.calculate_ratio(overhead, value)
        assert ratio > 0.80

    def test_low_overhead_high_value_is_symbiotic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        overhead = {"total_overhead_tokens": 500}
        value = {
            "tasks_completed": 5, "errors_caught": 3,
            "errors_auto_fixed": 1, "skills_used": 10, "memory_saves": 5,
        }
        # useful = 25000+9000+8000+20000+2500 = 64500
        # total = 65000, ratio = 500/65000 ~ 0.008
        ratio = m.calculate_ratio(overhead, value)
        assert ratio < 0.01

    def test_only_overhead_no_value(self, tmp_path):
        """All overhead, no value: ratio should be 1.0 (100%)."""
        m = SymbiosisMonitor(str(tmp_path))
        overhead = {"total_overhead_tokens": 5000}
        value = {
            "tasks_completed": 0, "errors_caught": 0,
            "errors_auto_fixed": 0, "skills_used": 0, "memory_saves": 0,
        }
        assert m.calculate_ratio(overhead, value) == 1.0


# ---------------------------------------------------------------------------
# measure_overhead
# ---------------------------------------------------------------------------


class TestMeasureOverhead:
    """Tests for SymbiosisMonitor.measure_overhead()."""

    def test_empty_project_returns_zeros_for_non_file_metrics(self, tmp_path):
        """A project with no rules or metrics should return zeros for dynamic metrics."""
        m = SymbiosisMonitor(str(tmp_path))
        overhead = m.measure_overhead()
        assert overhead["rules_tokens"] == 0
        assert overhead["hook_latency_ms"] == 0
        assert overhead["hook_count"] == 0
        assert overhead["governance_tokens"] == 0
        # claude_md_tokens may be non-zero if ~/.claude/CLAUDE.md exists globally

    def test_reads_rules_compact(self, tmp_path):
        _setup_project(tmp_path, rules_content="x" * 400)
        m = SymbiosisMonitor(str(tmp_path))
        overhead = m.measure_overhead()
        # 400 chars / 4 = 100 tokens
        assert overhead["rules_tokens"] == 100

    def test_reads_claude_md(self, tmp_path):
        _setup_project(tmp_path, claude_md_content="y" * 800)
        m = SymbiosisMonitor(str(tmp_path))
        overhead = m.measure_overhead()
        assert overhead["claude_md_tokens"] == 200

    def test_reads_hook_performance(self, tmp_path):
        metrics_dir = _setup_project(tmp_path)
        perf_file = metrics_dir / "performance.jsonl"
        entries = [
            _make_jsonl_entry({"component": "hook:blast-radius", "duration_ms": 42}),
            _make_jsonl_entry({"component": "hook:clarification-gate", "duration_ms": 18}),
            _make_jsonl_entry({"component": "skill:sdd-apply", "duration_ms": 5000}),
        ]
        perf_file.write_text("\n".join(entries) + "\n")

        m = SymbiosisMonitor(str(tmp_path))
        overhead = m.measure_overhead()
        assert overhead["hook_latency_ms"] == 60  # 42 + 18 (skill excluded)
        assert overhead["hook_count"] == 2


# ---------------------------------------------------------------------------
# measure_value
# ---------------------------------------------------------------------------


class TestMeasureValue:
    """Tests for SymbiosisMonitor.measure_value()."""

    def test_empty_project_returns_zeros(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        value = m.measure_value()
        assert value["tasks_completed"] == 0
        assert value["errors_caught"] == 0
        assert value["errors_auto_fixed"] == 0
        assert value["skills_used"] == 0
        assert value["memory_saves"] == 0

    def test_counts_errors(self, tmp_path):
        metrics_dir = _setup_project(tmp_path)
        error_file = metrics_dir / "error-learning.jsonl"
        entries = [_make_jsonl_entry({"type": "TEST_FAILURE"}) for _ in range(3)]
        error_file.write_text("\n".join(entries) + "\n")

        m = SymbiosisMonitor(str(tmp_path))
        value = m.measure_value()
        assert value["errors_caught"] == 3

    def test_counts_auto_repairs(self, tmp_path):
        metrics_dir = _setup_project(tmp_path)
        repair_file = metrics_dir / "repair-outcomes.jsonl"
        entries = [
            _make_jsonl_entry({"outcome": "success"}),
            _make_jsonl_entry({"outcome": "failure"}),
            _make_jsonl_entry({"outcome": "success"}),
        ]
        repair_file.write_text("\n".join(entries) + "\n")

        m = SymbiosisMonitor(str(tmp_path))
        value = m.measure_value()
        assert value["errors_auto_fixed"] == 2

    def test_counts_skill_invocations(self, tmp_path):
        metrics_dir = _setup_project(tmp_path)
        skill_file = metrics_dir / "skill-metrics.jsonl"
        entries = [_make_jsonl_entry({"skill": "sdd-apply"}) for _ in range(5)]
        skill_file.write_text("\n".join(entries) + "\n")

        m = SymbiosisMonitor(str(tmp_path))
        value = m.measure_value()
        assert value["skills_used"] == 5

    def test_counts_completed_tasks(self, tmp_path):
        _setup_project(tmp_path)
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True)
        tasks_data = {
            "tasks": [
                {"id": "1", "status": "completed"},
                {"id": "2", "status": "in_progress"},
                {"id": "3", "status": "completed"},
            ]
        }
        (tasks_dir / "active-tasks.json").write_text(json.dumps(tasks_data))

        m = SymbiosisMonitor(str(tmp_path))
        value = m.measure_value()
        assert value["tasks_completed"] == 2


# ---------------------------------------------------------------------------
# recommend
# ---------------------------------------------------------------------------


class TestRecommend:
    """Tests for SymbiosisMonitor.recommend()."""

    def test_symbiotic_no_recommendation(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        assert m.recommend("symbiotic", {"rules_tokens": 0, "hook_count": 0, "governance_tokens": 0, "claude_md_tokens": 0}) is None

    def test_neutral_has_recommendation(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        rec = m.recommend("neutral", {"rules_tokens": 0, "hook_count": 0, "governance_tokens": 0, "claude_md_tokens": 0})
        assert rec is not None
        assert "acceptable" in rec.lower()

    def test_parasitic_high_rules(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        rec = m.recommend("parasitic", {"rules_tokens": 5000, "hook_count": 5, "governance_tokens": 500, "claude_md_tokens": 1000})
        assert rec is not None
        assert "lean" in rec.lower() or "rules" in rec.lower()

    def test_parasitic_many_hooks(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        rec = m.recommend("parasitic", {"rules_tokens": 500, "hook_count": 30, "governance_tokens": 500, "claude_md_tokens": 1000})
        assert rec is not None
        assert "hook" in rec.lower() or "capability" in rec.lower()

    def test_parasitic_fallback(self, tmp_path):
        """When no specific overhead is high, suggest raising capability level."""
        m = SymbiosisMonitor(str(tmp_path))
        rec = m.recommend("parasitic", {"rules_tokens": 500, "hook_count": 5, "governance_tokens": 500, "claude_md_tokens": 1000})
        assert rec is not None
        assert "capability" in rec.lower()


# ---------------------------------------------------------------------------
# generate_report (integration)
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Integration tests for the full report pipeline."""

    def test_empty_project_returns_healthy_report(self, tmp_path, monkeypatch):
        """A new project with no metrics should be symbiotic (zero overhead, zero value)."""
        # Prevent picking up the real ~/.claude/CLAUDE.md
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "fakehome")
        m = SymbiosisMonitor(str(tmp_path))
        report = m.generate_report()
        # Zero everything -> ratio 0.0 -> symbiotic
        assert report.health == "symbiotic"
        assert report.overhead_ratio == 0.0
        assert report.total_overhead_tokens == 0

    def test_high_overhead_low_value_is_parasitic(self, tmp_path):
        """Large rules with no productive output -> parasitic."""
        # Create a large RULES-COMPACT.md (20000 chars = 5000 tokens)
        _setup_project(tmp_path, rules_content="x" * 20000)
        m = SymbiosisMonitor(str(tmp_path))
        report = m.generate_report()
        assert report.health == "parasitic"
        assert report.overhead_ratio > 0.30
        assert report.recommendation is not None

    def test_low_overhead_high_value_is_symbiotic(self, tmp_path):
        """Small rules, lots of completed work -> symbiotic."""
        metrics_dir = _setup_project(tmp_path, rules_content="x" * 40)  # 10 tokens

        # Add many skill invocations
        skill_file = metrics_dir / "skill-metrics.jsonl"
        entries = [_make_jsonl_entry({"skill": f"skill-{i}"}) for i in range(20)]
        skill_file.write_text("\n".join(entries) + "\n")

        # Add errors caught
        error_file = metrics_dir / "error-learning.jsonl"
        error_entries = [_make_jsonl_entry({"type": "TEST_FAILURE"}) for _ in range(5)]
        error_file.write_text("\n".join(error_entries) + "\n")

        m = SymbiosisMonitor(str(tmp_path))
        report = m.generate_report()
        assert report.health == "symbiotic"
        assert report.overhead_ratio < 0.10


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    """Tests for SymbiosisMonitor.format_report()."""

    def test_format_contains_key_sections(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        report = SymbiosisReport(
            rules_tokens=2000, claude_md_tokens=1000,
            hook_latency_ms=150, hook_count=10,
            governance_tokens=500, total_overhead_tokens=3500,
            tasks_completed=3, errors_caught=2,
            errors_auto_fixed=1, skills_used=8, memory_saves=4,
            overhead_ratio=0.05, health="symbiotic", recommendation=None,
        )
        text = m.format_report(report)
        assert "SYMBIOSIS REPORT" in text
        assert "OVERHEAD" in text
        assert "VALUE" in text
        assert "SYMBIOTIC" in text
        assert "2,000" in text  # rules_tokens formatted
        assert "RECOMMENDATION" not in text  # no recommendation for healthy

    def test_format_shows_recommendation_for_parasitic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        report = SymbiosisReport(
            rules_tokens=5000, claude_md_tokens=3000,
            hook_latency_ms=500, hook_count=25,
            governance_tokens=2000, total_overhead_tokens=10000,
            tasks_completed=0, errors_caught=0,
            errors_auto_fixed=0, skills_used=1, memory_saves=0,
            overhead_ratio=0.83, health="parasitic",
            recommendation="Reduce rules loading: switch to lean efficiency profile",
        )
        text = m.format_report(report)
        assert "PARASITIC" in text
        assert "RECOMMENDATION" in text
        assert "lean" in text.lower()


# ---------------------------------------------------------------------------
# log_report
# ---------------------------------------------------------------------------


class TestLogReport:
    """Tests for SymbiosisMonitor.log_report()."""

    def test_creates_jsonl_file(self, tmp_path):
        metrics_dir = _setup_project(tmp_path)
        m = SymbiosisMonitor(str(tmp_path))
        report = SymbiosisReport(
            rules_tokens=100, claude_md_tokens=50,
            hook_latency_ms=10, hook_count=2,
            governance_tokens=0, total_overhead_tokens=150,
            tasks_completed=1, errors_caught=0,
            errors_auto_fixed=0, skills_used=2, memory_saves=1,
            overhead_ratio=0.02, health="symbiotic", recommendation=None,
        )
        m.log_report(report)

        log_file = metrics_dir / "symbiosis.jsonl"
        assert log_file.exists()

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["health"] == "symbiotic"
        assert entry["overhead_ratio"] == 0.02
        assert entry["overhead_tokens"] == 150
        assert entry["tasks_completed"] == 1
        assert "timestamp" in entry

    def test_appends_multiple_entries(self, tmp_path):
        metrics_dir = _setup_project(tmp_path)
        m = SymbiosisMonitor(str(tmp_path))
        report = SymbiosisReport(
            rules_tokens=0, claude_md_tokens=0,
            hook_latency_ms=0, hook_count=0,
            governance_tokens=0, total_overhead_tokens=0,
            tasks_completed=0, errors_caught=0,
            errors_auto_fixed=0, skills_used=0, memory_saves=0,
            overhead_ratio=0.0, health="symbiotic", recommendation=None,
        )
        m.log_report(report)
        m.log_report(report)

        log_file = metrics_dir / "symbiosis.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_creates_metrics_dir_if_missing(self, tmp_path):
        """log_report should create the metrics directory if it doesn't exist."""
        m = SymbiosisMonitor(str(tmp_path))
        report = SymbiosisReport(
            rules_tokens=0, claude_md_tokens=0,
            hook_latency_ms=0, hook_count=0,
            governance_tokens=0, total_overhead_tokens=0,
            tasks_completed=0, errors_caught=0,
            errors_auto_fixed=0, skills_used=0, memory_saves=0,
            overhead_ratio=0.0, health="symbiotic", recommendation=None,
        )
        m.log_report(report)
        assert (tmp_path / ".cognitive-os" / "metrics" / "symbiosis.jsonl").exists()


# ---------------------------------------------------------------------------
# _read_jsonl_last_24h
# ---------------------------------------------------------------------------


class TestReadJsonlLast24h:
    """Tests for the JSONL reader utility."""

    def test_missing_file_returns_empty(self, tmp_path):
        result = _read_jsonl_last_24h(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        assert _read_jsonl_last_24h(f) == []

    def test_reads_recent_entries(self, tmp_path):
        f = tmp_path / "data.jsonl"
        entries = [_make_jsonl_entry({"value": i}) for i in range(3)]
        f.write_text("\n".join(entries) + "\n")
        result = _read_jsonl_last_24h(f)
        assert len(result) == 3

    def test_filters_old_entries_by_epoch(self, tmp_path):
        f = tmp_path / "data.jsonl"
        old_entry = json.dumps({"timestamp_epoch": 1000000, "old": True})
        new_entry = _make_jsonl_entry({"new": True})
        f.write_text(old_entry + "\n" + new_entry + "\n")

        result = _read_jsonl_last_24h(f)
        assert len(result) == 1
        assert result[0].get("new") is True

    def test_skips_malformed_lines(self, tmp_path):
        f = tmp_path / "data.jsonl"
        content = "not json\n" + _make_jsonl_entry({"good": True}) + "\n"
        f.write_text(content)

        result = _read_jsonl_last_24h(f)
        assert len(result) == 1
        assert result[0].get("good") is True


# ---------------------------------------------------------------------------
# Threshold boundary tests
# ---------------------------------------------------------------------------


class TestThresholdBoundaries:
    """Verify exact threshold boundary behavior."""

    def test_ratio_just_above_parasitic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        # 0.30001 should be parasitic
        assert m.classify_health(0.30001) == "parasitic"

    def test_ratio_just_below_healthy(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        # 0.09999 should be symbiotic
        assert m.classify_health(0.09999) == "symbiotic"

    def test_ratio_just_above_healthy(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        # 0.10001 should be neutral
        assert m.classify_health(0.10001) == "neutral"

    def test_ratio_just_below_parasitic(self, tmp_path):
        m = SymbiosisMonitor(str(tmp_path))
        # 0.29999 should be neutral
        assert m.classify_health(0.29999) == "neutral"
