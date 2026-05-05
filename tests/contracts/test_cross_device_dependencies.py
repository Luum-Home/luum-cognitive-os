"""Contract tests for ADR-168 cross-device dependency installation."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-deps-install.sh"
ADR = REPO / "docs" / "adrs" / "ADR-168-cross-device-dependency-installation.md"


def run_install(*args: str) -> dict:
    result = subprocess.run([str(SCRIPT), *args], cwd=REPO, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.mark.parametrize("platform", ["macos", "linux", "windows_wsl"])
def test_core_dry_run_emits_cross_platform_json(platform: str) -> None:
    payload = run_install("--profile", "core", "--platform", platform, "--dry-run", "--json")

    assert payload["schema_version"] == "cos-deps-install.v1"
    assert payload["mode"] == "dry-run"
    assert payload["platform"] == platform
    assert payload["manifest_profile"] == "default"
    assert payload["credential_policy"] == "never-copy-or-read-credential-stores"
    assert not payload["failed"]


def test_auth_bound_dependencies_are_reported_not_installed() -> None:
    payload = run_install("--profile", "standard", "--platform", "linux", "--dry-run", "--json")
    auth_names = {row["name"] for row in payload["auth_bound"]}

    assert "gh" in auth_names
    assert all(row["action"] != "installable" for row in payload["auth_bound"])


def test_adr_168_links_installer_and_contract_test() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "scripts/cos-deps-install.sh" in text
    assert "tests/contracts/test_cross_device_dependencies.py" in text
