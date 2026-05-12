# SCOPE: both
"""Portability probe for scripts/cos-primitive-authority-audit (bash wrapper
that delegates to scripts/primitive_authority_audit.py).

The wrapper is a thin shim that re-execs Python; this probe asserts:
  1. The wrapper file is executable bash and points at the Python script.
  2. It honors --help (passes through to underlying script).
  3. The Python target exists and is invokable.

Falsification:
  - Removing the Python target makes the wrapper fail.
  - Wrapper without exec bit cannot run.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WRAPPER = REPO / "scripts" / "cos-primitive-authority-audit"
PY_TARGET = REPO / "scripts" / "primitive_authority_audit.py"


def test_wrapper_is_executable_bash():
    """Bilateral: wrapper is bash, has exec bit, and delegates to the Python script."""
    assert WRAPPER.exists(), "wrapper missing"
    text = WRAPPER.read_text()
    assert text.startswith("#!/usr/bin/env bash"), "wrapper not bash"
    assert "primitive_authority_audit.py" in text, "wrapper does not delegate"
    assert os.access(WRAPPER, os.X_OK), "wrapper missing exec bit"


def test_python_target_exists():
    """Falsification: if the Python target is gone, the wrapper cannot work."""
    assert PY_TARGET.exists(), "Python target script missing"


def test_wrapper_smoke_help():
    """Bilateral: wrapper --help returns 0 and emits text (delegated to Python)."""
    cp = subprocess.run(
        ["bash", str(WRAPPER), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # argparse --help exits 0 with output on stdout
    assert cp.returncode == 0, f"--help failed: {cp.stderr}"
    assert cp.stdout.strip(), "--help produced no output"
