"""Contract tests for ADR-168 cross-device dependency installation."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-deps-install.sh"
ADR = REPO / "docs" / "02-Decisions" / "adrs" / "ADR-168-cross-device-dependency-installation.md"


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
    gh = next(row for row in payload["auth_bound"] if row["name"] == "gh")
    assert gh["syncable"] == "config-only"
    assert "~/.config/gh" in gh["never_copy"]
    assert "gh auth login" in gh["post_install"]


def test_core_tools_have_adr_168_platform_metadata() -> None:
    payload = run_install("--profile", "core", "--platform", "macos", "--dry-run", "--json")
    rows = {row["name"]: row for bucket in ("already_present", "installable", "manual") for row in payload[bucket]}

    for name in ("jq", "git", "uv", "python3"):
        row = rows[name]
        assert "core" in row["profiles"]
        assert row["scope"] in {"user", "system"}
        assert row["syncable"] == "no"
        assert row["install_manager"] in {"brew", "apt", "standalone", "manual", "legacy"}
        assert row["install_source"] in {"macos", "linux", "windows_wsl", "debian", "any"}


@pytest.mark.parametrize("platform", ["macos", "linux", "windows_wsl"])
def test_core_tools_report_no_credential_copy_paths(platform: str) -> None:
    payload = run_install("--profile", "core", "--platform", platform, "--dry-run", "--json")
    rows = [row for bucket in ("already_present", "installable", "manual", "auth_bound") for row in payload[bucket]]

    assert payload["credential_policy"] == "never-copy-or-read-credential-stores"
    assert all(not row["auth_bound"] for row in rows if row["name"] in {"jq", "git", "uv", "python3"})
    assert all(not row["never_copy"] for row in rows if row["name"] in {"jq", "git", "uv", "python3"})




def test_rust_transpiler_lab_profile_reports_lab_tools() -> None:
    payload = run_install("--profile", "rust-transpiler-lab", "--platform", "macos", "--dry-run", "--json")
    rows = {row["name"]: row for bucket in ("already_present", "installable", "manual") for row in payload[bucket]}

    assert payload["manifest_profile"] == "rust-transpiler-lab"
    assert {"py2many", "tnk", "depyler"}.issubset(rows)
    assert rows["depyler"]["install_command"] == "cargo install depyler"
    assert rows["tnk"]["install_manager"] == "cargo"
    assert rows["py2many"]["install_manager"] == "pip"


def test_adr_168_links_installer_and_contract_test() -> None:
    text = ADR.read_text(encoding="utf-8")

    assert "scripts/cos-deps-install.sh" in text
    assert "tests/contracts/test_cross_device_dependencies.py" in text
