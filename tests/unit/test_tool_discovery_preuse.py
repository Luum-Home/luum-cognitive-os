"""Unit tests for ADR-216 Tool Discovery Pre-Use Gate."""
from __future__ import annotations

from pathlib import Path

from lib.tool_discovery_preuse import evaluate_command


def test_blocks_ad_hoc_license_audit_command(project_root: Path) -> None:
    report = evaluate_command("pip-licenses --format=json && go-licenses report ./...", project_root)

    assert report["status"] == "block"
    assert report["findings"][0]["rule_id"] == "license-audit-ad-hoc"
    assert "scripts/agentic-tool-license-matrix.sh" in report["findings"][0]["canonical"]


def test_allows_canonical_license_audit_command(project_root: Path) -> None:
    report = evaluate_command("bash scripts/agentic-tool-license-matrix.sh --json", project_root)

    assert report["status"] == "pass"


def test_allows_explicit_tool_discovery_override(project_root: Path) -> None:
    report = evaluate_command("COS_ALLOW_TOOL_DISCOVERY_BYPASS=1 pip-licenses --format=json", project_root)

    assert report["status"] == "pass"


def test_warns_on_raw_github_clone_without_repo_scout(project_root: Path) -> None:
    report = evaluate_command("git clone https://github.com/example/tool", project_root)

    assert report["status"] == "warn"
    assert report["findings"][0]["rule_id"] == "external-repo-analysis-ad-hoc"


def test_blocks_raw_trivy_install_or_baseline(project_root: Path) -> None:
    install_report = evaluate_command("brew install trivy && trivy fs --scanners license .", project_root)
    scan_report = evaluate_command("trivy fs --scanners license --format json .", project_root)

    assert install_report["status"] == "block"
    assert install_report["findings"][0]["rule_id"] == "trivy-ad-hoc-secondary-scan"
    assert scan_report["status"] == "block"
    assert scan_report["findings"][0]["rule_id"] == "trivy-ad-hoc-secondary-scan"


def test_allows_canonical_trivy_wrappers(project_root: Path) -> None:
    install_report = evaluate_command("bash scripts/install-trivy.sh", project_root)
    scan_report = evaluate_command("bash scripts/license-audit-trivy.sh", project_root)

    assert install_report["status"] == "pass"
    assert scan_report["status"] == "pass"
