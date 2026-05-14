# SCOPE: os-only
"""Portability proof for scripts/cos_run_task.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos_run_task.py"


def test_cos_run_task_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script must not depend on OS repo cwd for safe invocation."""
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage:" in (result.stdout + result.stderr).lower()
