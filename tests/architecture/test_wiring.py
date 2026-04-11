"""Architecture fitness functions — deterministic wiring validation.

These tests run the enforcement scripts and assert they exit 0.
They serve as a continuous architecture gate: if the scripts detect a new
unwired component, the test suite fails here before CI proceeds.

Run with:
    pytest tests/architecture/test_wiring.py -v
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / script)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


def test_every_skill_in_catalog():
    """Every skill directory under .cognitive-os/skills/ has a matching CATALOG.md entry."""
    result = _run("check-catalog-sync.py")
    assert result.returncode == 0, (
        "Skill catalog is out of sync.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_every_hook_registered():
    """Every hook in hooks/*.sh is registered in security/efficiency profiles."""
    result = _run("check-hook-registration.py")
    assert result.returncode == 0, (
        "Unregistered hooks detected.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_no_new_unwired_libs():
    """No lib/*.py module added after the allowlist baseline is unwired."""
    result = _run("check-lib-wiring.py")
    assert result.returncode == 0, (
        "Unwired lib modules detected.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_scripts_are_executable():
    """Validation scripts exist and are Python files."""
    scripts = [
        "check-catalog-sync.py",
        "check-hook-registration.py",
        "check-lib-wiring.py",
        "check-test-ratchet.py",
    ]
    for script in scripts:
        path = PROJECT_ROOT / "scripts" / script
        assert path.exists(), f"Script missing: scripts/{script}"
        assert path.suffix == ".py", f"Script should be a .py file: {script}"


def test_allowlists_exist():
    """Allowlist files exist to grandfather existing unwired components."""
    hook_allowlist = PROJECT_ROOT / "hooks" / "_lib" / "registration-allowlist.txt"
    lib_allowlist = PROJECT_ROOT / "lib" / "_wiring-allowlist.txt"
    assert hook_allowlist.exists(), "hooks/_lib/registration-allowlist.txt is missing"
    assert lib_allowlist.exists(), "lib/_wiring-allowlist.txt is missing"
