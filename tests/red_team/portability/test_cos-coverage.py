# SCOPE: os-only
"""Portability probes for scripts/cos-coverage (bash shim).

Verifies the shim correctly delegates to cos_coverage.py and works portably
against any project directory, not just the SO repo.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_SHIM = REPO_ROOT / "scripts" / "cos-coverage"
CLI_PY = REPO_ROOT / "scripts" / "cos_coverage.py"


def run_shim(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CLI_SHIM), "--project-dir", str(project), *extra],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def run_py(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_PY), "--project-dir", str(project), *extra],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def test_shim_exits_zero_on_empty_project(tmp_path: Path) -> None:
    result = run_shim(tmp_path)
    assert result.returncode == 0, result.stderr


def test_shim_json_matches_python_json(tmp_path: Path) -> None:
    """The shim must produce the same JSON as the Python script directly."""
    run_py(tmp_path, "--refresh")  # warm cache
    py_out = run_py(tmp_path, "--json")
    sh_out = run_shim(tmp_path, "--json")
    assert sh_out.returncode == 0, sh_out.stderr
    py_data = json.loads(py_out.stdout)
    sh_data = json.loads(sh_out.stdout)
    # Core keys must match
    for key in ("coverage_pct", "real", "dormant", "aspirational"):
        assert py_data[key] == sh_data[key], f"Mismatch on {key}"


def test_shim_brief_is_single_line(tmp_path: Path) -> None:
    result = run_shim(tmp_path, "--brief")
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == 1
    assert "ACC:" in result.stdout


def test_shim_refresh_flag_accepted(tmp_path: Path) -> None:
    result = run_shim(tmp_path, "--refresh")
    assert result.returncode == 0, result.stderr


def test_falsification_shim_unknown_flag_fails(tmp_path: Path) -> None:
    result = run_shim(tmp_path, "--definitely-not-a-real-flag")
    assert result.returncode != 0
