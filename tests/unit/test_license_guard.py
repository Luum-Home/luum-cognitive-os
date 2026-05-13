"""Tests for lib/license_guard.py — License Auto-Guard.

Author: luum
"""

from __future__ import annotations

import json
from pathlib import Path


from lib.license_guard import (
    BLOCKED_LICENSES,
    auto_block_in_content_policy,
    check_and_enforce,
    check_license,
    format_license_report,
    scan_existing_references,
)


class TestCheckLicense:
    """Tests for check_license()."""

    def test_mit_returns_safe(self) -> None:
        result = check_license("my-lib", "MIT")
        assert result.status == "safe"
        assert result.tool_name == "my-lib"
        assert result.license_id == "MIT"

    def test_apache_returns_safe(self) -> None:
        result = check_license("crawl4ai", "Apache-2.0")
        assert result.status == "safe"

    def test_agpl_returns_blocked(self) -> None:
        result = check_license("mongo-driver", "AGPL-3.0")
        assert result.status == "blocked"
        assert "REJECT" in result.action_required

    def test_cc_by_nc_returns_blocked(self) -> None:
        result = check_license("some-tool", "CC-BY-NC-4.0")
        assert result.status == "blocked"
        assert "non-commercial" in result.reason.lower()

    def test_gpl_returns_caution(self) -> None:
        result = check_license("gpl-lib", "GPL-3.0")
        assert result.status == "caution"
        assert "copyleft" in result.reason.lower()

    def test_lgpl_returns_caution(self) -> None:
        result = check_license("lgpl-lib", "LGPL-2.1")
        assert result.status == "caution"

    def test_unknown_license_returns_unknown(self) -> None:
        result = check_license("mystery-lib", "WTFPL")
        assert result.status == "unknown"
        assert "manual review" in result.action_required.lower()

    def test_sspl_returns_blocked(self) -> None:
        result = check_license("sspl-tool", "SSPL-1.0")
        assert result.status == "blocked"

    def test_bsl_returns_blocked(self) -> None:
        result = check_license("bsl-tool", "BSL-1.1")
        assert result.status == "blocked"

    def test_elastic_returns_blocked(self) -> None:
        result = check_license("elastic-tool", "ELv2")
        assert result.status == "blocked"


class TestBlockedLicensesDict:
    """Tests for BLOCKED_LICENSES dict completeness."""

    def test_has_all_expected_licenses(self) -> None:
        expected = [
            "AGPL-3.0",
            "SSPL-1.0",
            "CC-BY-NC-4.0",
            "BSL-1.1",
            "ELv2",
            "Commons-Clause",
            "FSL-1.0",
        ]
        for lic in expected:
            assert lic in BLOCKED_LICENSES, f"{lic} missing from BLOCKED_LICENSES"

    def test_blocked_dict_not_empty(self) -> None:
        assert len(BLOCKED_LICENSES) > 0


class TestAutoBlock:
    """Tests for auto_block_in_content_policy()."""

    def test_auto_block_adds_to_content_policy(self, tmp_path: Path) -> None:
        policy = tmp_path / "content-policy.yaml"
        added = auto_block_in_content_policy(
            "bad-tool", "AGPL-3.0", str(policy)
        )
        assert added is True
        assert policy.exists()
        content = policy.read_text()
        assert "bad-tool" in content
        assert "AGPL-3.0" in content

    def test_auto_block_doesnt_duplicate(self, tmp_path: Path) -> None:
        policy = tmp_path / "content-policy.yaml"
        auto_block_in_content_policy("bad-tool", "AGPL-3.0", str(policy))
        added = auto_block_in_content_policy("bad-tool", "AGPL-3.0", str(policy))
        assert added is False

    def test_auto_block_ignores_safe_license(self, tmp_path: Path) -> None:
        policy = tmp_path / "content-policy.yaml"
        added = auto_block_in_content_policy("safe-tool", "MIT", str(policy))
        assert added is False


class TestCheckAndEnforce:
    """Tests for check_and_enforce() full flow."""

    def test_blocked_flow(self, tmp_path: Path) -> None:
        policy = tmp_path / "policy.yaml"
        log = tmp_path / "log.jsonl"
        result = check_and_enforce(
            "agpl-tool",
            "AGPL-3.0",
            policy_path=str(policy),
            log_path=str(log),
        )
        assert result.status == "blocked"
        assert policy.exists()
        assert log.exists()
        log_entry = json.loads(log.read_text().strip())
        assert log_entry["status"] == "blocked"

    def test_safe_flow_no_action(self, tmp_path: Path) -> None:
        policy = tmp_path / "policy.yaml"
        log = tmp_path / "log.jsonl"
        result = check_and_enforce(
            "safe-tool",
            "MIT",
            policy_path=str(policy),
            log_path=str(log),
        )
        assert result.status == "safe"
        assert not policy.exists()  # No policy file created for safe licenses
        assert log.exists()  # But the check is still logged


class TestFormatReport:
    """Tests for format_license_report()."""

    def test_report_has_required_sections(self) -> None:
        results = [
            check_license("safe-lib", "MIT"),
            check_license("bad-lib", "AGPL-3.0"),
            check_license("cautious-lib", "GPL-3.0"),
        ]
        report = format_license_report(results)
        assert "## License Check Report" in report
        assert "BLOCKED" in report
        assert "CAUTION" in report
        assert "SAFE" in report
        assert "Total" in report

    def test_report_empty_results(self) -> None:
        report = format_license_report([])
        assert "## License Check Report" in report
        assert "Total" in report


class TestScanExistingReferences:
    """Tests for scan_existing_references()."""

    def test_scan_finds_blocked_references(self, tmp_path: Path) -> None:
        # Create a file with a blocked license reference
        doc = tmp_path / "deps.md"
        doc.write_text("We use mongo which is AGPL-3.0 licensed\n")
        findings = scan_existing_references(str(tmp_path), extensions=[".md"])
        assert len(findings) > 0
        assert any(f.license_id == "AGPL-3.0" for f in findings)

    def test_scan_ignores_safe_licenses(self, tmp_path: Path) -> None:
        doc = tmp_path / "deps.md"
        doc.write_text("This project uses MIT licensed tools only\n")
        findings = scan_existing_references(str(tmp_path), extensions=[".md"])
        # MIT is not in BLOCKED_LICENSES, so no findings
        blocked_findings = [f for f in findings if f.license_id == "MIT"]
        assert len(blocked_findings) == 0

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        findings = scan_existing_references(str(tmp_path))
        assert findings == []
