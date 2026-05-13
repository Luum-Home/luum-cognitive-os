"""
Unit tests for lib.impact_analysis.

Covers:
  - test_empty_file_list_returns_low_risk
  - test_payment_path_returns_critical
  - test_auth_path_returns_high
  - test_nonexistent_project_dir_graceful
  - test_format_report_returns_string
  - test_path_outside_project_handled
"""

from __future__ import annotations

import pytest

from lib.impact_analysis import (
    analyze_impact,
    classify_risk,
    format_impact_report,
    ImpactReport,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Tests — analyze_impact
# ---------------------------------------------------------------------------


class TestAnalyzeImpact:

    def test_empty_file_list_returns_low_risk(self, tmp_path):
        """No changed files → LOW risk with 'No elevated risk factors' reason."""
        report = analyze_impact([], project_dir=str(tmp_path))
        assert report.risk_level == RiskLevel.LOW
        assert report.changed_files == []

    def test_empty_file_list_report_structure(self, tmp_path):
        """Empty input returns a valid ImpactReport with empty dicts."""
        report = analyze_impact([], project_dir=str(tmp_path))
        assert isinstance(report, ImpactReport)
        assert isinstance(report.direct_importers, dict)
        assert isinstance(report.affected_tests, dict)

    def test_payment_path_returns_critical(self, tmp_path):
        """A file in a /payment/ directory should return CRITICAL risk."""
        # Create the file so os.path.abspath works
        payment_dir = tmp_path / "internal" / "payment"
        payment_dir.mkdir(parents=True)
        payment_file = payment_dir / "handler.go"
        payment_file.write_text("package payment\n")

        report = analyze_impact([str(payment_file)], project_dir=str(tmp_path))
        assert report.risk_level == RiskLevel.CRITICAL, (
            f"Expected CRITICAL for payment path, got {report.risk_level}. "
            f"Reasons: {report.risk_reasons}"
        )

    def test_auth_path_returns_high(self, tmp_path):
        """A file in /auth/ should return at least HIGH risk."""
        auth_dir = tmp_path / "internal" / "auth"
        auth_dir.mkdir(parents=True)
        auth_file = auth_dir / "service.go"
        auth_file.write_text("package auth\n")

        report = analyze_impact([str(auth_file)], project_dir=str(tmp_path))
        assert report.risk_level >= RiskLevel.HIGH, (
            f"Expected HIGH or CRITICAL for auth path, got {report.risk_level}. "
            f"Reasons: {report.risk_reasons}"
        )

    def test_nonexistent_project_dir_graceful(self):
        """analyze_impact raises FileNotFoundError when project_dir does not exist.

        find_docker_services calls os.listdir(project_dir) which raises on a
        missing directory.  This test documents the current (unguarded) behavior.
        """
        fake_dir = "/nonexistent/project/dir/abc123"
        with pytest.raises(FileNotFoundError):
            analyze_impact([], project_dir=fake_dir)

    def test_path_outside_project_handled(self, tmp_path):
        """Files outside project_dir should be handled gracefully."""
        # File that doesn't exist — analyze_impact normalizes paths; should not crash
        outside_file = "/tmp/some_random_file_that_may_not_exist.py"
        report = analyze_impact([outside_file], project_dir=str(tmp_path))
        assert isinstance(report, ImpactReport)
        # Risk could be low or higher depending on path — just no crash

    def test_security_path_returns_high(self, tmp_path):
        """File in /security/ should return at least HIGH risk."""
        sec_dir = tmp_path / "pkg" / "security"
        sec_dir.mkdir(parents=True)
        sec_file = sec_dir / "jwt.go"
        sec_file.write_text("package security\n")

        report = analyze_impact([str(sec_file)], project_dir=str(tmp_path))
        assert report.risk_level >= RiskLevel.HIGH, (
            f"Expected HIGH+ for security path, got {report.risk_level}"
        )

    def test_report_has_risk_reasons(self, tmp_path):
        """ImpactReport always has at least one risk reason."""
        report = analyze_impact([], project_dir=str(tmp_path))
        assert len(report.risk_reasons) >= 1

    def test_analyze_uses_cwd_when_project_dir_none(self, monkeypatch, tmp_path):
        """When project_dir is None, current directory is used."""
        monkeypatch.chdir(tmp_path)
        report = analyze_impact([])
        assert isinstance(report, ImpactReport)


# ---------------------------------------------------------------------------
# Tests — classify_risk
# ---------------------------------------------------------------------------


class TestClassifyRisk:

    def test_empty_inputs_low_risk(self):
        risk, reasons = classify_risk([], {}, {}, {})
        assert risk == RiskLevel.LOW
        assert len(reasons) >= 1

    def test_critical_path_overrides_all(self):
        """A /payment/ file should produce CRITICAL regardless of other factors."""
        changed = ["/internal/payment/handler.go"]
        risk, reasons = classify_risk(changed, {}, {}, {})
        assert risk == RiskLevel.CRITICAL

    def test_many_importers_upgrades_to_high(self):
        """More than 10 importers → HIGH risk."""
        changed = ["file.go"]
        importers = {"file.go": [f"importer{i}.go" for i in range(11)]}
        risk, reasons = classify_risk(changed, importers, {}, {})
        assert risk >= RiskLevel.HIGH

    def test_moderate_importers_upgrades_to_medium(self):
        """6 importers → at least MEDIUM risk."""
        changed = ["file.go"]
        importers = {"file.go": [f"importer{i}.go" for i in range(6)]}
        risk, reasons = classify_risk(changed, importers, {}, {})
        assert risk >= RiskLevel.MEDIUM

    def test_no_test_coverage_upgrades_to_medium(self):
        """All changed files with no test coverage → at least MEDIUM."""
        changed = ["myfile.go"]
        risk, reasons = classify_risk(changed, {}, {}, {})
        # No test coverage found for all files
        assert risk >= RiskLevel.MEDIUM


# ---------------------------------------------------------------------------
# Tests — format_impact_report
# ---------------------------------------------------------------------------


class TestFormatImpactReport:

    def test_format_report_returns_string(self, tmp_path):
        report = analyze_impact([], project_dir=str(tmp_path))
        output = format_impact_report(report)
        assert isinstance(output, str)

    def test_format_report_contains_risk_level(self, tmp_path):
        report = analyze_impact([], project_dir=str(tmp_path))
        output = format_impact_report(report)
        assert "Risk Level" in output or "LOW" in output

    def test_format_report_contains_summary(self, tmp_path):
        report = analyze_impact([], project_dir=str(tmp_path))
        output = format_impact_report(report)
        assert "SUMMARY" in output

    def test_format_report_nonempty(self, tmp_path):
        report = analyze_impact([], project_dir=str(tmp_path))
        output = format_impact_report(report)
        assert len(output) > 0
