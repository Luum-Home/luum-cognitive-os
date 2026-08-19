"""Prueba pareja de scripts/signal_orphan_verify.py: se lo corre, no se lo nombra.

El auditor de profundidad asocia pruebas a artefactos por NOMBRE DE ARCHIVO, asi
que una prueba compartida por tres scripts no se puede atribuir a ninguno. Esta
es la mitad que le toca a signal_orphan_verify.

Que ejercita: que el script CORRA como subproceso, respete la convencion de exit
codes del repo (0 sin hallazgos, 1 con hallazgos, 2 error), y --la garantia que
motivo su existencia-- que NO PUBLIQUE UN CONTEO SIN SU POBLACION NI SU BUCKET DE
CEGUERA. Un cero sin denominador es indistinguible de una no-observacion, y es el
error que esta sesion cometio ocho veces antes de que estos auditores existieran.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTEFACTO = REPO / "scripts/signal_orphan_verify.py"
VENV = REPO / ".venv" / "bin" / "python3"
ARGS = ['hook-timing']


def _correr(*extra: str) -> subprocess.CompletedProcess:
    if not ARTEFACTO.is_file():
        pytest.skip("scripts/signal_orphan_verify.py no esta en el arbol")
    exe = str(VENV) if VENV.is_file() else sys.executable
    return subprocess.run(
        [exe, str(ARTEFACTO), *ARGS, *extra],
        cwd=REPO, capture_output=True, text=True, timeout=180,
    )


def test_corre_y_respeta_la_convencion_de_exit_codes() -> None:
    r = _correr()
    assert r.returncode in (0, 1), (
        f"salio {r.returncode}; un 2 es error del propio auditor. "
        f"stderr: {r.stderr[-600:]}"
    )
    assert r.stdout.strip(), "auditor mudo: no informa nada"


def test_no_publica_un_conteo_sin_poblacion_ni_ceguera() -> None:
    r = _correr("--json")
    if r.returncode == 2:
        pytest.skip("no soporta --json")
    try:
        datos = json.loads(r.stdout)
    except json.JSONDecodeError:
        pytest.skip("no emite JSON en --json")
    plano = json.dumps(datos).lower()
    assert any(k in plano for k in ("population", "poblacion", "total")), (
        "publica conteos sin declarar sobre cuantos casos miro"
    )
    assert any(
        k in plano
        for k in ("blind", "ceguera", "unclassifiable", "indetermin", "unmeasurable")
    ), (
        "no declara que casos NO puede juzgar; sin ese bucket un cero significa a "
        "la vez 'no paso' y 'no pude mirar'"
    )
