# SCOPE: os-only
# scope: both
"""
Portability proofs for scripts/cos-coordination-status.sh — P3.3 coordination
status wrapper.

Confirms the shell wrapper delegates correctly to the snake_case Python
implementation and works outside the SO harness.

Run with:
    python3 -m pytest "tests/red_team/portability/test_cos-coordination-status.py" -v
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_SH = REPO_ROOT / "scripts" / "cos-coordination-status.sh"
CLI_PY = REPO_ROOT / "scripts" / "cos_coordination_status.py"


def run_cli(*extra: str, direct_python: bool = False) -> "subprocess.CompletedProcess[str]":
    command = ["python3", str(CLI_PY), *extra] if direct_python else ["bash", str(CLI_SH), *extra]
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
        cwd=str(REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# Proof 1: exits 0 against this repo
# ---------------------------------------------------------------------------

def test_exits_zero_against_repo() -> None:
    """Script must exit 0 and not crash when run from the repo root."""
    result = run_cli()
    assert result.returncode == 0, f"Unexpected error: {result.stderr}"


# ---------------------------------------------------------------------------
# Proof 2: --json flag produces valid JSON (delegates to cos_work_inventory)
# ---------------------------------------------------------------------------

def test_json_flag_produces_valid_json() -> None:
    """--json passthrough must yield parseable JSON output."""
    result = run_cli("--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)


# ---------------------------------------------------------------------------
# Proof 3: unknown flag rejected (falsification probe)
# ---------------------------------------------------------------------------

def test_unknown_flag_rejected() -> None:
    """Passing an unrecognised flag must fail with a non-zero exit code."""
    result = run_cli("--this-flag-does-not-exist-xyz")
    assert result.returncode != 0, "Expected non-zero exit for unknown flag"


def test_snake_case_python_entrypoint_produces_json() -> None:
    """Direct Python entrypoint must stay snake_case and functional."""
    result = run_cli("--json", direct_python=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
