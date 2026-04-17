"""End-to-end tests for install.sh -> manifest-check.sh wiring.

After install.sh finishes provisioning .cognitive-os/ and .claude/, it
invokes scripts/manifest-check.sh as an advisory dependency report.
The report runs against the source manifest (manifests/dependencies.yaml)
and prints OK/MISSING per declared tool/MCP.

Contract:
- The check runs by default and its output is visible to the user.
- The check NEVER fails the install (exit 1 from missing required tools
  is acceptable; only exit 2 from a broken manifest surfaces a warning).
- --skip-manifest-check and COGNITIVE_OS_SKIP_MANIFEST_CHECK suppress it.
- The selected profile is passed through (default vs full).

These tests run install.sh end-to-end into a tmp project directory.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "install.sh"


@pytest.fixture
def install_dir(tmp_path):
    project = tmp_path / "test-project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    return project


@pytest.fixture(autouse=True)
def isolate_registry(tmp_path, monkeypatch):
    """Use a temp registry so tests don't pollute ~/.cognitive-os/."""
    monkeypatch.setenv("COS_REGISTRY_FILE", str(tmp_path / "registry.json"))


def _run_installer(install_dir: Path, *args: str, env_extra: dict | None = None):
    env = {**os.environ}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(INSTALLER), "--force", *args],
        cwd=install_dir,
        capture_output=True,
        text=True,
        env=env,
    )


# ── Default behavior ────────────────────────────────────────────────────


def test_install_runs_manifest_check_by_default(install_dir):
    proc = _run_installer(install_dir)
    assert proc.returncode == 0, proc.stderr
    assert "Checking declared dependencies" in proc.stdout
    # The manifest-check produces either PASS or FAIL depending on the host.
    assert ("Result: PASS" in proc.stdout) or ("Result: FAIL" in proc.stdout)


def test_install_passes_profile_to_manifest_check_default(install_dir):
    proc = _run_installer(install_dir)
    assert "profile: default" in proc.stdout


def test_install_passes_profile_to_manifest_check_full(install_dir):
    proc = _run_installer(install_dir, "--full")
    assert "profile: full" in proc.stdout


def test_install_succeeds_even_when_check_reports_missing(install_dir):
    """A failing manifest-check (exit 1) MUST NOT fail the install."""
    proc = _run_installer(install_dir)
    # We can't guarantee the host has every recommended tool, but the install
    # must always exit 0 regardless of what the check reports.
    assert proc.returncode == 0, (
        f"install must succeed even with missing deps; got {proc.returncode}\n"
        f"stderr: {proc.stderr}\nstdout (tail): {proc.stdout[-500:]}"
    )


# ── Opt-out paths ───────────────────────────────────────────────────────


def test_skip_manifest_check_flag_suppresses_report(install_dir):
    proc = _run_installer(install_dir, "--skip-manifest-check")
    assert proc.returncode == 0, proc.stderr
    assert "Manifest check skipped" in proc.stdout
    assert "Checking declared dependencies" not in proc.stdout


def test_skip_via_env_var_suppresses_report(install_dir):
    proc = _run_installer(
        install_dir, env_extra={"COGNITIVE_OS_SKIP_MANIFEST_CHECK": "true"}
    )
    assert proc.returncode == 0, proc.stderr
    assert "Manifest check skipped" in proc.stdout


def test_help_documents_new_flag():
    proc = subprocess.run(
        [str(INSTALLER), "--help"], capture_output=True, text=True
    )
    assert proc.returncode == 0
    assert "--skip-manifest-check" in proc.stdout
    assert "COGNITIVE_OS_SKIP_MANIFEST_CHECK" in proc.stdout


def test_unknown_flag_help_lists_skip_manifest(install_dir):
    """Stdout for unknown flag should advertise the new flag too."""
    proc = _run_installer(install_dir, "--bogus-flag")
    assert proc.returncode != 0
    assert "--skip-manifest-check" in proc.stderr


# ── Robustness: install must not break if check has problems ───────────


def test_check_output_appears_after_success_message(install_dir):
    """The dep report should come AFTER 'installed successfully' so the
    user can see install completed before reading the dep status."""
    proc = _run_installer(install_dir)
    out = proc.stdout
    success_idx = out.find("Cognitive OS installed successfully")
    check_idx = out.find("Checking declared dependencies")
    assert success_idx >= 0, "missing success line"
    assert check_idx >= 0, "missing check line"
    assert success_idx < check_idx, (
        "manifest-check must run AFTER the install summary so failures "
        "in the check don't obscure that install itself worked"
    )
