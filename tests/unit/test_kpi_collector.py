"""Unit tests for lib/kpi_collector.py

Validates KPI collection from JSONL metric files: trust scores,
skill metrics, error learning, escalation events, hallucinations,
dashboard formatting, and edge cases (empty/missing files).

Python 3.9+ compatible.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from lib.kpi_collector import (
    _read_jsonl,
    collect_session_kpis,
    format_kpi_dashboard,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, entries: List[Dict[str, Any]]) -> None:
    """Write a list of dicts to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def metrics_dir(tmp_path: Path) -> Path:
    """Return a temporary metrics directory."""
    d = tmp_path / "metrics"
    d.mkdir()
    return d


@pytest.fixture()
def populated_metrics_dir(metrics_dir: Path) -> Path:
    """Return a metrics directory pre-populated with sample data."""
    # Trust scores
    _write_jsonl(metrics_dir / "trust-scores.jsonl", [
        {"score": 85, "uncertainties_count": 2, "timestamp": "2026-03-27T12:00:00Z"},
        {"score": 90, "uncertainties_count": 1, "timestamp": "2026-03-27T12:01:00Z"},
        {"score": 75, "uncertainties_count": 0, "timestamp": "2026-03-27T12:02:00Z"},
    ])

    # Skill metrics
    _write_jsonl(metrics_dir / "skill-metrics.jsonl", [
        {"skill": "sdd-apply", "success": True, "timestamp": "2026-03-27T12:00:00Z"},
        {"skill": "sdd-verify", "success": True, "timestamp": "2026-03-27T12:01:00Z"},
        {"skill": "sdd-apply", "success": False, "timestamp": "2026-03-27T12:02:00Z"},
        {"skill": "sdd-apply", "success": True, "timestamp": "2026-03-27T12:03:00Z"},
    ])

    # Error learning
    _write_jsonl(metrics_dir / "error-learning.jsonl", [
        {"type": "TEST_FAILURE", "service": "api", "timestamp": "2026-03-27T12:00:00Z"},
        {"type": "TEST_FAILURE", "service": "api", "timestamp": "2026-03-27T12:01:00Z"},
        {"type": "TEST_FAILURE", "service": "api", "timestamp": "2026-03-27T12:02:00Z"},
        {"type": "BUILD_ERROR", "service": "web", "timestamp": "2026-03-27T12:03:00Z"},
    ])

    # Escalation events
    _write_jsonl(metrics_dir / "escalation-events.jsonl", [
        {"escalation_count": 1, "tool_calls_total": 15, "timestamp": "2026-03-27T12:00:00Z"},
    ])

    # Hallucinations
    _write_jsonl(metrics_dir / "hallucinations.jsonl", [
        {"hallucinations": 0, "verified": 5, "timestamp": "2026-03-27T12:00:00Z"},
        {"hallucinations": 1, "verified": 3, "timestamp": "2026-03-27T12:01:00Z"},
    ])

    return metrics_dir


# ---------------------------------------------------------------------------
# Tests: _read_jsonl
# ---------------------------------------------------------------------------


class TestReadJsonl:
    """Test the JSONL reader helper."""

    def test_reads_valid_jsonl(self, metrics_dir: Path) -> None:
        path = metrics_dir / "test.jsonl"
        _write_jsonl(path, [{"a": 1}, {"b": 2}])
        result = _read_jsonl(path)
        assert len(result) == 2
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}

    def test_returns_empty_for_missing_file(self, metrics_dir: Path) -> None:
        result = _read_jsonl(metrics_dir / "nonexistent.jsonl")
        assert result == []

    def test_skips_malformed_lines(self, metrics_dir: Path) -> None:
        path = metrics_dir / "mixed.jsonl"
        path.write_text('{"valid": true}\nnot json\n{"also_valid": true}\n')
        result = _read_jsonl(path)
        assert len(result) == 2

    def test_skips_blank_lines(self, metrics_dir: Path) -> None:
        path = metrics_dir / "blanks.jsonl"
        path.write_text('{"a": 1}\n\n\n{"b": 2}\n')
        result = _read_jsonl(path)
        assert len(result) == 2

    def test_empty_file(self, metrics_dir: Path) -> None:
        path = metrics_dir / "empty.jsonl"
        path.write_text("")
        result = _read_jsonl(path)
        assert result == []


# ---------------------------------------------------------------------------
# Tests: collect_session_kpis -- empty metrics
# ---------------------------------------------------------------------------


class TestCollectEmpty:
    """Test KPI collection when no metric files exist."""

    def test_empty_directory_returns_defaults(self, metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(metrics_dir))

        assert kpis["trust"]["avg_trust_score"] == 0.0
        assert kpis["trust"]["trust_score_count"] == 0
        assert kpis["skills"]["total_executions"] == 0
        assert kpis["skills"]["first_attempt_success_rate"] == 0.0
        assert kpis["errors"]["total_errors"] == 0
        assert kpis["errors"]["recurrence_count"] == 0
        assert kpis["escalations"]["escalation_count"] == 0
        assert kpis["escalations"]["escalation_rate"] == 0.0
        assert kpis["hallucinations"]["total_checks"] == 0
        assert kpis["cost"]["total_usd"] == 0.0

    def test_has_timestamp(self, metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(metrics_dir))
        assert "timestamp" in kpis

    def test_quality_behind_when_empty(self, metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["quality"]["status"] == "BEHIND"


# ---------------------------------------------------------------------------
# Tests: collect_session_kpis -- populated metrics
# ---------------------------------------------------------------------------


class TestCollectPopulated:
    """Test KPI collection with real metric data."""

    def test_trust_score_average(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        # (85 + 90 + 75) / 3 = 83.33
        assert kpis["trust"]["avg_trust_score"] == pytest.approx(83.3, abs=0.1)
        assert kpis["trust"]["trust_score_count"] == 3

    def test_self_awareness_rate(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        # 2 out of 3 have uncertainties > 0 = 66.7%
        assert kpis["trust"]["self_awareness_rate"] == pytest.approx(66.7, abs=0.1)

    def test_skill_metrics(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        assert kpis["skills"]["total_executions"] == 4
        assert kpis["skills"]["successful_executions"] == 3
        assert kpis["skills"]["first_attempt_success_rate"] == 75.0

    def test_error_recurrence(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        assert kpis["errors"]["total_errors"] == 4
        # TEST_FAILURE appears 3 times -> 1 recurring type
        assert kpis["errors"]["recurrence_count"] == 1
        assert kpis["errors"]["error_types"]["TEST_FAILURE"] == 3
        assert kpis["errors"]["error_types"]["BUILD_ERROR"] == 1

    def test_escalation_rate(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        # 1 escalation / 4 skill executions = 25%
        assert kpis["escalations"]["escalation_count"] == 1
        assert kpis["escalations"]["escalation_rate"] == 25.0
        assert kpis["escalations"]["escalation_rate_status"] == "HIGH"

    def test_hallucination_kpis(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        assert kpis["hallucinations"]["total_checks"] == 2
        assert kpis["hallucinations"]["total_hallucinations"] == 1
        assert kpis["hallucinations"]["total_verified"] == 8
        # 1/(1+8) = 11.1%
        assert kpis["hallucinations"]["hallucination_rate"] == pytest.approx(
            11.1, abs=0.1
        )

    def test_quality_uses_trust_score_when_available(
        self, populated_metrics_dir: Path
    ) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        # Trust score available -> quality = avg trust = 83.3
        assert kpis["quality"]["composite_score"] == pytest.approx(83.3, abs=0.1)
        assert kpis["quality"]["status"] == "AT_RISK"


# ---------------------------------------------------------------------------
# Tests: collect_session_kpis -- quality status thresholds
# ---------------------------------------------------------------------------


class TestQualityStatus:
    """Test quality status classification at boundary values."""

    def test_on_track_at_90(self, metrics_dir: Path) -> None:
        _write_jsonl(metrics_dir / "trust-scores.jsonl", [
            {"score": 90, "uncertainties_count": 1},
            {"score": 92, "uncertainties_count": 1},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["quality"]["status"] == "ON_TRACK"

    def test_at_risk_at_80(self, metrics_dir: Path) -> None:
        _write_jsonl(metrics_dir / "trust-scores.jsonl", [
            {"score": 80, "uncertainties_count": 1},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["quality"]["status"] == "AT_RISK"

    def test_behind_below_75(self, metrics_dir: Path) -> None:
        _write_jsonl(metrics_dir / "trust-scores.jsonl", [
            {"score": 50, "uncertainties_count": 0},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["quality"]["status"] == "BEHIND"

    def test_falls_back_to_success_rate_without_trust(
        self, metrics_dir: Path
    ) -> None:
        """When no trust scores exist, uses first_attempt_success_rate."""
        _write_jsonl(metrics_dir / "skill-metrics.jsonl", [
            {"skill": "a", "success": True},
            {"skill": "b", "success": True},
            {"skill": "c", "success": True},
            {"skill": "d", "success": True},
            {"skill": "e", "success": False},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        # 4/5 = 80% success rate
        assert kpis["quality"]["composite_score"] == 80.0
        assert kpis["quality"]["status"] == "AT_RISK"


# ---------------------------------------------------------------------------
# Tests: escalation rate status boundaries
# ---------------------------------------------------------------------------


class TestEscalationRateStatus:
    """Test escalation rate classification."""

    def test_low_rate(self, metrics_dir: Path) -> None:
        """< 5% escalation rate is LOW."""
        _write_jsonl(metrics_dir / "skill-metrics.jsonl", [
            {"skill": f"s{i}", "success": True} for i in range(100)
        ])
        _write_jsonl(metrics_dir / "escalation-events.jsonl", [
            {"escalation_count": 1, "timestamp": "2026-03-27T12:00:00Z"},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["escalations"]["escalation_rate"] == 1.0
        assert kpis["escalations"]["escalation_rate_status"] == "LOW"

    def test_healthy_rate(self, metrics_dir: Path) -> None:
        """5-15% escalation rate is HEALTHY."""
        _write_jsonl(metrics_dir / "skill-metrics.jsonl", [
            {"skill": f"s{i}", "success": True} for i in range(10)
        ])
        _write_jsonl(metrics_dir / "escalation-events.jsonl", [
            {"escalation_count": 1, "timestamp": f"2026-03-27T12:0{i}:00Z"}
            for i in range(1)
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        # 1/10 = 10%
        assert kpis["escalations"]["escalation_rate"] == 10.0
        assert kpis["escalations"]["escalation_rate_status"] == "HEALTHY"

    def test_high_rate(self, metrics_dir: Path) -> None:
        """> 15% escalation rate is HIGH."""
        _write_jsonl(metrics_dir / "skill-metrics.jsonl", [
            {"skill": f"s{i}", "success": True} for i in range(5)
        ])
        _write_jsonl(metrics_dir / "escalation-events.jsonl", [
            {"escalation_count": 1, "timestamp": f"2026-03-27T12:0{i}:00Z"}
            for i in range(2)
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        # 2/5 = 40%
        assert kpis["escalations"]["escalation_rate"] == 40.0
        assert kpis["escalations"]["escalation_rate_status"] == "HIGH"


# ---------------------------------------------------------------------------
# Tests: format_kpi_dashboard
# ---------------------------------------------------------------------------


class TestFormatDashboard:
    """Test dashboard formatting."""

    def test_dashboard_has_header(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        dashboard = format_kpi_dashboard(kpis)
        assert "AGENT KPI DASHBOARD" in dashboard

    def test_dashboard_has_all_sections(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        dashboard = format_kpi_dashboard(kpis)
        assert "QUALITY:" in dashboard
        assert "TRUST SCORES:" in dashboard
        assert "SKILL EXECUTION:" in dashboard
        assert "ERRORS:" in dashboard
        assert "ESCALATIONS:" in dashboard
        assert "HALLUCINATIONS:" in dashboard
        assert "COST:" in dashboard

    def test_dashboard_includes_values(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        dashboard = format_kpi_dashboard(kpis)
        # Check that actual numbers appear
        assert "83.3%" in dashboard  # avg trust
        assert "75.0%" in dashboard  # success rate
        assert "TEST_FAILURE: 3" in dashboard

    def test_empty_dashboard(self, metrics_dir: Path) -> None:
        """Dashboard should render cleanly with no data."""
        kpis = collect_session_kpis(str(metrics_dir))
        dashboard = format_kpi_dashboard(kpis)
        assert "AGENT KPI DASHBOARD" in dashboard
        assert "0.0%" in dashboard

    def test_dashboard_returns_string(self, populated_metrics_dir: Path) -> None:
        kpis = collect_session_kpis(str(populated_metrics_dir))
        dashboard = format_kpi_dashboard(kpis)
        assert isinstance(dashboard, str)
        assert len(dashboard) > 100  # Non-trivial output


# ---------------------------------------------------------------------------
# Tests: partial data (some files missing)
# ---------------------------------------------------------------------------


class TestPartialData:
    """Test behavior when only some metric files exist."""

    def test_only_skill_metrics(self, metrics_dir: Path) -> None:
        _write_jsonl(metrics_dir / "skill-metrics.jsonl", [
            {"skill": "a", "success": True},
            {"skill": "b", "success": False},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["skills"]["total_executions"] == 2
        assert kpis["trust"]["trust_score_count"] == 0
        assert kpis["errors"]["total_errors"] == 0

    def test_only_trust_scores(self, metrics_dir: Path) -> None:
        _write_jsonl(metrics_dir / "trust-scores.jsonl", [
            {"score": 95, "uncertainties_count": 2},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["trust"]["avg_trust_score"] == 95.0
        assert kpis["skills"]["total_executions"] == 0

    def test_only_errors(self, metrics_dir: Path) -> None:
        _write_jsonl(metrics_dir / "error-learning.jsonl", [
            {"type": "LINT_ERROR", "service": "web"},
        ])
        kpis = collect_session_kpis(str(metrics_dir))
        assert kpis["errors"]["total_errors"] == 1
        assert kpis["errors"]["recurrence_count"] == 0


# ---------------------------------------------------------------------------
# Tests: real metric files from .cognitive-os/metrics/
# ---------------------------------------------------------------------------


class TestRealMetrics:
    """Test collection against the actual project metric files if they exist."""

    @pytest.fixture()
    def real_metrics_dir(self, project_root: Path) -> Path:
        """Return the real .cognitive-os/metrics/ directory."""
        return project_root / ".cognitive-os" / "metrics"

    def test_can_read_real_skill_metrics(self, real_metrics_dir: Path) -> None:
        """Smoke test: if the real skill-metrics.jsonl exists, we can read it."""
        path = real_metrics_dir / "skill-metrics.jsonl"
        if not path.exists():
            pytest.skip("No real skill-metrics.jsonl found")
        entries = _read_jsonl(path)
        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_collect_from_real_dir(self, real_metrics_dir: Path) -> None:
        """Smoke test: collect_session_kpis works on real metrics directory."""
        if not real_metrics_dir.exists():
            pytest.skip("No .cognitive-os/metrics/ directory found")
        kpis = collect_session_kpis(str(real_metrics_dir))
        assert "trust" in kpis
        assert "skills" in kpis
        assert "errors" in kpis
        assert "quality" in kpis
