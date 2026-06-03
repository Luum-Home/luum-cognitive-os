# SCOPE: os-only
"""Portability proof for scripts/dod_check.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "dod_check.py"


def test_dod_check_wrapper_safe_invocation_from_arbitrary_project_root(
    tmp_path: Path,
) -> None:
    """Falsification probe: wrapper must resolve its packaged checker independent of cwd."""
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "CODEX_PROJECT_DIR": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
        }
    )
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Definition of Done" in output
    assert "No such file or directory" not in output
    assert "Traceback" not in output
