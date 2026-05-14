# SCOPE: os-only
"""Portability proof for scripts/cos-init.sh."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / 'scripts/cos-init.sh'


def test_cos_init_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: must not depend on OS repo cwd."""
    command = [sys.executable, str(ARTIFACT), "--help"] if ARTIFACT.suffix == ".py" else [str(ARTIFACT), "--help"]
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
