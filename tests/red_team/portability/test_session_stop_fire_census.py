# SCOPE: os-only
"""Portability proof for scripts/session_stop_fire_census.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/session_stop_fire_census.py"


def test_census_runs_from_an_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: must not require the OS repo as cwd.

    Run from an empty directory with no telemetry at all. The census reads
    .cognitive-os/metrics relative to cwd, so the honest outcome there is a
    zero-count report, never a crash and never a read of the OS repo.
    """
    result = subprocess.run(
        [sys.executable, str(ARTIFACT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "disparos de session-cleanup" in result.stdout
    assert "filas totales de telemetria      : 0" in result.stdout, (
        "Corrio sobre un directorio vacio y aun asi conto filas: esta leyendo "
        f"telemetria de otro lado.\n{result.stdout}"
    )
