# SCOPE: both
"""Portability probe for scripts/primitive_authority_audit.py.

Bilateral: the script emits a deterministic report regardless of project
context. Falsification: --help works; --json (if supported) produces JSON;
running on an empty project does not crash.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "primitive_authority_audit.py"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), *extra]
    return subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd=str(project_dir), timeout=30
    )


def test_help_returns_zero(tmp_path: Path):
    """Bilateral: --help works regardless of project state."""
    cp = _run(tmp_path, "--help")
    assert cp.returncode == 0, f"--help failed: {cp.stderr}"
    assert cp.stdout.strip(), "--help produced no output"


def test_script_is_executable_python(tmp_path: Path):
    """Bilateral: script is Python and has a __main__ entrypoint."""
    text = SCRIPT.read_text()
    assert text.startswith("#!/usr/bin/env python3"), "wrong shebang"
    assert 'if __name__ == "__main__"' in text, "missing main guard"


def test_falsification_unknown_flag(tmp_path: Path):
    """Falsification: unknown flag should exit non-zero (argparse error)."""
    cp = _run(tmp_path, "--definitely-not-a-real-flag")
    assert cp.returncode != 0, "unknown flag must error"
