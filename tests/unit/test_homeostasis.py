"""Unit tests for lib/homeostasis.py

Validates the homeostasis control loops: metric collection, diagnosis
(adjustments for capability level, model routing, self-improvement,
symbiosis), auto-apply logic, and report formatting.
"""

import json
import time

import pytest

from lib.homeostasis import (
    Adjustment,
    HealthMetrics,
    Homeostasis,
    _read_jsonl,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_metrics(**overrides) -> HealthMetrics:
    """Create a HealthMetrics with sane healthy defaults, overridable."""
    defaults = dict(
        tokens_per_session_avg=20000,
        error_rate_24h=0.03,
        cost_today_usd=3.00,
        budget_remaining_pct=0.70,
        task_success_rate=0.90,
        overhead_ratio=0.08,
        current_capability_level=3,
        current_phase="reconstruction",
    )
    defaults.update(overrides)
    return HealthMetrics(**defaults)


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with config and metrics dirs."""
    config = tmp_path / "cognitive-os.yaml"
    config.write_text(
        "project:\n"
        "  name: test-project\n"
        "  phase: reconstruction\n"
        "\n"
        "model_capability:\n"
        "  level: 3\n"
        "\n"
        "resources:\n"
        "  budget:\n"
        "    daily_alert_usd: 10\n"
    )
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def homeostasis(project_dir):
    """Create a Homeostasis instance for the test project."""
    return Homeostasis(str(project_dir))


# ---------------------------------------------------------------------------
# _read_jsonl
# ---------------------------------------------------------------------------


class TestReadJsonl:
    """Tests for the JSONL reader helper."""

    def test_missing_file_returns_empty(self, tmp_path):
        result = _read_jsonl(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_reads_valid_lines(self, tmp_path):
        path = tmp_path / "test.jsonl"
        path.write_text('{"a":1}\n{"b":2}\n')
        result = _read_jsonl(path)
        assert len(result) == 2
        assert result[0] == {"a": 1}

    def test_skips_bad_json(self, tmp_path):
        path = tmp_path / "test.jsonl"
        path.write_text('{"a":1}\nBAD LINE\n{"b":2}\n')
        result = _read_jsonl(path)
        assert len(result) == 2

    def test_filters_by_age_epoch(self, tmp_path):
        path = tmp_path / "test.jsonl"
        now = time.time()
        old = now - 200000  # ~2.3 days ago
        path.write_text(
            json.dumps({"timestamp_epoch": old, "val": "old"}) + "\n"
            + json.dumps({"timestamp_epoch": now, "val": "new"}) + "\n"
        )
        result = _read_jsonl(path, max_age_seconds=86400)
        assert len(result) == 1
        assert result[0]["val"] == "new"

    def test_filters_by_age_iso(self, tmp_path):
        from datetime import datetime, timezone, timedelta

        path = tmp_path / "test.jsonl"
        old_ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        new_ts = datetime.now(timezone.utc).isoformat()
        path.write_text(
            json.dumps({"timestamp": old_ts, "val": "old"}) + "\n"
            + json.dumps({"timestamp": new_ts, "val": "new"}) + "\n"
        )
        result = _read_jsonl(path, max_age_seconds=86400)
        assert len(result) == 1
        assert result[0]["val"] == "new"


# ---------------------------------------------------------------------------
# Healthy metrics -> no adjustments
# ---------------------------------------------------------------------------


class TestHealthyOrganism:
    """When all metrics are within thresholds, no adjustments should be produced."""

    def test_healthy_metrics_produce_no_adjustments(self, homeostasis):
        metrics = _make_metrics()
        adjustments = homeostasis.diagnose(metrics)
        assert adjustments == []

    def test_borderline_healthy_no_adjustments(self, homeostasis):
        """Values just below thresholds should not trigger adjustments."""
        metrics = _make_metrics(
            tokens_per_session_avg=49999,
            error_rate_24h=0.19,
            budget_remaining_pct=0.21,  # 79% used, just below 80% warn
            task_success_rate=0.71,
            overhead_ratio=0.29,
        )
        adjustments = homeostasis.diagnose(metrics)
        assert adjustments == []


# ---------------------------------------------------------------------------
# Control loop 1: Token efficiency -> capability level
# ---------------------------------------------------------------------------


class TestTokenEfficiency:
    """High token consumption should recommend raising capability level."""

    def test_high_tokens_recommends_raise(self, homeostasis):
        metrics = _make_metrics(tokens_per_session_avg=60000, current_capability_level=3)
        adjustments = homeostasis.diagnose(metrics)
        cap_adjustments = [a for a in adjustments if a.system == "capability_level" and a.action == "raise"]
        assert len(cap_adjustments) == 1
        assert cap_adjustments[0].recommended_value == "4"
        assert cap_adjustments[0].auto_apply is False

    def test_high_tokens_at_max_level_no_raise(self, homeostasis):
        """At level 5, cannot raise further."""
        metrics = _make_metrics(tokens_per_session_avg=60000, current_capability_level=5)
        adjustments = homeostasis.diagnose(metrics)
        cap_adjustments = [a for a in adjustments if a.system == "capability_level" and a.action == "raise"]
        assert len(cap_adjustments) == 0

    def test_normal_tokens_no_raise(self, homeostasis):
        metrics = _make_metrics(tokens_per_session_avg=30000)
        adjustments = homeostasis.diagnose(metrics)
        cap_adjustments = [a for a in adjustments if a.system == "capability_level" and a.action == "raise"]
        assert len(cap_adjustments) == 0


# ---------------------------------------------------------------------------
# Control loop 2: Error rate -> safety nets
# ---------------------------------------------------------------------------


class TestErrorRate:
    """High error rate should recommend lowering capability level."""

    def test_high_error_rate_recommends_lower(self, homeostasis):
        metrics = _make_metrics(error_rate_24h=0.25, current_capability_level=4)
        adjustments = homeostasis.diagnose(metrics)
        cap_adjustments = [a for a in adjustments if a.system == "capability_level" and a.action == "lower"]
        assert len(cap_adjustments) == 1
        assert cap_adjustments[0].recommended_value == "3"
        assert cap_adjustments[0].auto_apply is False

    def test_high_error_rate_at_level_1_no_lower(self, homeostasis):
        """At level 1, cannot lower further."""
        metrics = _make_metrics(error_rate_24h=0.30, current_capability_level=1)
        adjustments = homeostasis.diagnose(metrics)
        cap_adjustments = [a for a in adjustments if a.system == "capability_level" and a.action == "lower"]
        assert len(cap_adjustments) == 0

    def test_normal_error_rate_no_lower(self, homeostasis):
        metrics = _make_metrics(error_rate_24h=0.05)
        adjustments = homeostasis.diagnose(metrics)
        cap_adjustments = [a for a in adjustments if a.system == "capability_level" and a.action == "lower"]
        assert len(cap_adjustments) == 0


# ---------------------------------------------------------------------------
# Control loop 3: Cost -> model routing
# ---------------------------------------------------------------------------


class TestBudgetPressure:
    """Budget pressure should recommend model downgrade, auto-applied."""

    def test_critical_budget_recommends_haiku(self, homeostasis):
        metrics = _make_metrics(budget_remaining_pct=0.03)  # 97% used
        adjustments = homeostasis.diagnose(metrics)
        routing = [a for a in adjustments if a.system == "model_routing"]
        assert len(routing) == 1
        assert "haiku" in routing[0].recommended_value
        assert routing[0].auto_apply is True

    def test_warn_budget_recommends_sonnet(self, homeostasis):
        metrics = _make_metrics(budget_remaining_pct=0.15)  # 85% used
        adjustments = homeostasis.diagnose(metrics)
        routing = [a for a in adjustments if a.system == "model_routing"]
        assert len(routing) == 1
        assert "sonnet" in routing[0].recommended_value
        assert routing[0].auto_apply is True

    def test_healthy_budget_no_downgrade(self, homeostasis):
        metrics = _make_metrics(budget_remaining_pct=0.50)  # 50% used
        adjustments = homeostasis.diagnose(metrics)
        routing = [a for a in adjustments if a.system == "model_routing"]
        assert len(routing) == 0


# ---------------------------------------------------------------------------
# Control loop 4: Task success -> self-improvement
# ---------------------------------------------------------------------------


class TestTaskSuccess:
    """Low task success rate should recommend self-improvement."""

    def test_low_success_recommends_self_improve(self, homeostasis):
        metrics = _make_metrics(task_success_rate=0.60)
        adjustments = homeostasis.diagnose(metrics)
        si = [a for a in adjustments if a.system == "self_improvement"]
        assert len(si) == 1
        assert si[0].action == "trigger"
        assert si[0].auto_apply is False

    def test_healthy_success_no_trigger(self, homeostasis):
        metrics = _make_metrics(task_success_rate=0.85)
        adjustments = homeostasis.diagnose(metrics)
        si = [a for a in adjustments if a.system == "self_improvement"]
        assert len(si) == 0


# ---------------------------------------------------------------------------
# Control loop 5: Overhead ratio -> symbiosis
# ---------------------------------------------------------------------------


class TestOverheadRatio:
    """High overhead ratio should trigger symbiosis alert."""

    def test_parasitic_overhead_triggers_alert(self, homeostasis):
        metrics = _make_metrics(overhead_ratio=0.35)
        adjustments = homeostasis.diagnose(metrics)
        sym = [a for a in adjustments if a.system == "symbiosis"]
        assert len(sym) == 1
        assert sym[0].action == "alert"
        assert sym[0].auto_apply is False

    def test_healthy_overhead_no_alert(self, homeostasis):
        metrics = _make_metrics(overhead_ratio=0.05)
        adjustments = homeostasis.diagnose(metrics)
        sym = [a for a in adjustments if a.system == "symbiosis"]
        assert len(sym) == 0


# ---------------------------------------------------------------------------
# apply_safe_adjustments
# ---------------------------------------------------------------------------


class TestApplySafe:
    """Only auto_apply=True adjustments should be applied."""

    def test_auto_apply_separated_from_manual(self, homeostasis):
        adjustments = [
            Adjustment("model_routing", "downgrade", "budget", "opus", "sonnet", True),
            Adjustment("capability_level", "lower", "errors", "4", "3", False),
            Adjustment("model_routing", "downgrade", "budget2", "sonnet", "haiku", True),
        ]
        applied = homeostasis.apply_safe_adjustments(adjustments)
        assert len(applied) == 2
        assert all("AUTO-APPLIED" in a for a in applied)

    def test_no_auto_adjustments_returns_empty(self, homeostasis):
        adjustments = [
            Adjustment("capability_level", "raise", "tokens", "3", "4", False),
        ]
        applied = homeostasis.apply_safe_adjustments(adjustments)
        assert applied == []

    def test_model_downgrade_writes_flag_file(self, project_dir, homeostasis):
        adjustments = [
            Adjustment("model_routing", "downgrade", "budget critical", "opus", "haiku", True),
        ]
        homeostasis.apply_safe_adjustments(adjustments)
        flag = project_dir / ".cognitive-os" / "metrics" / "model-downgrade-active.json"
        assert flag.exists()
        data = json.loads(flag.read_text())
        assert "reason" in data


# ---------------------------------------------------------------------------
# format_health_report
# ---------------------------------------------------------------------------


class TestHealthReport:
    """The health report should be readable and contain key metrics."""

    def test_healthy_report_contains_key_elements(self, homeostasis):
        metrics = _make_metrics()
        report = homeostasis.format_health_report(metrics, [])
        assert "HOMEOSTASIS REPORT" in report
        assert "Tokens/session" in report
        assert "Error rate" in report
        assert "Budget used today" in report
        assert "Task success rate" in report
        assert "Overhead ratio" in report
        assert "Capability level: 3 (excellent)" in report
        assert "Phase: reconstruction" in report
        assert "None needed. Organism is healthy." in report

    def test_report_with_adjustments(self, homeostasis):
        metrics = _make_metrics(error_rate_24h=0.25, current_capability_level=4)
        adjustments = homeostasis.diagnose(metrics)
        report = homeostasis.format_health_report(metrics, adjustments)
        assert "ADJUSTMENTS:" in report
        assert "[MANUAL]" in report
        assert "capability_level" in report

    def test_report_shows_auto_tag(self, homeostasis):
        metrics = _make_metrics(budget_remaining_pct=0.03)
        adjustments = homeostasis.diagnose(metrics)
        report = homeostasis.format_health_report(metrics, adjustments)
        assert "[AUTO]" in report

    def test_critical_status_indicator(self):
        indicator = Homeostasis._status_indicator(0.95, 0.20, higher_is_worse=True)
        assert "CRITICAL" in indicator

    def test_healthy_status_indicator(self):
        indicator = Homeostasis._status_indicator(0.02, 0.20, higher_is_worse=True)
        assert "HEALTHY" in indicator

    def test_low_success_indicator(self):
        indicator = Homeostasis._status_indicator(0.50, 0.70, higher_is_worse=False)
        assert "CRITICAL" in indicator


# ---------------------------------------------------------------------------
# collect_metrics with actual files
# ---------------------------------------------------------------------------


class TestCollectMetrics:
    """Test metric collection from actual JSONL files."""

    def test_empty_project_returns_healthy_defaults(self, homeostasis):
        """No metrics files = assume healthy."""
        metrics = homeostasis.collect_metrics()
        assert metrics.tokens_per_session_avg == 0.0
        assert metrics.error_rate_24h == 0.0
        assert metrics.cost_today_usd == 0.0
        assert metrics.task_success_rate == 1.0
        assert metrics.overhead_ratio == 0.0
        assert metrics.current_capability_level == 3
        assert metrics.current_phase == "reconstruction"

    def test_reads_cost_events(self, project_dir, homeostasis):
        cost_file = project_dir / ".cognitive-os" / "metrics" / "cost-events.jsonl"
        now = time.time()
        entries = [
            {"timestamp_epoch": now, "estimated_cost_usd": 1.50},
            {"timestamp_epoch": now - 100, "estimated_cost_usd": 2.00},
        ]
        cost_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        metrics = homeostasis.collect_metrics()
        assert metrics.cost_today_usd == 3.50

    def test_reads_error_rate(self, project_dir, homeostasis):
        error_file = project_dir / ".cognitive-os" / "metrics" / "error-learning.jsonl"
        skill_file = project_dir / ".cognitive-os" / "metrics" / "skill-metrics.jsonl"
        now = time.time()

        # 2 errors, 10 tasks = 20% error rate
        errors = [{"timestamp_epoch": now, "type": "TEST_FAILURE"} for _ in range(2)]
        tasks = [{"timestamp_epoch": now, "success": True} for _ in range(8)]
        tasks += [{"timestamp_epoch": now, "success": False} for _ in range(2)]

        error_file.write_text("\n".join(json.dumps(e) for e in errors) + "\n")
        skill_file.write_text("\n".join(json.dumps(e) for e in tasks) + "\n")

        metrics = homeostasis.collect_metrics()
        assert abs(metrics.error_rate_24h - 0.20) < 0.01
        assert abs(metrics.task_success_rate - 0.80) < 0.01

    def test_reads_config_values(self, project_dir, homeostasis):
        metrics = homeostasis.collect_metrics()
        assert metrics.current_capability_level == 3
        assert metrics.current_phase == "reconstruction"
        # Budget: $0 cost out of $10 = 100% remaining
        assert metrics.budget_remaining_pct == 1.0


# ---------------------------------------------------------------------------
# log_health_check
# ---------------------------------------------------------------------------


class TestLogHealthCheck:
    """Verify logging to homeostasis.jsonl."""

    def test_creates_log_entry(self, project_dir, homeostasis):
        metrics = _make_metrics()
        adjustments = [
            Adjustment("model_routing", "downgrade", "test", "opus", "haiku", True)
        ]
        homeostasis.log_health_check(metrics, adjustments)

        log_path = project_dir / ".cognitive-os" / "metrics" / "homeostasis.jsonl"
        assert log_path.exists()
        data = json.loads(log_path.read_text().strip())
        assert data["adjustments_count"] == 1
        assert data["capability_level"] == 3
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# Full run cycle
# ---------------------------------------------------------------------------


class TestFullCycle:
    """Test the convenience run() method."""

    def test_run_returns_tuple(self, homeostasis):
        metrics, adjustments, applied = homeostasis.run()
        assert isinstance(metrics, HealthMetrics)
        assert isinstance(adjustments, list)
        assert isinstance(applied, list)

    def test_run_with_sick_organism(self, project_dir):
        """An organism with multiple issues should produce multiple adjustments."""
        # Write config with high capability level
        config = project_dir / "cognitive-os.yaml"
        config.write_text(
            "project:\n"
            "  name: sick-project\n"
            "  phase: production\n"
            "\n"
            "model_capability:\n"
            "  level: 4\n"
            "\n"
            "resources:\n"
            "  budget:\n"
            "    daily_alert_usd: 10\n"
        )

        # Write metrics showing problems
        metrics_dir = project_dir / ".cognitive-os" / "metrics"
        now = time.time()

        # High cost (>95% budget)
        cost_file = metrics_dir / "cost-events.jsonl"
        cost_entries = [
            {"timestamp_epoch": now, "estimated_cost_usd": 4.80, "input_tokens": 100000, "output_tokens": 50000},
            {"timestamp_epoch": now - 100, "estimated_cost_usd": 4.90, "input_tokens": 100000, "output_tokens": 50000},
        ]
        cost_file.write_text("\n".join(json.dumps(e) for e in cost_entries) + "\n")

        # High error rate
        error_file = metrics_dir / "error-learning.jsonl"
        errors = [{"timestamp_epoch": now, "type": "BUILD_ERROR"} for _ in range(5)]
        error_file.write_text("\n".join(json.dumps(e) for e in errors) + "\n")

        # Low success rate
        skill_file = metrics_dir / "skill-metrics.jsonl"
        tasks = [{"timestamp_epoch": now, "success": False} for _ in range(7)]
        tasks += [{"timestamp_epoch": now, "success": True} for _ in range(3)]
        skill_file.write_text("\n".join(json.dumps(e) for e in tasks) + "\n")

        h = Homeostasis(str(project_dir))
        metrics, adjustments, applied = h.run()

        # Should have multiple adjustments
        systems = {a.system for a in adjustments}
        assert "model_routing" in systems  # budget critical
        assert "capability_level" in systems  # high error rate -> lower
        assert "self_improvement" in systems  # low success rate

        # Model routing should be auto-applied
        assert len(applied) >= 1
        assert any("model_routing" in a for a in applied)

        # Log file should exist
        log_path = metrics_dir / "homeostasis.jsonl"
        assert log_path.exists()


# ---------------------------------------------------------------------------
# Multiple simultaneous conditions
# ---------------------------------------------------------------------------


class TestMultipleConditions:
    """Test that multiple control loops fire independently."""

    def test_high_tokens_and_high_errors_produce_conflicting_adjustments(self, homeostasis):
        """High tokens wants to raise level, high errors wants to lower it.
        Both should appear -- the human resolves the conflict."""
        metrics = _make_metrics(
            tokens_per_session_avg=60000,
            error_rate_24h=0.25,
            current_capability_level=3,
        )
        adjustments = homeostasis.diagnose(metrics)
        actions = {(a.system, a.action) for a in adjustments}
        assert ("capability_level", "raise") in actions
        assert ("capability_level", "lower") in actions
