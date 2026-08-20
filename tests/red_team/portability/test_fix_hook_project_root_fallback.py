# SCOPE: os-only
"""Proof pareado de portabilidad para scripts/fix_hook_project_root_fallback.py.

Que es este script y por que necesita proof
-------------------------------------------
Es la migracion que reemplazo, en trece hooks, el fallback

    PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

por el resolver compartido `hooks/_lib/project-root.sh`. Ya corrio una vez. El
riesgo no es que no funcione: es que vuelva a correr. Un migrador que no es
idempotente aplica el parche DOS veces y deja el hook peor que antes, y la unica
forma de enterarse es que alguien lo corra en un arbol ya migrado -- que es
exactamente lo que hace quien encuentra el script meses despues.

Las sondas
----------
1. ANTI-VACIO: el detector tiene que encontrar un ofensor SEMBRADO. Sin esto, un
   regex roto reporta "cero ofensores" y las demas pruebas pasan sobre una lista
   vacia. Este repo ya tuvo hoy un gate que informaba verde mientras evaluaba cero
   archivos por un backslash de mas.
2. FALSACION: parchear un hook sano no puede modificarlo. Un migrador que toca todo
   lo que ve no esta detectando, esta reescribiendo.
3. IDEMPOTENCIA: la segunda pasada sobre el mismo archivo devuelve False y deja los
   bytes intactos.
4. INVARIANCIA DE CWD: el detector barre SU arbol, no el directorio desde el que se
   lo invoca. Un auditor anclado al cwd no falla ruidosamente: audita el arbol
   equivocado y sale limpio por vacio, que es la peor forma de pasar.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "fix_hook_project_root_fallback.py"

HOOK_ROTO = """#!/usr/bin/env bash
# SCOPE: both
set -euo pipefail
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
echo "$PROJECT_DIR"
"""

HOOK_SANO = """#!/usr/bin/env bash
# SCOPE: both
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/project-root.sh"
PROJECT_DIR="$(cos_project_root)"
echo "$PROJECT_DIR"
"""


@pytest.fixture(scope="module")
def mod():
    """Importa el migrador por ruta. Su nombre es snake_case, asi que es importable."""
    assert SCRIPT.is_file(), f"{SCRIPT} no existe"
    spec = importlib.util.spec_from_file_location("_fix_hook_project_root", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_declara_scope():
    cabecera = SCRIPT.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), (
        "el primitivo no declara SCOPE en las primeras tres lineas"
    )


def test_el_detector_encuentra_un_ofensor_sembrado(mod, tmp_path: Path):
    """Sonda anti-vacio. Si esto falla, el regex esta roto y todo lo demas miente."""
    victima = tmp_path / "hook-roto.sh"
    victima.write_text(HOOK_ROTO)
    assert mod.BAD_ASSIGN_RE.search(victima.read_text()), (
        "el regex del migrador no reconoce el fallback que existe para reemplazar: "
        "sembramos uno textual y no lo vio"
    )


def test_no_toca_un_hook_sano(mod, tmp_path: Path):
    """Falsacion. Un migrador que reescribe lo que ya esta bien no discrimina."""
    sano = tmp_path / "hook-sano.sh"
    sano.write_text(HOOK_SANO)
    antes = sano.read_bytes()
    cambio = mod.patch_hook(sano)
    assert cambio is False, "reporto haber parcheado un hook que ya estaba correcto"
    assert sano.read_bytes() == antes, "modifico los bytes de un hook sano"


def test_es_idempotente(mod, tmp_path: Path):
    """El riesgo real: que el script vuelva a correr en un arbol ya migrado."""
    victima = tmp_path / "hook-roto.sh"
    victima.write_text(HOOK_ROTO)

    primera = mod.patch_hook(victima)
    assert primera is True, "no parcheo un hook que si tenia el fallback malo"
    tras_primera = victima.read_bytes()
    assert b"/../.." not in tras_primera, "quedo el fallback viejo despues de parchear"

    segunda = mod.patch_hook(victima)
    assert segunda is False, (
        "la segunda pasada volvio a reportar cambio: el migrador NO es idempotente y "
        "correrlo dos veces deja el hook peor que antes"
    )
    assert victima.read_bytes() == tras_primera, (
        "la segunda pasada modifico bytes: doble aplicacion del parche"
    )


def test_el_detector_no_depende_del_cwd(tmp_path: Path):
    """Invariancia de cwd, medida sobre el proceso real y no sobre la funcion.

    Se lo corre en modo listado desde el repo y desde un directorio ajeno. Si el
    veredicto cambia, esta anclado al cwd y audita el arbol equivocado.
    """
    env = dict(os.environ)
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)

    def correr(cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--dry-run"],
            cwd=str(cwd), capture_output=True, text=True, timeout=120,
            env=env, check=False,
        )

    desde_repo = correr(REPO_ROOT)
    desde_afuera = correr(tmp_path)
    assert desde_repo.returncode in (0, 1), (
        "--dry-run no corrio limpio desde el repo; sin eso la comparacion de abajo "
        f"no discrimina nada: {desde_repo.stderr[-400:]}"
    )
    assert desde_repo.returncode == desde_afuera.returncode, (
        "el veredicto cambia segun desde donde se lo corra: esta anclado al cwd\n"
        f"repo={desde_repo.returncode} afuera={desde_afuera.returncode}\n"
        f"{desde_afuera.stderr[-500:]}"
    )
    assert desde_repo.stdout == desde_afuera.stdout, (
        "la lista de ofensores cambia segun el cwd"
    )


def test_el_arbol_ya_esta_migrado(mod):
    """Estado: despues de la migracion no puede quedar ningun ofensor.

    Es la unica asercion sobre el repo vivo. Si aparece uno nuevo, alguien
    reintrodujo el fallback y hay que mandarlo al resolver compartido.
    """
    quedan = mod.offenders(REPO_ROOT)
    assert quedan == [], (
        f"quedaron hooks con el fallback viejo: {quedan}\n"
        "Corré: .venv/bin/python3 scripts/fix_hook_project_root_fallback.py"
    )
