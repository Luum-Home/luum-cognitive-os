"""Unit tests for lib/repetition_detector.py."""

from __future__ import annotations

import json
from pathlib import Path


from cos_lib.repetition_detector import RepetitionDetector


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
            "skill": f"run-{i}",
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
            {"skill": f"sk-{i}", "tool_calls": ["Grep", f"tool-{i}"], "tokens": 1000}
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
            {"skill": "detect-stack", "tool_calls": ["Read"], "tokens": 500},
            {"skill": "generate-config", "tool_calls": ["Write"], "tokens": 500},
            {"skill": "scaffold-project", "tool_calls": ["Bash"], "tokens": 500},
        ] * 4  # repeat the triplet 4 times
        det = _write_metrics(tmp_path, entries)
        chains = det.analyze_skill_chains(min_occurrences=3)
        assert len(chains) >= 1
        chain_names = [c["chain"] for c in chains]
        assert ["detect-stack", "generate-config", "scaffold-project"] in chain_names

    def test_skill_chain_suggestion_text(self, tmp_path):
        entries = [
            {"skill": "a", "tool_calls": [], "tokens": 100},
            {"skill": "b", "tool_calls": [], "tokens": 100},
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
        """Sin corpus, "(none detected)" seria mentira: no se busco nada.

        Antes este test fijaba esa frase sobre un directorio vacio. Es el caso
        exacto que el arreglo del 2026-08-19 separa: cero-por-ausencia-de-fuente
        no es cero-por-ausencia-de-hallazgos.
        """
        det = RepetitionDetector(str(tmp_path))
        report = det.format_report([], [])
        assert "NO DATA SOURCE" in report
        assert "(none detected)" not in report


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


# ── A zero that is not emitted is a hole, not a zero ─────────────────────────
# Measured 2026-08-19: this module read `skill_name` and `tool_calls`; the
# producer writes `skill` and nothing in the repo writes `tool_calls` at all.
# Both analyses returned [] on all 257 rows and format_report printed
# "(none detected)", which reads as "we looked and found nothing". Falco ships
# `include_empty_values: false` by default and thereby manufactures the same
# blindness; Gatekeeper truncates the detail but never the counter. These tests
# pin the distinction in both directions.

def _write(tmp_path, rows):
    d = tmp_path / ".cognitive-os" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    (d / "skill-metrics.jsonl").write_text(
        "\n".join(__import__("json").dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    return str(d)


def test_absent_field_reports_no_source_not_an_empty_result(tmp_path):
    """The real corpus shape: rows exist, `tool_calls` never does."""
    from cos_lib.repetition_detector import RepetitionDetector

    det = RepetitionDetector(_write(tmp_path, [
        {"skill": "unknown-agent", "tokens": 900, "success": True},
        {"skill": "unknown-agent", "tokens": 800, "success": True},
    ]))
    st = det.source_status()
    assert st["rows"] == 2
    assert st["sequences_measurable"] is False
    assert st["chains_measurable"] is False, "the sentinel is not a skill name"

    report = det.format_report(det.analyze_tool_sequences(), det.analyze_skill_chains())
    assert "NO DATA SOURCE" in report
    assert "(none detected)" not in report


def test_present_field_with_no_match_still_reports_none_detected(tmp_path):
    """Null control: with a real source and nothing repeated, zero IS a zero.

    Without this the fix would pass just as well if it printed NO DATA SOURCE
    unconditionally, which would trade one false statement for another.
    """
    from cos_lib.repetition_detector import RepetitionDetector

    det = RepetitionDetector(_write(tmp_path, [
        {"skill": "run-tests", "tool_calls": ["Read"], "tokens": 900, "success": True},
    ]))
    st = det.source_status()
    assert st["sequences_measurable"] is True
    assert st["chains_measurable"] is True

    report = det.format_report(det.analyze_tool_sequences(), det.analyze_skill_chains())
    assert "(none detected)" in report
    assert "NO DATA SOURCE" not in report


def test_reads_the_field_the_producer_actually_writes(tmp_path):
    """`skill`, not `skill_name` -- the rename that made this module blind."""
    from cos_lib.repetition_detector import RepetitionDetector

    det = RepetitionDetector(_write(tmp_path, [
        {"skill_name": "ghost", "tokens": 900, "success": True},   # el campo VIEJO, a proposito
    ]))
    assert det.source_status()["rows_with_named_skill"] == 0, (
        "skill_name is not a field any producer writes; reading it is the bug"
    )
