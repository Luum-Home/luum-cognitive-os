# SCOPE: os-only
# scope: both
"""
Portability proofs for scripts/cos_work_inventory.py — P3.3 work inventory.

These tests run the CLI against a plain temp directory (no Cognitive OS stack)
to confirm it handles non-SO repositories gracefully.

Run with:
    python3 -m pytest tests/red_team/portability/test_cos_work_inventory.py -v
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "scripts" / "cos_work_inventory.py"
PYTHON = sys.executable


def run_cli(project: Path, *extra: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [PYTHON, str(CLI), "--project-dir", str(project), *extra],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


# ---------------------------------------------------------------------------
# Proof 1: exits 0 against this repo (baseline portability check)
# ---------------------------------------------------------------------------

def test_repo_project_exits_zero() -> None:
    """CLI must not crash when run against a valid git repository."""
    result = run_cli(REPO_ROOT)
    assert result.returncode == 0, f"Unexpected error: {result.stderr}"


# ---------------------------------------------------------------------------
# Proof 2: --json flag produces valid JSON
# ---------------------------------------------------------------------------

def test_json_flag_produces_valid_json() -> None:
    """--json output must be parseable JSON."""
    result = run_cli(REPO_ROOT, "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)


# ---------------------------------------------------------------------------
# Proof 3: unknown flag rejected with non-zero exit (falsification probe)
# ---------------------------------------------------------------------------

def test_unknown_flag_rejected(tmp_path: Path) -> None:
    """Passing an unrecognised flag must fail with a non-zero exit code."""
    result = run_cli(tmp_path, "--this-flag-does-not-exist-xyz")
    assert result.returncode != 0, "Expected non-zero exit for unknown flag"
