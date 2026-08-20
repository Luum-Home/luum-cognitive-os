"""El guard de escritura concurrente TOMA un lock, no solo corre.

Origen: 2026-08-19. El hook estaba registrado y llevaba 1.062 invocaciones sin
haber tomado un solo lock. Salia temprano por SESSION_ID vacio: el settings no
exporta COGNITIVE_OS_SESSION_ID y el fallback leia `.current-session-$$`, con el
PID DEL PROPIO HOOK -- un archivo que tendria que haberlo creado un proceso con
ese mismo PID, o sea imposible por construccion. Nunca llegaba al mkdir del
directorio de locks, que por eso ni existia.

Es el guard central de la unica familia que ningun arnes cubre --coordinacion
entre sesiones concurrentes-- y estaba construido y desconectado.

Este test verifica el EFECTO, no la ejecucion: que el lock aparezca en disco. Un
test que solo comprobara "el hook sale 0" habria estado verde durante las 1.062
invocaciones inertes, que es exactamente el genero de test que esta sesion
encontro tres veces defendiendo bugs.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "concurrent-write-guard.sh"


def _correr(proj: Path, session_id: str | None, por_env: bool = False):
    objetivo = proj / "archivo.txt"
    objetivo.write_text("contenido")
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(objetivo)},
    }
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(proj))
    env.pop("COGNITIVE_OS_SESSION_ID", None)
    env.pop("CLAUDE_SESSION_ID", None)
    if session_id is not None:
        if por_env:
            env["COGNITIVE_OS_SESSION_ID"] = session_id
        else:
            payload["session_id"] = session_id
    return subprocess.run(
        ["bash", str(HOOK)], input=json.dumps(payload),
        capture_output=True, text=True, env=env, timeout=30,
    )


def _locks(proj: Path) -> list[Path]:
    d = proj / ".cognitive-os" / "sessions" / "locks"
    return sorted(d.glob("*")) if d.is_dir() else []


@pytest.fixture()
def proyecto(tmp_path: Path) -> Path:
    p = tmp_path / "proyecto"
    (p / ".cognitive-os" / "sessions").mkdir(parents=True)
    return p


def test_toma_el_lock_con_el_session_id_del_payload(proyecto: Path) -> None:
    """La via que el harness usa de verdad: session_id viene en el payload."""
    r = _correr(proyecto, "sesion-A")
    assert r.returncode == 0, r.stderr[-500:]
    assert _locks(proyecto), (
        "no se creo ningun lock. Es la regresion de 2026-08-19: el hook corre, "
        "sale 0, y no toma nada -- indistinguible de funcionar."
    )


def test_tambien_por_variable_de_entorno(proyecto: Path) -> None:
    """La via historica sigue valiendo; el arreglo agrega, no reemplaza."""
    _correr(proyecto, "sesion-B", por_env=True)
    assert _locks(proyecto)


def test_sin_session_id_no_bloquea_ni_explota(proyecto: Path) -> None:
    """Sin identidad de sesion no hay coordinacion posible: salir 0 es correcto.

    Lo que NO es correcto es que ese camino sea el unico alcanzable, que era el
    estado durante 1.062 invocaciones.
    """
    r = _correr(proyecto, None)
    assert r.returncode == 0
    assert not _locks(proyecto)


def test_el_lock_registra_de_quien_es(proyecto: Path) -> None:
    """Un lock sin duenio no sirve para coordinar: el conflicto se decide por sesion."""
    _correr(proyecto, "sesion-C")
    archivos = _locks(proyecto)
    assert archivos
    contenido = " ".join(f.read_text(errors="replace") for f in archivos if f.is_file())
    assert "sesion-C" in contenido, f"el lock no dice de quien es: {contenido[:200]}"
