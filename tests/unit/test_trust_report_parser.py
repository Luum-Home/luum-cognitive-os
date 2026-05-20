"""Unit tests for lib/trust_report_parser.py — ADR-038 Wave 3.

Tests cover:
- Parsing realistic agent output with Wave-3 header format
- Fuzzy whitespace tolerance (extra blank lines, indented bullets)
- Missing/absent report sections (None returned)
- Multi-paragraph bullets in section bodies
- Legacy "TRUST REPORT: Score: XX/100" format support
- TrustReportParseError with helpful diagnostics on malformed input
- score_to_status boundary conditions (re-exported from schema)
- format_header / format_full round-trip via Pydantic model
"""

import pytest

from lib.trust_report_parser import TrustReport, TrustReportParser, TrustReportParseError, score_to_status
from lib.trust_report_schema import build_trust_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_OUTPUT = """\
PROGRESS: [step 1/3] Implemented feature
PROGRESS: [step 2/3] Wrote unit tests
PROGRESS: [step 3/3] Ran lint

RESULT:
  status: completed
  summary: Feature implemented and tested.
  files_created: lib/example.py
  files_modified: none
  tests: 12 passed, 0 failed
  blockers: none

TRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=4 UNCERTAINTIES=2
---
Score: 82/100

WHAT I VERIFIED:
  - All 12 unit tests pass (python3 -m pytest)
  - Lint clean (ruff check, 0 errors)
  - No import errors
  - Type annotations checked

UNSURE ABOUT:
  - Load behaviour under concurrent requests
  - Edge case X with Unicode input

HUMAN SHOULD CHECK:
  - Run integration tests in staging
  - Verify behaviour under load
"""

_LEGACY_OUTPUT = """\
Files created: handler.go

TRUST REPORT:
  Score: 65/100

  EVIDENCE PROVIDED:
    [check] Compiles without errors
    [warn] Tests not comprehensive

  WHAT I'M CONFIDENT ABOUT:
    - Core logic implemented

  WHAT I'M UNSURE ABOUT:
    - No integration tests written
    - Error handling for edge cases

  WHAT THE HUMAN SHOULD VERIFY:
    - Run full test suite before merge
"""


# ---------------------------------------------------------------------------
# score_to_status (re-exported)
# ---------------------------------------------------------------------------

class TestScoreToStatusReexport:
    def test_high(self):
        assert score_to_status(90) == "HIGH"
        assert score_to_status(100) == "HIGH"

    def test_medium(self):
        assert score_to_status(70) == "MEDIUM"
        assert score_to_status(89) == "MEDIUM"

    def test_low(self):
        assert score_to_status(50) == "LOW"
        assert score_to_status(69) == "LOW"

    def test_critical(self):
        assert score_to_status(0) == "CRITICAL"
        assert score_to_status(49) == "CRITICAL"


# ---------------------------------------------------------------------------
# Parsing realistic Wave-3 agent output
# ---------------------------------------------------------------------------

class TestExtractFromOutput:
    def test_realistic_full_output(self):
        parser = TrustReportParser()
        report = parser.extract_from_output(_VALID_OUTPUT)
        assert report is not None
        assert isinstance(report, TrustReport)
        assert report.score == 82
        assert report.status == "MEDIUM"
        assert report.evidence_count == 4
        assert report.uncertainty_count == 2

    def test_verified_section_parsed(self):
        parser = TrustReportParser()
        report = parser.extract_from_output(_VALID_OUTPUT)
        assert report is not None
        assert any("12 unit tests" in item for item in report.verified)

    def test_unsure_section_parsed(self):
        parser = TrustReportParser()
        report = parser.extract_from_output(_VALID_OUTPUT)
        assert report is not None
        assert len(report.unsure) >= 1

    def test_human_should_check_parsed(self):
        parser = TrustReportParser()
        report = parser.extract_from_output(_VALID_OUTPUT)
        assert report is not None
        assert len(report.human_should_check) >= 1

    def test_high_score_output(self):
        output = (
            "TRUST_REPORT: SCORE=95 STATUS=HIGH EVIDENCE=6 UNCERTAINTIES=1\n"
            "---\n"
            "WHAT I VERIFIED:\n"
            "  - 42 tests pass\n"
            "  - Build succeeds\n"
            "  - Lint clean\n"
            "  - Type checked\n"
            "  - Integration tests pass\n"
            "  - Performance baseline met\n"
            "UNSURE ABOUT:\n"
            "  - Behaviour under pathological inputs\n"
            "HUMAN SHOULD CHECK:\n"
            "  - Manual smoke test\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert report.score == 95
        assert report.status == "HIGH"
        assert report.evidence_count == 6

    def test_critical_score_output(self):
        output = (
            "TRUST_REPORT: SCORE=25 STATUS=CRITICAL EVIDENCE=0 UNCERTAINTIES=3\n"
            "---\n"
            "WHAT I VERIFIED:\n"
            "UNSURE ABOUT:\n"
            "  - Everything\n"
            "  - No tests\n"
            "  - No lint\n"
            "HUMAN SHOULD CHECK:\n"
            "  - Re-implement from scratch\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert report.status == "CRITICAL"
        assert report.uncertainty_count == 3


# ---------------------------------------------------------------------------
# Fuzzy whitespace tolerance
# ---------------------------------------------------------------------------

class TestFuzzyWhitespace:
    def test_extra_blank_lines_between_sections(self):
        output = (
            "TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=1\n"
            "---\n"
            "\n\n"
            "WHAT I VERIFIED:\n"
            "\n"
            "  - Tests pass\n"
            "  - Lint clean\n"
            "\n\n"
            "UNSURE ABOUT:\n"
            "\n"
            "  - Coverage not measured\n"
            "\n\n"
            "HUMAN SHOULD CHECK:\n"
            "  - Verify in staging\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert report.score == 75

    def test_deeply_indented_bullets(self):
        output = (
            "TRUST_REPORT: SCORE=70 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1\n"
            "---\n"
            "WHAT I VERIFIED:\n"
            "        - Deeply indented item\n"
            "UNSURE ABOUT:\n"
            "      - Another deeply indented item\n"
            "HUMAN SHOULD CHECK:\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert any("Deeply indented" in item for item in report.verified)

    def test_header_with_extra_spaces(self):
        output = "TRUST_REPORT:  SCORE=80  STATUS=MEDIUM  EVIDENCE=2  UNCERTAINTIES=1\n---\nUNSURE ABOUT:\n  - x\n"
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert report.score == 80


# ---------------------------------------------------------------------------
# Missing/absent report
# ---------------------------------------------------------------------------

class TestMissingReport:
    def test_no_report_returns_none(self):
        output = "Task completed. Files written. No trust report here."
        parser = TrustReportParser()
        assert parser.extract_from_output(output) is None

    def test_empty_string_returns_none(self):
        parser = TrustReportParser()
        assert parser.extract_from_output("") is None

    def test_none_input_returns_none(self):
        parser = TrustReportParser()
        assert parser.extract_from_output(None) is None

    def test_partial_header_no_match(self):
        # Missing UNCERTAINTIES field
        output = "TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=2\nSome body"
        parser = TrustReportParser()
        # Should not match the header regex and return None
        result = parser.extract_from_output(output)
        assert result is None


# ---------------------------------------------------------------------------
# Multi-paragraph / verbose bullets
# ---------------------------------------------------------------------------

class TestMultiParagraphBullets:
    def test_long_bullet_items_parsed(self):
        output = (
            "TRUST_REPORT: SCORE=72 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2\n"
            "---\n"
            "WHAT I VERIFIED:\n"
            "  - Ran python3 -m pytest tests/ — 47 passed, 0 failed, 2 warnings\n"
            "  - Ran ruff check . — no issues found in 15 files\n"
            "  - Verified import structure with python3 -c 'import lib.example'\n"
            "UNSURE ABOUT:\n"
            "  - The regex may miss Unicode edge cases that weren't in the test suite\n"
            "  - Behaviour when the input file exceeds 1 GB has not been tested\n"
            "HUMAN SHOULD CHECK:\n"
            "  - Run with a real production dataset to confirm performance\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert len(report.verified) == 3
        assert len(report.unsure) == 2
        assert len(report.human_should_check) == 1


# ---------------------------------------------------------------------------
# Legacy format
# ---------------------------------------------------------------------------

class TestLegacyFormat:
    def test_legacy_output_parsed(self):
        parser = TrustReportParser()
        report = parser.extract_from_output(_LEGACY_OUTPUT)
        assert report is not None
        assert report.score == 65
        assert report.status == "LOW"

    def test_legacy_evidence_markers_counted(self):
        parser = TrustReportParser()
        report = parser.extract_from_output(_LEGACY_OUTPUT)
        assert report is not None
        assert report.evidence_count == 2  # [check] + [warn]

    def test_legacy_uncertainty_defaults_to_one_minimum(self):
        # Legacy format with no explicit uncertainty section
        output = "TRUST REPORT:\n  Score: 90/100\n  All done.\n"
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        # Parser clamps to 1 so TrustReport model doesn't reject it
        assert report.uncertainty_count >= 1


# ---------------------------------------------------------------------------
# TrustReportParseError with diagnostics
# ---------------------------------------------------------------------------

class TestParseError:
    def test_band_mismatch_raises_parse_error(self):
        bad_output = (
            "TRUST_REPORT: SCORE=95 STATUS=CRITICAL EVIDENCE=2 UNCERTAINTIES=1\n"
            "---\n"
            "WHAT I VERIFIED:\n"
            "  - Tests pass\n"
            "  - Lint clean\n"
            "UNSURE ABOUT:\n"
            "  - Something\n"
            "HUMAN SHOULD CHECK:\n"
        )
        parser = TrustReportParser()
        with pytest.raises(TrustReportParseError) as exc_info:
            parser.extract_from_output(bad_output)
        err = exc_info.value
        assert err.malformed_section != ""
        assert err.hint != ""
        # The error message should mention the mismatch
        assert "BAND_MISMATCH" in str(err) or "TRUST_REPORT" in str(err)

    def test_zero_uncertainty_raises_parse_error(self):
        bad_output = (
            "TRUST_REPORT: SCORE=80 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=0\n"
            "---\n"
            "WHAT I VERIFIED:\n"
            "  - x\n"
            "  - y\n"
            "UNSURE ABOUT:\n"
            "HUMAN SHOULD CHECK:\n"
        )
        parser = TrustReportParser()
        with pytest.raises(TrustReportParseError):
            parser.extract_from_output(bad_output)


# ---------------------------------------------------------------------------
# format_header / format_full round-trip
# ---------------------------------------------------------------------------

class TestFormatRoundtrip:
    def test_format_header(self):
        report = build_trust_report(
            score=75,
            verified=["Tests pass"],
            unsure=["Coverage unknown"],
            human_should_check=[],
        )
        parser = TrustReportParser()
        header = parser.format_header(report)
        assert header == "TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1"

    def test_format_full_parseable(self):
        report = build_trust_report(
            score=90,
            verified=["Build passes", "Tests green"],
            unsure=["Edge case X"],
            human_should_check=["Check staging"],
        )
        parser = TrustReportParser()
        rendered = parser.format_full(report)
        parsed = parser.extract_from_output(rendered)
        assert parsed is not None
        assert parsed.score == 90
        assert parsed.status == "HIGH"
        assert parsed.evidence_count == 2
        assert parsed.uncertainty_count == 1
