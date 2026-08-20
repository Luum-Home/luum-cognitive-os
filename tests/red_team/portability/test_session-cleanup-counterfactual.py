# SCOPE: os-only
"""Portability proof for scripts/session-cleanup-counterfactual.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/session-cleanup-counterfactual.sh"


def test_counterfactual_runs_from_an_arbitrary_cwd(tmp_path: Path) -> None:
    """Falsification probe: resolves its own repo, never the caller's cwd.

    Also proves the point of the script itself: with the session identity
    resolved, the live session directory must still be there afterwards.
    """
    target = tmp_path / "proyecto"
    result = subprocess.run(
        ["bash", str(ARTIFACT), str(target)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "RUN A" in result.stdout and "RUN B" in result.stdout
    assert "BORRADO" not in result.stdout, (
        "El hook borro el directorio de una sesion sin prueba de muerte del "
        f"duenio.\n{result.stdout}"
    )
    # El proyecto temporal se creo fuera del repo del artefacto.
    assert target.exists() and REPO_ROOT not in target.parents
