"""Unit tests for lib/trust_report_parser.py."""

import pytest

from lib.trust_report_parser import TrustReport, TrustReportParser, score_to_status


class TestScoreToStatus:
    """Test the score_to_status helper."""

    def test_high(self):
        assert score_to_status(100) == "HIGH"
        assert score_to_status(95) == "HIGH"
        assert score_to_status(90) == "HIGH"

    def test_medium(self):
        assert score_to_status(89) == "MEDIUM"
        assert score_to_status(75) == "MEDIUM"
        assert score_to_status(70) == "MEDIUM"

    def test_low(self):
        assert score_to_status(69) == "LOW"
        assert score_to_status(55) == "LOW"
        assert score_to_status(50) == "LOW"

    def test_critical(self):
        assert score_to_status(49) == "CRITICAL"
        assert score_to_status(25) == "CRITICAL"
        assert score_to_status(0) == "CRITICAL"


class TestParseHeader:
    """Test parsing the machine-parseable header format."""

    def test_parse_valid_header(self):
        text = (
            "TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2\n"
            "---\n"
            "Score: 75/100\n"
            "Some human-readable content."
        )
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 75
        assert report.status == "MEDIUM"
        assert report.evidence_count == 3
        assert report.uncertainty_count == 2
        assert "Score: 75/100" in report.raw_text

    def test_parse_header_high_score(self):
        text = "TRUST_REPORT: SCORE=95 STATUS=HIGH EVIDENCE=5 UNCERTAINTIES=1\n---\nBody"
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 95
        assert report.status == "HIGH"
        assert report.evidence_count == 5
        assert report.uncertainty_count == 1

    def test_parse_header_zero_score(self):
        text = "TRUST_REPORT: SCORE=0 STATUS=CRITICAL EVIDENCE=0 UNCERTAINTIES=0\n---\n"
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 0
        assert report.status == "CRITICAL"

    def test_parse_header_without_separator(self):
        text = "TRUST_REPORT: SCORE=80 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=1\nSome text"
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 80

    def test_parse_header_case_insensitive(self):
        text = "trust_report: score=80 status=medium evidence=2 uncertainties=1\n---\nBody"
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 80
        assert report.status == "MEDIUM"


class TestParseLegacy:
    """Test parsing the legacy Trust Report format."""

    def test_parse_legacy_format(self):
        text = (
            "TRUST REPORT:\n"
            "  Score: 85/100\n"
            "\n"
            "  EVIDENCE PROVIDED:\n"
            "    [check] Tests pass\n"
            "    [warn] Coverage not measured\n"
            "    [fail] Integration tests missing\n"
            "\n"
            "  WHAT I'M CONFIDENT ABOUT:\n"
            "    - Unit tests cover happy path\n"
            "\n"
            "  WHAT I'M UNSURE ABOUT:\n"
            "    - Edge case handling\n"
            "    - Performance under load\n"
        )
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 85
        assert report.status == "MEDIUM"
        assert report.evidence_count == 3
        assert report.uncertainty_count == 2

    def test_parse_legacy_no_evidence(self):
        text = "TRUST REPORT:\n  Score: 40/100\n\n  No evidence.\n"
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is not None
        assert report.score == 40
        assert report.status == "CRITICAL"
        assert report.evidence_count == 0
        assert report.uncertainty_count == 0

    def test_parse_no_trust_report(self):
        text = "This is just regular output with no trust report."
        parser = TrustReportParser()
        report = parser.parse(text)
        assert report is None


class TestExtractFromOutput:
    """Test extracting Trust Report from full agent output."""

    def test_extract_new_format(self):
        output = (
            "PROGRESS: [step 1/2] Implemented feature\n"
            "PROGRESS: [step 2/2] Wrote tests\n"
            "\n"
            "TRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=4 UNCERTAINTIES=1\n"
            "---\n"
            "Score: 82/100\n"
            "\n"
            "EVIDENCE PROVIDED:\n"
            "  [check] Build passes\n"
            "  [check] Tests pass: 12/12\n"
            "  [check] Lint clean\n"
            "  [warn] Coverage not measured\n"
            "\n"
            "WHAT I'M UNSURE ABOUT:\n"
            "  - Behavior with concurrent requests\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert report.score == 82
        assert report.status == "MEDIUM"
        assert report.evidence_count == 4
        assert report.uncertainty_count == 1

    def test_extract_legacy_format(self):
        output = (
            "Files created: handler.go\n"
            "\n"
            "TRUST REPORT:\n"
            "  Score: 65/100\n"
            "\n"
            "  EVIDENCE PROVIDED:\n"
            "    [check] Compiles\n"
            "\n"
            "  WHAT I'M UNSURE ABOUT:\n"
            "    - No tests written\n"
            "    - Error handling incomplete\n"
            "    - Performance unknown\n"
        )
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is not None
        assert report.score == 65
        assert report.status == "LOW"
        assert report.evidence_count == 1
        assert report.uncertainty_count == 3

    def test_extract_no_report(self):
        output = "Task completed successfully. All files written."
        parser = TrustReportParser()
        report = parser.extract_from_output(output)
        assert report is None

    def test_extract_empty_output(self):
        parser = TrustReportParser()
        assert parser.extract_from_output("") is None
        assert parser.extract_from_output(None) is None


class TestFormatHeader:
    """Test header generation."""

    def test_format_header(self):
        report = TrustReport(
            score=75, status="MEDIUM",
            evidence_count=3, uncertainty_count=2,
            raw_text="Body text",
        )
        parser = TrustReportParser()
        header = parser.format_header(report)
        assert header == "TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2"

    def test_format_full_roundtrip(self):
        """format_full output should be parseable back."""
        original = TrustReport(
            score=90, status="HIGH",
            evidence_count=5, uncertainty_count=1,
            raw_text="Score: 90/100\nDetailed report.",
        )
        parser = TrustReportParser()
        formatted = parser.format_full(original)
        parsed = parser.parse(formatted)
        assert parsed is not None
        assert parsed.score == original.score
        assert parsed.status == original.status
        assert parsed.evidence_count == original.evidence_count
        assert parsed.uncertainty_count == original.uncertainty_count
