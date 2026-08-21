# SCOPE: os-only
"""Un stash compartido no puede producir un bloqueo por worktree.

El defecto, medido el 2026-08-20
--------------------------------
`cos_work_inventory.py` corre la inspeccion de stashes desde cada worktree enlazado.
Eso es sano y su propio docstring explica por que: prueba que el inventario es
independiente del IDE. Pero el docstring TAMBIEN dice, en su primera linea, que

    "Git stores stash refs per repository"

y aun asi el resultado se emitia como un `BLOCK` POR WORKTREE. O sea: la misma
informacion, contada una vez bien en el bucle de `payload["stashes"]`, y N veces mas
como `linked-worktree-stashes-present`.

Lo que costo: dos stashes creados por la sesion del operador --`fea17d5b4689` y
`7616ae0a1dbe`, comprobados con `git -C <wt> rev-parse stash@{0} stash@{1}` en los 13
worktrees, mismos SHAs-- se contaban como 15 "worktree stashes" y 13 BLOCKERS. Con eso
el preflight de ADR-116 **freno el lanzamiento de agentes por trabajo que no existia**.
Las 13 ramas tenian `ahead_of_main=0`, `merged=True` y worktree limpio: cero lineas en
riesgo, y `git branch -d` las acepto todas sin forzar una sola.

Es la clase que esa jornada persiguio entera, esta vez en el instrumento que gobierna
si se puede trabajar: un conteo que mide otra cosa y produce un bloqueo real sobre una
ausencia.

Lo que el arreglo NO toca
-------------------------
"No pude inspeccionar ese worktree" SIGUE reportandose. Es un estado distinto de "ahi
no hay stashes", y colapsarlos seria repetir el defecto que esta misma jornada
encontro en la precondicion de chaos y en tres guards mas. Baja de BLOCK a WARN porque
no poder mirar no es evidencia de riesgo, pero no desaparece.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INV = REPO / "scripts" / "cos_work_inventory.py"


@pytest.fixture(scope="module")
def inv():
    """Importa el inventario registrandolo en sys.modules.

    Sin el registro, los `@dataclass` del modulo revientan al evaluarse: dataclasses
    resuelve anotaciones via `sys.modules[cls.__module__]`. (Aprendido rompiendolo.)
    """
    spec = importlib.util.spec_from_file_location("cos_work_inventory", INV)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _payload(inv_mod, *, worktrees: int, inspeccionables: bool) -> dict:
    """Payload minimo con UN stash del repo visto desde N worktrees enlazados.

    La forma se toma de una corrida real del inventario, no se inventa: un payload
    inventado puede omitir una clave y hacer que build_findings falle por una razon
    que no tiene nada que ver con lo que se quiere probar.
    """
    p = {
        # `status` es la salida de `git status` parseada, NO un string. Escribir "ok"
        # aca hace que build_findings reviente indexando un str con una clave -- y el
        # fallo se lee como si el arreglo estuviera mal, cuando lo que esta mal es la
        # sonda. (Aprendido rompiendolo, y es exactamente lo que el docstring de esta
        # funcion advierte: la forma se toma de una corrida real, no se inventa.)
        "status": {
            "branch": "main", "ahead": 0, "behind": 0, "entries": [],
            "counts": {"modified": 0, "staged": 0, "unmerged": 0, "untracked": 0},
        },
        "worktrees": [], "orphans": [], "claims": [], "resource_leases": [],
        "path_ownership": [], "race_risks": [], "session_fs_stats": {},
        "sessions": [], "stashes_extended": [], "worktrees_direct": [],
        "preserve_branches": [], "branch_pattern": "", "base_ref": "origin/main",
        "project": str(REPO),
    }
    p["stashes"] = [{
        "ref": "stash@{0}", "level": "BLOCK", "age_seconds": 9999,
        "file_count": 62, "subject": "trabajo del operador", "is_auto_pre_agent": False,
    }]
    p["worktree_stashes"] = [
        {
            "worktree_path": f"/tmp/wt-{i}", "worktree_branch": f"codex/x{i}",
            "is_current_project": False, "available": inspeccionables,
            "stash_count": 1, "stashes": [{}],
        }
        for i in range(worktrees)
    ]
    return p


def _por_codigo(findings) -> collections.Counter:
    return collections.Counter(
        getattr(f, "code", getattr(f, "kind", "?")) for f in findings
    )


def test_un_stash_compartido_se_cuenta_UNA_vez(inv):
    """EL HALLAZGO. Trece worktrees viendo el mismo stash producen UN finding.

    Si esto falla con N, volvio el bloqueo duplicado y el preflight vuelve a frenar
    agentes por trabajo que no existe.
    """
    fs = inv.build_findings(_payload(inv, worktrees=13, inspeccionables=True))
    c = _por_codigo(fs)
    assert c.get("linked-worktree-stashes-present", 0) == 0, (
        f"se emitieron {c['linked-worktree-stashes-present']} findings por un stash "
        "COMPARTIDO. Los stashes son por repositorio: verlos desde 13 worktrees no "
        "son 13 hallazgos."
    )
    assert c.get("stash-aged", 0) == 1, (
        "el stash del repo dejo de reportarse: al sacar el duplicado se llevo puesto "
        f"el original. Codigos emitidos: {dict(c)}"
    )


def test_no_haber_podido_inspeccionar_sigue_reportandose(inv):
    """CONTROL SIMETRICO. Sin esto, el arreglo podria haber apagado la senal util.

    "No pude mirar ahi" no es "ahi no hay nada". Es la distincion que esta jornada
    encontro colapsada en la precondicion de chaos, en el secret-detector y en tres
    guards mas.
    """
    fs = inv.build_findings(_payload(inv, worktrees=3, inspeccionables=False))
    c = _por_codigo(fs)
    assert c.get("linked-worktree-stash-uninspectable", 0) == 3, (
        f"un worktree que no se pudo inspeccionar dejo de reportarse: {dict(c)}. "
        "Eso convierte 'no pude verificar' en silencio."
    )


def test_las_dos_ramas_dan_distinto(inv):
    """LA SONDA. Si inspeccionable y no-inspeccionable dieran lo mismo, no discrimina.

    Un test cuyas dos ramas coinciden no prueba el comportamiento: prueba que la
    sonda no esta ejercitando la diferencia.
    """
    ok = _por_codigo(inv.build_findings(_payload(inv, worktrees=3, inspeccionables=True)))
    roto = _por_codigo(inv.build_findings(_payload(inv, worktrees=3, inspeccionables=False)))
    assert ok != roto, (
        "las dos ramas del contrafactico dan el mismo resultado: la sonda no "
        f"discrimina. ok={dict(ok)} roto={dict(roto)}"
    )


def test_el_docstring_sigue_diciendo_que_son_por_repositorio(inv):
    """El motivo del arreglo tiene que sobrevivir en la fuente.

    Si alguien reescribe `collect_stashes_by_worktree` sin ese dato, el proximo lector
    vuelve a creer que hay un stash por worktree y reintroduce el bloqueo duplicado.
    """
    fuente = INV.read_text()
    i = fuente.find("def collect_stashes_by_worktree")
    assert i > 0, "la funcion cambio de nombre; revisar si el arreglo sobrevivio"
    assert "per repository" in fuente[i:i + 900], (
        "el docstring dejo de decir que los stashes son por repositorio, que es "
        "exactamente el dato que evita reintroducir el bloqueo duplicado"
    )
