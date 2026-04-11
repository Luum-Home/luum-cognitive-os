"""Unit tests for lib/repetition_detector.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lib.repetition_detector import RepetitionDetector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write_metrics(tmp_path: Path, entries: list[dict]) -> RepetitionDetector:
    """Write entries to a temp skill-metrics.jsonl and return a detector."""
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    out = metrics_dir / "skill-metrics.jsonl"
    out.write_text(
        "\n".join(json.dumps(e) for e in entries), encoding="utf-8"
    )
    return RepetitionDetector(str(metrics_dir))


REPEATED_SEQUENCE = ["Grep", "Read", "Edit", "Bash"]


def _seq_entries(n: int = 3) -> list[dict]:
    """n entries all sharing the same tool_calls sequence."""
    return [
        {
            "skill_name": f"run-{i}",
            "tool_calls": REPEATED_SEQUENCE,
            "tokens": 4000,
            "duration_ms": 1000,
            "success": True,
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDetectSimpleSequence:
    def test_detect_simple_sequence(self, tmp_path):
        det = _write_metrics(tmp_path, _seq_entries(3))
        patterns = det.analyze_tool_sequences(min_length=3, min_occurrences=3)
        assert len(patterns) >= 1
        sequences = [p["sequence"] for p in patterns]
        assert REPEATED_SEQUENCE in sequences

    def test_occurrences_counted_correctly(self, tmp_path):
        det = _write_metrics(tmp_path, _seq_entries(5))
        patterns = det.analyze_tool_sequences(min_length=4, min_occurrences=5)
        top = next(p for p in patterns if p["sequence"] == REPEATED_SEQUENCE)
        assert top["occurrences"] == 5


class TestFilters:
    def test_min_length_filter(self, tmp_path):
        """Sequences shorter than min_length must not appear."""
        det = _write_metrics(tmp_path, _seq_entries(5))
        # With min_length=5 the 4-tool sequence must be excluded
        patterns = det.analyze_tool_sequences(min_length=5, min_occurrences=3)
        sequences = [p["sequence"] for p in patterns]
        assert REPEATED_SEQUENCE not in sequences

    def test_min_occurrences_filter(self, tmp_path):
        """Sequences appearing fewer times than threshold must be excluded."""
        det = _write_metrics(tmp_path, _seq_entries(2))
        patterns = det.analyze_tool_sequences(min_length=3, min_occurrences=3)
        assert patterns == []


class TestEdgeCases:
    def test_no_patterns_empty_data(self, tmp_path):
        det = _write_metrics(tmp_path, [])
        assert det.analyze_tool_sequences() == []

    def test_no_patterns_no_repetition(self, tmp_path):
        entries = [
            {"skill_name": f"sk-{i}", "tool_calls": ["Grep", f"tool-{i}"], "tokens": 1000}
            for i in range(10)
        ]
        det = _write_metrics(tmp_path, entries)
        patterns = det.analyze_tool_sequences(min_occurrences=3)
        assert patterns == []

    def test_handles_missing_metrics(self, tmp_path):
        det = RepetitionDetector(str(tmp_path / "nonexistent"))
        assert det.analyze_tool_sequences() == []
        assert det.analyze_skill_chains() == []

    def test_handles_empty_metrics(self, tmp_path):
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()
        (metrics_dir / "skill-metrics.jsonl").write_text("", encoding="utf-8")
        det = RepetitionDetector(str(metrics_dir))
        assert det.analyze_tool_sequences() == []


class TestSkillChainDetection:
    def test_skill_chain_detection(self, tmp_path):
        entries = [
            {"skill_name": "detect-stack", "tool_calls": ["Read"], "tokens": 500},
            {"skill_name": "generate-config", "tool_calls": ["Write"], "tokens": 500},
            {"skill_name": "scaffold-project", "tool_calls": ["Bash"], "tokens": 500},
        ] * 4  # repeat the triplet 4 times
        det = _write_metrics(tmp_path, entries)
        chains = det.analyze_skill_chains(min_occurrences=3)
        assert len(chains) >= 1
        chain_names = [c["chain"] for c in chains]
        assert ["detect-stack", "generate-config", "scaffold-project"] in chain_names

    def test_skill_chain_suggestion_text(self, tmp_path):
        entries = [
            {"skill_name": "a", "tool_calls": [], "tokens": 100},
            {"skill_name": "b", "tool_calls": [], "tokens": 100},
        ] * 3
        det = _write_metrics(tmp_path, entries)
        chains = det.analyze_skill_chains(min_occurrences=3)
        for c in chains:
            assert "skill" in c["suggestion"].lower()


class TestEstimateSavings:
    def test_estimate_savings_calculation(self, tmp_path):
        det = _write_metrics(tmp_path, _seq_entries(5))
        patterns = det.analyze_tool_sequences(min_length=4, min_occurrences=5)
        savings = det.estimate_savings(patterns)
        assert savings["patterns_found"] == len(patterns)
        # avg_tokens=4000, savings_per = 4000-500=3500, occurrences=5 → 17500
        top = next(p for p in patterns if p["sequence"] == REPEATED_SEQUENCE)
        assert top["potential_savings"] == 3500 * 5

    def test_estimate_savings_empty(self, tmp_path):
        det = RepetitionDetector(str(tmp_path))
        result = det.estimate_savings([])
        assert result == {
            "patterns_found": 0,
            "total_savings_tokens": 0,
            "savings_per_month": 0,
        }

    def test_potential_savings_positive(self, tmp_path):
        det = _write_metrics(tmp_path, _seq_entries(4))
        patterns = det.analyze_tool_sequences(min_occurrences=3)
        assert all(p["potential_savings"] >= 0 for p in patterns)
        if patterns:
            assert any(p["potential_savings"] > 0 for p in patterns)


class TestFormatReport:
    def test_format_report_structure(self, tmp_path):
        det = _write_metrics(tmp_path, _seq_entries(3))
        patterns = det.analyze_tool_sequences(min_occurrences=3)
        chains = det.analyze_skill_chains(min_occurrences=3)
        report = det.format_report(patterns, chains)
        assert "# Repetition Detector Report" in report
        assert "Summary" in report
        assert "Repeated Tool Sequences" in report
        assert "Repeated Skill Chains" in report

    def test_format_report_empty(self, tmp_path):
        det = RepetitionDetector(str(tmp_path))
        report = det.format_report([], [])
        assert "(none detected)" in report


class TestSuggestSkillNames:
    def test_suggest_skill_names_basic(self, tmp_path):
        det = RepetitionDetector(str(tmp_path))
        pattern = {
            "sequence": ["Grep", "Read", "Edit"],
            "occurrences": 3,
            "example_context": "search for function",
        }
        names = det.suggest_skill_names(pattern)
        assert len(names) >= 1
        assert all(isinstance(n, str) and len(n) > 0 for n in names)

    def test_suggest_skill_names_no_context(self, tmp_path):
        det = RepetitionDetector(str(tmp_path))
        pattern = {"sequence": ["Bash", "Read"], "occurrences": 3, "example_context": ""}
        names = det.suggest_skill_names(pattern)
        assert len(names) >= 1
