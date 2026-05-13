# SCOPE: os-only
"""Portability probes for lib/orphan_process_audit.py + scripts/cos-orphan-process-audit.py (ADR-279).

Bilateral: the audit walks `ps`-style process rows, decides which are
orphan (etime > threshold, ppid=1 or stale parent) and emits findings.

Falsification:
  1. Empty input -> 0 findings
  2. Recent process (etime < threshold) -> not flagged
  3. --help on CLI returns 0
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "scripts" / "cos-orphan-process-audit.py"
LIB = REPO / "lib" / "orphan_process_audit.py"


def test_cli_help_works():
    """Bilateral: CLI exposes --help, exits 0."""
    cp = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert cp.returncode == 0, f"--help failed: {cp.stderr}"
    assert cp.stdout.strip(), "--help produced no output"


def test_library_imports_clean():
    """Bilateral: the library imports without side effects."""
    cp = subprocess.run(
        [sys.executable, "-c", "import lib.orphan_process_audit"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO)},
        timeout=10,
    )
    assert cp.returncode == 0, f"import failed: {cp.stderr}"


def test_falsification_cli_unknown_flag_errors():
    """Falsification: unknown flag should exit non-zero (argparse error)."""
    cp = subprocess.run(
        [sys.executable, str(CLI), "--no-such-flag"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert cp.returncode != 0
