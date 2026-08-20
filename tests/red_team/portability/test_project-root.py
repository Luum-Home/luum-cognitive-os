# SCOPE: os-only
"""Proof pareado de portabilidad para hooks/_lib/project-root.sh.

Por que este archivo NO es el que genero el scaffold
----------------------------------------------------
El scaffold produce una sonda generica: corre el artefacto desde dos raices y
compara veredictos. Sirve para un hook ejecutable. Esto es una LIBRERIA que se
sourcea: `bash hooks/_lib/project-root.sh` sale 0 con stdout vacio siempre, asi
que los dos lados coinciden pase lo que pase y el proof pasa por vacio.

Un proof que no puede fallar no es evidencia de que la primitiva funcione; es
evidencia de que la sonda no la esta ejercitando. Por eso las pruebas de abajo
SOURCEAN la lib y le piden la raiz, y por eso la primera de todas verifica que la
sonda no volvio a quedar muda.

Lo que la primitiva existe para arreglar
----------------------------------------
Trece hooks resolvian la raiz asi:

    PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

Para un hook en `<repo>/hooks/` eso da el PADRE del repo; desde
`packages/<pkg>/hooks/` da `<repo>/packages`. Claude Code setea
CLAUDE_PROJECT_DIR, asi que el fallback solo se ejerce en los otros arneses --
donde nadie mira. El dano estaba en disco: siete pares .ctx/.ts en
`<padre>/.cognitive-os/cache/`, el mas viejo del 10 de junio.

La raiz esperada se deriva con `git rev-parse --show-toplevel`, una fuente
DISTINTA de la aritmetica de rutas que tenia el bug. Si se derivara subiendo
niveles desde __file__, esta prueba heredaria el mismo modelo mental que el
defecto y podria certificarlo en verde -- que es exactamente lo que hizo otro
gate de este repo el 2026-08-20.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LIB = REPO_ROOT / "hooks" / "_lib" / "project-root.sh"

# Las cuatro variables que la lib consulta antes de caer al ancla. Se limpian
# TODAS: dejar una puesta mide el atajo, no el fallback, y el fallback es lo
# unico que estaba roto.
VARS_DE_ARNES = (
    "COGNITIVE_OS_PROJECT_DIR",
    "CODEX_PROJECT_DIR",
    "CLAUDE_PROJECT_DIR",
)


def _raiz_segun_git() -> str:
    """Fuente independiente de la verdad. No usa `..` ni cuenta niveles."""
    r = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30, check=False,
    )
    if r.returncode != 0:
        pytest.skip(f"no se pudo preguntarle a git por la raiz: {r.stderr.strip()}")
    return r.stdout.strip()


def _preguntarle_a_la_lib(cwd: Path, con_vars: dict[str, str] | None = None) -> str:
    """Sourcea la lib y le pide la raiz, con el entorno de arnes limpio."""
    env = dict(os.environ)
    for v in VARS_DE_ARNES:
        env.pop(v, None)
    # Heredados, estos convierten cualquier guard en uno que aprueba todo.
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)
    if con_vars:
        env.update(con_vars)
    r = subprocess.run(
        ["bash", "-c", f'source "{LIB}" && cos_project_root'],
        cwd=str(cwd), capture_output=True, text=True, timeout=30, env=env, check=False,
    )
    assert r.returncode == 0, f"cos_project_root fallo: {r.stderr[-500:]}"
    return r.stdout.strip()


def test_la_sonda_no_esta_muda():
    """Control anti-vacio. Sin esto, todo lo de abajo pasa con stdout vacio."""
    salida = _preguntarle_a_la_lib(REPO_ROOT)
    assert salida, (
        "cos_project_root no imprimio nada: la sonda no esta ejercitando la lib y "
        "las aserciones de abajo comparan vacio contra vacio"
    )


def test_resuelve_la_raiz_sin_ninguna_variable_de_arnes(tmp_path: Path):
    """El hallazgo. Con el entorno limpio, el ancla tiene que dar la raiz del repo.

    Si esto falla con el padre del repo, volvio el off-by-one de `../..`.
    """
    esperada = _raiz_segun_git()
    obtenida = _preguntarle_a_la_lib(tmp_path)
    assert obtenida == esperada, (
        f"la lib resolvio {obtenida!r} y la raiz es {esperada!r}.\n"
        f"Si lo que devolvio es el PADRE de la raiz, volvio el off-by-one: el ancla "
        f"tiene que subir DOS niveles desde hooks/_lib/, no desde hooks/."
    )


def test_no_depende_del_cwd(tmp_path: Path):
    """Invariancia de cwd: la respuesta no puede cambiar segun desde donde se llame.

    Un resolver anclado al cwd no falla ruidosamente: contesta la raiz equivocada
    y todo lo que dependa de ella lee y escribe en el arbol de al lado.
    """
    desde_repo = _preguntarle_a_la_lib(REPO_ROOT)
    desde_afuera = _preguntarle_a_la_lib(tmp_path)
    assert desde_repo == desde_afuera, (
        f"la raiz cambia segun el cwd: {desde_repo!r} vs {desde_afuera!r}"
    )
    assert str(tmp_path) not in desde_afuera, (
        "la lib devolvio una ruta dentro del directorio ajeno: esta usando el cwd"
    )


@pytest.mark.parametrize("var", VARS_DE_ARNES)
def test_la_variable_del_arnes_sigue_teniendo_prioridad(tmp_path: Path, var: str):
    """Control de no-regresion en la otra direccion.

    El arreglo toco el FALLBACK. Si de paso rompio la precedencia, los arneses que
    si setean su variable empezarian a ignorarla, y eso seria peor que el bug
    original porque afecta al camino que hoy funciona.
    """
    obtenida = _preguntarle_a_la_lib(tmp_path, con_vars={var: str(tmp_path)})
    assert obtenida == str(tmp_path), (
        f"{var} estaba seteada en {tmp_path} y la lib devolvio {obtenida!r}: "
        "se perdio la precedencia de la variable de arnes"
    )
