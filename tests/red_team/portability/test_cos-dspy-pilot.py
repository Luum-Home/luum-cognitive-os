# SCOPE: both
"""Portability probes for scripts/cos-dspy-pilot.

Bilateral assertion: invoking the script via python3 on any harness produces
JSON on stdout matching the dspy-structured-skill-pilot/v1 schema.

Falsification probes:
  - Unknown CLI flag must cause a non-zero exit (argparse rejects it), proving
    the script is real argparse-driven code, not a print-stub.
  - Output must be valid JSON with the documented schema_version (a stub
    returning plain text would fail the json.loads).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-dspy-pilot"


def test_cos_dspy_pilot_runs_and_returns_versioned_json() -> None:
    """Bilateral: script returns versioned JSON payload on any harness."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "dspy-structured-skill-pilot/v1"
    assert payload["target_skill"] == "sdd-verify"
    assert payload["status"] in {"ready", "dependency-missing"}


def test_cos_dspy_pilot_honors_target_skill_flag() -> None:
    """Bilateral: --target-skill flag is wired to the pilot report."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--target-skill", "custom-skill"],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["target_skill"] == "custom-skill"


def test_cos_dspy_pilot_rejects_unknown_flag() -> None:
    """Falsification: argparse must reject bogus flags (proves it's not a stub)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-such-flag"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0, (
        "falsification: unknown flag should exit non-zero, "
        f"got {result.returncode}; stdout={result.stdout[:120]}"
    )
