"""Unit tests for lib/trust_report_schema.py — ADR-038 Wave 3.

Coverage:
- Valid construction (full model, factory helper)
- Band mismatch (score↔status inconsistency)
- Score range violations (below 0, above 100)
- Missing uncertainty (uncertainty_count < 1)
- Negative evidence_count
- Auto-derived status via build_trust_report
- header_line() and as_text() helpers
- score_to_status() boundary conditions
"""

import pytest
from pydantic import ValidationError

from lib.trust_report_schema import TrustReport, build_trust_report, score_to_status


# ---------------------------------------------------------------------------
# score_to_status helper
# ---------------------------------------------------------------------------

class TestScoreToStatus:
    def test_high_lower_bound(self):
        assert score_to_status(90) == "HIGH"

    def test_high_upper_bound(self):
        assert score_to_status(100) == "HIGH"

    def test_medium_lower_bound(self):
        assert score_to_status(70) == "MEDIUM"

    def test_medium_upper_bound(self):
        assert score_to_status(89) == "MEDIUM"

    def test_low_lower_bound(self):
        assert score_to_status(50) == "LOW"

    def test_low_upper_bound(self):
        assert score_to_status(69) == "LOW"

    def test_critical_upper_bound(self):
        assert score_to_status(49) == "CRITICAL"

    def test_critical_zero(self):
        assert score_to_status(0) == "CRITICAL"


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------

class TestTrustReportValid:
    def _minimal(self) -> TrustReport:
        return TrustReport(
            score=75,
            status="MEDIUM",
            evidence_count=3,
            uncertainty_count=2,
            verified=["Tests pass", "Lint clean"],
            unsure=["Coverage unknown", "Load behaviour untested"],
            human_should_check=["Run integration tests"],
        )

    def test_valid_medium(self):
        r = self._minimal()
        assert r.score == 75
        assert r.status == "MEDIUM"
        assert r.evidence_count == 3
        assert r.uncertainty_count == 2

    def test_valid_high(self):
        r = TrustReport(
            score=95,
            status="HIGH",
            evidence_count=5,
            uncertainty_count=1,
            verified=["All 42 tests pass"],
            unsure=["Edge case X not covered"],
            human_should_check=[],
        )
        assert r.status == "HIGH"

    def test_valid_low(self):
        r = TrustReport(
            score=55,
            status="LOW",
            evidence_count=1,
            uncertainty_count=3,
            verified=["Code compiles"],
            unsure=["No tests", "Error paths untested", "Concurrency unknown"],
            human_should_check=["Write tests"],
        )
        assert r.status == "LOW"

    def test_valid_critical(self):
        r = TrustReport(
            score=30,
            status="CRITICAL",
            evidence_count=0,
            uncertainty_count=2,
            verified=[],
            unsure=["Not verified at all", "Unknown state"],
            human_should_check=["Re-do manually"],
        )
        assert r.status == "CRITICAL"

    def test_evidence_count_zero_allowed(self):
        r = TrustReport(
            score=40,
            status="CRITICAL",
            evidence_count=0,
            uncertainty_count=1,
            verified=[],
            unsure=["Everything"],
            human_should_check=[],
        )
        assert r.evidence_count == 0

    def test_empty_lists_allowed(self):
        r = TrustReport(
            score=90,
            status="HIGH",
            evidence_count=0,
            uncertainty_count=1,
            verified=[],
            unsure=["One thing"],
            human_should_check=[],
        )
        assert r.verified == []


# ---------------------------------------------------------------------------
# Band mismatch
# ---------------------------------------------------------------------------

class TestBandMismatch:
    def test_score_95_with_low_status_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=95,
                status="LOW",
                evidence_count=2,
                uncertainty_count=1,
                verified=["x"],
                unsure=["y"],
                human_should_check=[],
            )
        msg = str(exc_info.value)
        assert "BAND_MISMATCH" in msg

    def test_score_50_with_high_status_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=50,
                status="HIGH",
                evidence_count=1,
                uncertainty_count=1,
                verified=["x"],
                unsure=["y"],
                human_should_check=[],
            )
        assert "BAND_MISMATCH" in str(exc_info.value)

    def test_score_89_with_high_status_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=89,
                status="HIGH",
                evidence_count=1,
                uncertainty_count=1,
                verified=["x"],
                unsure=["y"],
                human_should_check=[],
            )
        assert "BAND_MISMATCH" in str(exc_info.value)

    def test_score_0_with_low_status_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=0,
                status="LOW",
                evidence_count=0,
                uncertainty_count=1,
                verified=[],
                unsure=["x"],
                human_should_check=[],
            )
        assert "BAND_MISMATCH" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Score range violations
# ---------------------------------------------------------------------------

class TestScoreRange:
    def test_score_above_100_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=101,
                status="HIGH",
                evidence_count=1,
                uncertainty_count=1,
                verified=["x"],
                unsure=["y"],
                human_should_check=[],
            )
        assert "RANGE_ERROR" in str(exc_info.value)

    def test_score_below_0_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=-1,
                status="CRITICAL",
                evidence_count=0,
                uncertainty_count=1,
                verified=[],
                unsure=["x"],
                human_should_check=[],
            )
        assert "RANGE_ERROR" in str(exc_info.value)

    def test_boundary_0_accepted(self):
        r = TrustReport(
            score=0,
            status="CRITICAL",
            evidence_count=0,
            uncertainty_count=1,
            verified=[],
            unsure=["x"],
            human_should_check=[],
        )
        assert r.score == 0

    def test_boundary_100_accepted(self):
        r = TrustReport(
            score=100,
            status="HIGH",
            evidence_count=1,
            uncertainty_count=1,
            verified=["x"],
            unsure=["y"],
            human_should_check=[],
        )
        assert r.score == 100


# ---------------------------------------------------------------------------
# Missing uncertainty (100% confidence red-flag)
# ---------------------------------------------------------------------------

class TestUncertaintyRequired:
    def test_zero_uncertainty_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=90,
                status="HIGH",
                evidence_count=3,
                uncertainty_count=0,
                verified=["x", "y", "z"],
                unsure=[],
                human_should_check=[],
            )
        msg = str(exc_info.value)
        assert "MISSING_UNCERTAINTY" in msg

    def test_negative_uncertainty_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=75,
                status="MEDIUM",
                evidence_count=2,
                uncertainty_count=-1,
                verified=["x", "y"],
                unsure=[],
                human_should_check=[],
            )
        assert "MISSING_UNCERTAINTY" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Negative evidence_count
# ---------------------------------------------------------------------------

class TestEvidenceCount:
    def test_negative_evidence_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrustReport(
                score=75,
                status="MEDIUM",
                evidence_count=-1,
                uncertainty_count=1,
                verified=[],
                unsure=["x"],
                human_should_check=[],
            )
        assert "RANGE_ERROR" in str(exc_info.value)


# ---------------------------------------------------------------------------
# build_trust_report factory
# ---------------------------------------------------------------------------

class TestBuildTrustReport:
    def test_auto_derives_status(self):
        r = build_trust_report(
            score=82,
            verified=["Tests pass"],
            unsure=["Coverage unknown"],
            human_should_check=[],
        )
        assert r.status == "MEDIUM"

    def test_auto_derives_counts(self):
        r = build_trust_report(
            score=55,
            verified=["A", "B"],
            unsure=["C", "D", "E"],
            human_should_check=["F"],
        )
        assert r.evidence_count == 2
        assert r.uncertainty_count == 3

    def test_explicit_counts_override(self):
        r = build_trust_report(
            score=70,
            verified=["A"],
            unsure=["B"],
            human_should_check=[],
            evidence_count=10,
            uncertainty_count=5,
        )
        assert r.evidence_count == 10
        assert r.uncertainty_count == 5

    def test_factory_enforces_constraints(self):
        with pytest.raises(ValidationError):
            build_trust_report(
                score=82,
                verified=[],
                unsure=[],  # uncertainty_count will be 0 — rejected
                human_should_check=[],
            )


# ---------------------------------------------------------------------------
# header_line and as_text helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def _report(self) -> TrustReport:
        return build_trust_report(
            score=75,
            verified=["Tests pass"],
            unsure=["Coverage not measured"],
            human_should_check=["Run integration suite"],
        )

    def test_header_line_format(self):
        r = self._report()
        line = r.header_line()
        assert line.startswith("TRUST_REPORT:")
        assert "SCORE=75" in line
        assert "STATUS=MEDIUM" in line
        assert "EVIDENCE=1" in line
        assert "UNCERTAINTIES=1" in line

    def test_as_text_contains_sections(self):
        r = self._report()
        text = r.as_text()
        assert "WHAT I VERIFIED" in text
        assert "UNSURE ABOUT" in text
        assert "HUMAN SHOULD CHECK" in text
        assert "Tests pass" in text
        assert "Coverage not measured" in text
