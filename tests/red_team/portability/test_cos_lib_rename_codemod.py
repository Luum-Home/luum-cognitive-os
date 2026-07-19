# SCOPE: os-only
"""Portability proof for scripts/cos_lib_rename_codemod.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos_lib_rename_codemod.py"


def test_cos_lib_rename_codemod_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_cos_lib_rename_codemod_help_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: --help must not depend on OS repo cwd."""
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert "No such file or directory" not in output, output
