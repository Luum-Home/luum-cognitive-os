"""Unit tests for Claude usage reader."""
import json

import pytest

from lib.claude_usage_reader import (
    calculate_cost,
    format_reconciliation_report,
    read_session_file,
    reconcile_costs,
    summarize_usage,
)

pytestmark = pytest.mark.unit


class TestReadSessionFile:
    def test_reads_valid_jsonl(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text(
            json.dumps(
                {"input_tokens": 100, "output_tokens": 50, "model": "claude-sonnet-4"}
            )
            + "\n"
        )
        entries = read_session_file(f)
        assert len(entries) == 1
        assert entries[0]["input_tokens"] == 100

    def test_skips_non_usage_lines(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text(
            '{"type": "message", "content": "hello"}\n{"input_tokens": 100}\n'
        )
        entries = read_session_file(f)
        assert len(entries) == 1

    def test_handles_malformed_json(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text('not json\n{"input_tokens": 100}\n')
        entries = read_session_file(f)
        assert len(entries) == 1

    def test_handles_missing_file(self, tmp_path):
        entries = read_session_file(tmp_path / "nonexistent.jsonl")
        assert entries == []


class TestCalculateCost:
    def test_sonnet_pricing(self):
        entry = {
            "model": "claude-sonnet-4",
            "input_tokens": 1000000,
            "output_tokens": 0,
        }
        assert calculate_cost(entry) == 3.0

    def test_opus_pricing(self):
        entry = {
            "model": "claude-opus-4-6",
            "input_tokens": 0,
            "output_tokens": 1000000,
        }
        assert calculate_cost(entry) == 75.0

    def test_unknown_model_uses_cost_usd(self):
        entry = {"model": "unknown", "cost_usd": 1.5}
        assert calculate_cost(entry) == 1.5


class TestSummarizeUsage:
    def test_summarizes_entries(self):
        entries = [
            {"input_tokens": 100, "output_tokens": 50, "model": "claude-sonnet-4"},
            {"input_tokens": 200, "output_tokens": 100, "model": "claude-sonnet-4"},
        ]
        summary = summarize_usage(entries)
        assert summary["total_entries"] == 2
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 150


class TestReconcileCosts:
    def test_reconciliation(self, tmp_path):
        cost_file = tmp_path / "cost-events.jsonl"
        cost_file.write_text(json.dumps({"estimated_cost_usd": 0.05}) + "\n")
        entries = [
            {"input_tokens": 10000, "output_tokens": 5000, "model": "claude-sonnet-4"}
        ]
        report = reconcile_costs(entries, str(cost_file))
        assert "ground_truth_cost_usd" in report
        assert "tracked_cost_usd" in report
        assert "discrepancy_pct" in report

    def test_missing_cost_file(self, tmp_path):
        entries = [
            {"input_tokens": 1000, "output_tokens": 500, "model": "claude-sonnet-4"}
        ]
        report = reconcile_costs(entries, str(tmp_path / "nonexistent.jsonl"))
        assert report["tracked_cost_usd"] == 0.0


class TestFormatReport:
    def test_format_includes_key_fields(self):
        report = {
            "ground_truth_cost_usd": 1.5,
            "tracked_cost_usd": 1.3,
            "discrepancy_usd": 0.2,
            "discrepancy_pct": 13.3,
            "entries_analyzed": 42,
            "models_used": ["claude-sonnet-4"],
        }
        output = format_reconciliation_report(report)
        assert "COST RECONCILIATION" in output
        assert "WARNING" in output  # >10% discrepancy
