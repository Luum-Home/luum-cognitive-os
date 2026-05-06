"""Tests for ADR-212 cross-stack license audit policy."""
from __future__ import annotations

from pathlib import Path

from lib.cross_stack_license_audit import audit_workflows, classify_trivy_version, load_policy


def _write_policy(repo: Path) -> None:
    manifest = repo / "manifests/cross-stack-license-audit.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version: cross-stack-license-audit/v1
primary:
  toolchain: syft-grype
  tools: [syft, grype]
secondary:
  toolchain: trivy
  denied_versions: [0.69.4, 0.69.5, 0.69.6]
  denied_workflow_actions:
    - aquasecurity/trivy-action
    - aquasecurity/setup-trivy
  require_immutable_workflow_pin: true
""".strip(),
        encoding="utf-8",
    )


def test_classifies_known_bad_trivy_version(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    policy = load_policy(tmp_path)

    finding = classify_trivy_version("Version: 0.69.4", policy)

    assert finding is not None
    assert finding.severity == "block"
    assert finding.code == "blocked-trivy-version"


def test_allows_non_denied_trivy_version(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    policy = load_policy(tmp_path)

    assert classify_trivy_version("Version: 0.69.3", policy) is None


def test_blocks_mutable_trivy_workflow_action(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    workflow = tmp_path / ".github/workflows/security.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        """
name: security
on: [push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: aquasecurity/trivy-action@v0.34.2
""".strip(),
        encoding="utf-8",
    )
    policy = load_policy(tmp_path)

    findings = audit_workflows(tmp_path, policy)

    assert len(findings) == 1
    assert findings[0].severity == "block"
    assert findings[0].code == "mutable-trivy-workflow-action"


def test_allows_immutable_trivy_workflow_pin(tmp_path: Path) -> None:
    _write_policy(tmp_path)
    workflow = tmp_path / ".github/workflows/security.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "uses: aquasecurity/trivy-action@" + "a" * 40 + "\n",
        encoding="utf-8",
    )
    policy = load_policy(tmp_path)

    assert audit_workflows(tmp_path, policy) == []
