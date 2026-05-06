"""Behavior tests for ADR-215 cross-stack secret audit CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.behavior
def test_cross_stack_secret_audit_cli_outputs_json_and_writes_latest(project_root: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "manifests/cross-stack-secret-audit.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text((project_root / "manifests/cross-stack-secret-audit.yaml").read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [str(project_root / "scripts/cos-cross-stack-secret-audit"), "--project-dir", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode in {0, 1}
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cross-stack-secret-audit-report/v1"
    assert payload["primary_toolchain"] == "gitleaks-trufflehog"
    latest = tmp_path / ".cognitive-os/reports/secret-audit/cross-stack-secret-audit-latest.json"
    assert latest.exists()


@pytest.mark.behavior
def test_cross_stack_secret_audit_cli_strict_fails_on_sensitive_local_surface(project_root: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "manifests/cross-stack-secret-audit.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text((project_root / "manifests/cross-stack-secret-audit.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / ".env").write_text("DO_NOT_PRINT_ME=secret\n", encoding="utf-8")

    result = subprocess.run(
        [str(project_root / "scripts/cos-cross-stack-secret-audit"), "--project-dir", str(tmp_path), "--json", "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "warn"
    assert any(f["code"] == "secret-never-touch-file-present" for f in payload["findings"])
    assert "DO_NOT_PRINT_ME" not in result.stdout


@pytest.mark.behavior
def test_cos_secret_audit_route_works(project_root: Path) -> None:
    result = subprocess.run(
        [str(project_root / "scripts/cos"), "secret", "audit", "--json", "--no-write-latest"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode in {0, 1, 2}
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cross-stack-secret-audit-report/v1"
