"""Behavior tests for ADR-212 cross-stack license audit CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.behavior
def test_cross_stack_license_audit_cli_blocks_mutable_trivy_action(project_root: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "manifests/cross-stack-license-audit.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text((project_root / "manifests/cross-stack-license-audit.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    workflow = tmp_path / ".github/workflows/security.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("uses: aquasecurity/setup-trivy@v0.2.5\n", encoding="utf-8")

    result = subprocess.run(
        [str(project_root / "scripts/cos-cross-stack-license-audit"), "--project-dir", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "block"
    assert any(f["code"] == "mutable-trivy-workflow-action" for f in payload["findings"])


@pytest.mark.behavior
def test_cross_stack_license_audit_cli_outputs_json(project_root: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "manifests/cross-stack-license-audit.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text((project_root / "manifests/cross-stack-license-audit.yaml").read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [str(project_root / "scripts/cos-cross-stack-license-audit"), "--project-dir", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cross-stack-license-audit-report/v1"
    assert payload["primary_toolchain"] == "syft-grype"
