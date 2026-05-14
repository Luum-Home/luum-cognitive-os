# SCOPE: os-only
"""Portability proof for scripts/cos-session-branch.sh."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos-session-branch.sh"


def test_cos_session_branch_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script must not depend on OS repo cwd for safe invocation."""
    result = subprocess.run(
        ["bash", str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Usage" in (result.stdout + result.stderr) or "[1/4]" in (result.stdout + result.stderr)
