"""Tests for ADR-215 cross-stack secret audit policy."""
from __future__ import annotations

from pathlib import Path

from lib.cross_stack_secret_audit import (
    audit_workflows,
    classify_external_finding,
    discover_sensitive_files,
    load_policy,
)


def _write_policy(repo: Path) -> None:
    manifest = repo / "manifests/cross-stack-secret-audit.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version: cross-stack-secret-audit/v1
primary:
  toolchain: gitleaks-trufflehog
  tools: [gitleaks, trufflehog]
workflow_policy:
  require_immutable_workflow_pin: true
  denied_mutable_actions:
    - gitleaks/gitleaks-action
    - trufflesecurity/trufflehog
policy:
  exclude_paths:
    - '(^|/)\.git($|/)'
  secret_never_touch:
    - '(^|/)\.env($|\.)'
    - '(^|/).*\.pem$'
  placeholder_path_allowlist:
    - '(^|/)tests($|/)'
    - '(^|/)fixtures($|/)'
  placeholder_fingerprints:
    - '[REDACTED]'
    - 'FAKEKEYFORTEST'
  unknown_unclassified_findings: suspect
reporting:
  latest_report: .cognitive-os/reports/secret-audit/cross-stack-secret-audit-latest.json
""".strip(),
        encoding="utf-8",
    )


def test_blocks_mutable_secret_scanner_workflow_action(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    workflow = tmp_path / ".github/workflows/secrets.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("uses: gitleaks/gitleaks-action@v2\n", encoding="utf-8")
    policy = load_policy(tmp_path)

    findings = audit_workflows(tmp_path, policy)

    assert len(findings) == 1
    assert findings[0].severity == "block"
    assert findings[0].code == "mutable-secret-scanner-workflow-action"


def test_allows_immutable_secret_scanner_workflow_pin(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    workflow = tmp_path / ".github/workflows/secrets.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("uses: trufflesecurity/trufflehog@" + "a" * 40 + "\n", encoding="utf-8")
    policy = load_policy(tmp_path)

    assert audit_workflows(tmp_path, policy) == []


def test_discovers_secret_never_touch_files_without_reading_contents(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    (tmp_path / ".env").write_text("REAL_VALUE_SHOULD_NOT_BE_IN_REPORT=secret\n", encoding="utf-8")
    (tmp_path / "safe.txt").write_text("ok\n", encoding="utf-8")
    policy = load_policy(tmp_path)

    findings = discover_sensitive_files(tmp_path, policy)

    assert [f.path for f in findings] == [".env"]
    assert "REAL_VALUE" not in findings[0].message
    assert findings[0].severity == "warn"


def test_classifies_allowlisted_fixture_as_placeholder(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    policy = load_policy(tmp_path)

    assert classify_external_finding("tests/fixtures/token.txt", "not-a-real-token", policy) == "placeholder"


def test_classifies_non_allowlisted_redacted_finding_as_suspect(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    policy = load_policy(tmp_path)

    assert classify_external_finding("src/config.py", "[REDACTED]", policy) == "suspect"
