"""Tests for lib/self_improvement.py — minimal self-improvement analysis."""
import json
import os
import sys
import tempfile


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from lib.self_improvement import (
    analyze_kpi_history,
    suggest_improvements,
    format_improvement_report,
)


def _write_jsonl(path: str, entries: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


class TestAnalyzeKpiHistory:
    def test_empty_metrics_dir(self):
        tmpdir = tempfile.mkdtemp()
        result = analyze_kpi_history(tmpdir)
        assert result["total_completions"] == 0
        assert result["avg_trust_score"] == 0
        assert result["success_rate"] == 0

    def test_with_consequence_data(self):
        tmpdir = tempfile.mkdtemp()
        _write_jsonl(os.path.join(tmpdir, "consequence-history.jsonl"), [
            {"trust_score": 85, "success": True, "consequence": "maintain"},
            {"trust_score": 90, "success": True, "consequence": "promote"},
            {"trust_score": 45, "success": False, "consequence": "warn"},
        ])
        result = analyze_kpi_history(tmpdir)
        assert result["total_completions"] == 3
        assert result["total_successes"] == 2
        assert result["trust_scores_are_real"] is True
        assert 70 < result["avg_trust_score"] < 80  # (85+90+45)/3 ≈ 73.3

    def test_detects_hardcoded_75_scores(self):
        tmpdir = tempfile.mkdtemp()
        _write_jsonl(os.path.join(tmpdir, "consequence-history.jsonl"), [
            {"trust_score": 75, "success": True, "consequence": "maintain"},
            {"trust_score": 75, "success": True, "consequence": "maintain"},
        ])
        result = analyze_kpi_history(tmpdir)
        assert result["trust_scores_are_real"] is False

    def test_error_recurrence(self):
        tmpdir = tempfile.mkdtemp()
        _write_jsonl(os.path.join(tmpdir, "error-learning.jsonl"), [
            {"type": "TEST_FAILURE", "service": "auth"},
            {"type": "TEST_FAILURE", "service": "auth"},
            {"type": "TEST_FAILURE", "service": "auth"},
            {"type": "BUILD_ERROR", "service": "api"},
        ])
        result = analyze_kpi_history(tmpdir)
        assert "TEST_FAILURE:auth" in result["recurring_errors"]
        assert result["recurring_errors"]["TEST_FAILURE:auth"] == 3

    def test_skill_failures(self):
        tmpdir = tempfile.mkdtemp()
        _write_jsonl(os.path.join(tmpdir, "skill-archive.jsonl"), [
            {"skill_name": "sdd-apply", "success": False},
            {"skill_name": "sdd-apply", "success": False},
            {"skill_name": "sdd-verify", "success": True},
        ])
        result = analyze_kpi_history(tmpdir)
        assert result["skill_failures"]["sdd-apply"] == 2


class TestSuggestImprovements:
    def test_detects_dead_trust_scores(self):
        analysis = {"trust_scores_are_real": False, "consequences": {"maintain": 100}}
        suggestions = suggest_improvements(analysis)
        assert any("CRITICAL" in s for s in suggestions)
        assert any("hardcoded" in s.lower() or "default" in s.lower() for s in suggestions)

    def test_low_trust_score(self):
        analysis = {"trust_scores_are_real": True, "avg_trust_score": 60, "consequences": {}}
        suggestions = suggest_improvements(analysis)
        assert any("trust score" in s.lower() for s in suggestions)

    def test_low_success_rate(self):
        analysis = {"trust_scores_are_real": True, "success_rate": 70, "consequences": {}}
        suggestions = suggest_improvements(analysis)
        assert any("success rate" in s.lower() for s in suggestions)

    def test_recurring_errors(self):
        analysis = {
            "trust_scores_are_real": True,
            "recurring_errors": {"TEST_FAILURE:auth": 5},
            "consequences": {},
        }
        suggestions = suggest_improvements(analysis)
        assert any("recurring" in s.lower() or "error" in s.lower() for s in suggestions)

    def test_healthy_returns_empty(self):
        analysis = {
            "trust_scores_are_real": True,
            "avg_trust_score": 85,
            "success_rate": 95,
            "recurring_errors": {},
            "skill_failures": {},
            "consequences": {"maintain": 50, "promote": 10},
            "total_completions": 60,
        }
        suggestions = suggest_improvements(analysis)
        assert len(suggestions) == 0

    def test_no_data(self):
        analysis = {"trust_scores_are_real": True, "total_completions": 0, "consequences": {}}
        suggestions = suggest_improvements(analysis)
        assert any("no completion data" in s.lower() for s in suggestions)


class TestFormatReport:
    def test_produces_markdown(self):
        analysis = {
            "avg_trust_score": 75,
            "trust_scores_are_real": False,
            "success_rate": 80,
            "total_completions": 100,
            "total_errors": 5,
            "recurring_errors": {},
            "consequences": {"maintain": 100},
            "data_sources": {
                "kpi_entries": 10,
                "session_entries": 20,
                "skill_entries": 30,
                "error_entries": 5,
                "consequence_entries": 100,
            },
        }
        report = format_improvement_report(analysis)
        assert "# Self-Improvement Report" in report
        assert "Data Sources" in report
        assert "Suggestions" in report

    def test_healthy_report(self):
        analysis = {
            "trust_scores_are_real": True,
            "avg_trust_score": 90,
            "success_rate": 95,
            "total_completions": 50,
            "total_errors": 0,
            "recurring_errors": {},
            "skill_failures": {},
            "consequences": {"maintain": 40, "promote": 10},
            "data_sources": {"kpi_entries": 0, "session_entries": 0,
                           "skill_entries": 0, "error_entries": 0,
                           "consequence_entries": 50},
        }
        report = format_improvement_report(analysis)
        assert "Healthy" in report
