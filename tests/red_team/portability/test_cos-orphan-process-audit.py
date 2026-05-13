# SCOPE: os-only
"""Portability probe for scripts/cos-orphan-process-audit.py (ADR-279).

Bilateral: CLI is a thin wrapper; --help works; unknown flag errors.
Falsification: missing lib import would break the CLI.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "cos-orphan-process-audit.py"


def test_cli_is_python_with_shebang():
    text = SCRIPT.read_text()
    assert text.startswith("#!/usr/bin/env python3"), "missing python3 shebang"


def test_cli_help_works():
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.strip()


def test_falsification_unknown_flag_errors():
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-such-flag-XYZ"],
        capture_output=True, text=True, timeout=10,
    )
    assert cp.returncode != 0
