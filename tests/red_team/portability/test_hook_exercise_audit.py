# SCOPE: os-only
"""Prueba de portabilidad pareada de scripts/hook_exercise_audit.py.

Sonda de falsacion: el artefacto resuelve su propio repo desde ``__file__``,
nunca desde el cwd del proceso, y tampoco desde el cwd del modulo que importa
(``hook_quality_audit``, del que toma el registro de hooks y el corpus de
tests). Corrido desde un cwd ajeno tiene que producir exactamente la misma
salida. Un artefacto anclado en ``Path.cwd()`` falla este test en vez de
portarse mal en silencio dentro de un checkout consumidor.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / 'scripts/hook_exercise_audit.py'

# Dos corridas completas sobre ~1000 archivos de test; el timeout global de
# pytest.ini (30s) no alcanza y matarlo por reloj no probaria nada.
pytestmark = pytest.mark.timeout(300)


def _run(cwd: Path, *extra: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(ARTIFACT), *extra],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


def test_help_succeeds_from_arbitrary_project_root(tmp_path: Path) -> None:
    """`--help` es contrato medido aca: sale 0 e imprime usage."""
    result = _run(tmp_path, "--help")
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage" in result.stdout.lower(), result.stdout


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Invariancia de cwd: mismo exit code y misma salida desde el repo y afuera."""
    from_repo = _run(REPO_ROOT, "--json")
    from_foreign = _run(tmp_path, "--json")
    assert from_foreign.returncode == from_repo.returncode, from_foreign.stderr
    assert from_foreign.stdout == from_repo.stdout
    assert str(tmp_path) not in from_foreign.stdout
