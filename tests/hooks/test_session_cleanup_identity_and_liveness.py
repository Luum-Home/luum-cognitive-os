# SCOPE: os-only
"""El hook de cleanup tiene que operar sobre la sesion que realmente es.

`hooks/session-cleanup.sh` resolvia su identidad con `COGNITIVE_OS_SESSION_ID`
(que session-init exporta en SU proceso y los hooks, que son hermanos y no
hijos, nunca heredan) y con `.current-session-$$` (escrito con el PID del
escritor, leido con el del lector). Medido sobre 296.383 filas de telemetria:
344 disparos, los 344 saliendo por el `exit 0` de "sin sesion".

Estos tests prueban EFECTO EN DISCO, nunca exit code: el hook sale 0 tanto
cuando hace lo correcto como cuando destruye una sesion viva, y esa es
exactamente la razon por la que el defecto sobrevivio. El test que tapaba el
defecto original exigia `not exists()`; aca lo que se exige es que el
directorio de una sesion VIVA siga existiendo con su contenido.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "session-cleanup.sh"
BASH = "/bin/bash"
SID = "sesion-bajo-prueba"


def _pid_muerto() -> int:
    """Un PID libre de verdad: se arranca, se espera a que muera, se confirma."""
    p = int(subprocess.run(["sh", "-c", "echo $$"], capture_output=True, text=True).stdout)
    for _ in range(50):
        if subprocess.run(["ps", "-p", str(p)], capture_output=True).returncode != 0:
            return p
        time.sleep(0.1)
    pytest.skip("no se pudo conseguir un PID muerto de forma confiable")


def _proyecto(tmp_path: Path, pid: int) -> Path:
    proj = tmp_path / "proj"
    sess = proj / ".cognitive-os" / "sessions" / SID
    (sess / "metrics").mkdir(parents=True)
    (proj / ".cognitive-os" / "metrics").mkdir(parents=True)
    (sess / "metrics" / "skill-metrics.jsonl").write_text('{"m":1}\n{"m":2}\n')
    (sess / "subagent-tool-calls-agentX").write_text("LIVE\n")
    (sess / "meta.json").write_text(json.dumps({"session_id": SID, "pid": pid}))
    (proj / ".cognitive-os" / "sessions" / "active-sessions.json").write_text(
        json.dumps({"sessions": [{"id": SID}]})
    )
    return proj


def _correr(proj: Path, **env_extra) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for k in ("COGNITIVE_OS_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID",
              "COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR"):
        env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(proj)
    env.update(env_extra)
    return subprocess.run([BASH, str(HOOK)], input="", capture_output=True,
                          text=True, env=env, cwd=str(proj), timeout=60)


def _sess(proj: Path) -> Path:
    return proj / ".cognitive-os" / "sessions" / SID


def _archivo(proj: Path) -> Path:
    return proj / ".cognitive-os" / "archive" / "sessions" / SID


def _registradas(proj: Path) -> list:
    raw = (proj / ".cognitive-os" / "sessions" / "active-sessions.json").read_text()
    return [s["id"] for s in json.loads(raw)["sessions"]]


# ─── Direccion 1: sesion VIVA — no se toca nada ──────────────────────────────

def test_sesion_viva_sobrevive_al_stop(tmp_path):
    """Stop dispara POR TURNO (hasta 41 veces por ventana, medido).

    La sesion en la que el hook corre esta viva por construccion, y el PID de
    meta.json no puede desmentirlo: session-init.sh:29 escribe ahi su propio
    `$$`, el de un subproceso que vive segundos. Las 10 sesiones en disco dan
    ese PID como muerto, una de ellas mientras su sesion seguia abierta.
    """
    proj = _proyecto(tmp_path, _pid_muerto())   # PID muerto a proposito
    r = _correr(proj, CLAUDE_CODE_SESSION_ID=SID)

    assert r.returncode == 0, r.stderr
    assert _sess(proj).is_dir(), "se retiro el directorio de una sesion VIVA"
    assert (_sess(proj) / "subagent-tool-calls-agentX").read_text() == "LIVE\n", (
        "se perdio estado vivo del enforcer de presupuesto"
    )
    assert not _archivo(proj).exists(), "se archivo una sesion viva"
    assert _registradas(proj) == [SID], (
        "se deregistro una sesion viva: el paso 2 corria sin guard alguno"
    )


def test_sesion_viva_sobrevive_a_stops_repetidos(tmp_path):
    """41 disparos en una ventana era el maximo medido; se prueban 5."""
    proj = _proyecto(tmp_path, _pid_muerto())
    for _ in range(5):
        assert _correr(proj, CLAUDE_CODE_SESSION_ID=SID).returncode == 0
    assert _sess(proj).is_dir()
    assert _registradas(proj) == [SID]


# ─── Direccion 2: duenio PROBADAMENTE muerto — se archiva, se mergea una vez ─

def _proyecto_muerto(tmp_path) -> Path:
    proj = _proyecto(tmp_path, _pid_muerto())
    # Fuera de la ventana de gracia por mtime.
    os.utime(_sess(proj), (1, 1))
    return proj


def test_duenio_muerto_se_archiva_segun_adr119(tmp_path):
    proj = _proyecto_muerto(tmp_path)
    r = _correr(proj, COGNITIVE_OS_SESSION_ID=SID, CLAUDE_CODE_SESSION_ID="otra-sesion")

    assert r.returncode == 0, r.stderr
    assert not _sess(proj).exists()
    assert _archivo(proj).is_dir(), "ADR-119 manda archive-first, no borrado"
    assert (_archivo(proj) / "subagent-tool-calls-agentX").read_text() == "LIVE\n", (
        "el archivado tiene que preservar el contenido, no destruirlo"
    )
    assert _registradas(proj) == []


def test_el_merge_de_metricas_es_incremental_por_offset(tmp_path):
    """Con Stop por turno, un merge no incremental deja N copias de cada fila."""
    proj = _proyecto_muerto(tmp_path)
    glob = proj / ".cognitive-os" / "metrics" / "skill-metrics.jsonl"

    _correr(proj, COGNITIVE_OS_SESSION_ID=SID, CLAUDE_CODE_SESSION_ID="otra-sesion")
    primero = glob.read_text()
    assert primero.count("\n") == 2, f"merge inicial mal: {primero!r}"

    for _ in range(3):
        _correr(proj, COGNITIVE_OS_SESSION_ID=SID, CLAUDE_CODE_SESSION_ID="otra-sesion")
    assert glob.read_text() == primero, "el merge duplico filas al reejecutarse"


def test_el_hook_no_se_toma_a_si_mismo_como_prueba_de_vida(tmp_path):
    """El merge crea $SESSION_DIR/.merge-offsets y con eso mueve el mtime.

    Si el veredicto de vitalidad se evaluara DESPUES del merge, la ventana de
    gracia veria la escritura de este mismo hook y concluiria "hay alguien
    vivo". Se detecto corriendo la prueba B del contrafactico.
    """
    proj = _proyecto_muerto(tmp_path)
    _correr(proj, COGNITIVE_OS_SESSION_ID=SID, CLAUDE_CODE_SESSION_ID="otra-sesion")
    assert _archivo(proj).is_dir(), (
        "el hook se declaro a si mismo prueba de vida de la sesion que limpia"
    )


def test_sesion_ajena_tocada_hace_poco_se_considera_viva(tmp_path):
    """PID muerto NO alcanza: puede ser el efimero de session-init."""
    proj = _proyecto(tmp_path, _pid_muerto())   # mtime = ahora
    _correr(proj, COGNITIVE_OS_SESSION_ID=SID, CLAUDE_CODE_SESSION_ID="otra-sesion")
    assert _sess(proj).is_dir(), (
        "se retiro una sesion escrita hace segundos por un PID efimero muerto"
    )


# ─── La identidad, medida: a que directorio apunta ───────────────────────────

def test_la_identidad_sale_de_claude_code_session_id(tmp_path):
    """`CLAUDE_SESSION_ID` (sin CODE) no existe en el arnes; la real es la otra."""
    proj = _proyecto_muerto(tmp_path)
    _correr(proj, CLAUDE_CODE_SESSION_ID="otra", CLAUDE_SESSION_ID=SID)
    # Resolvio "otra", que no tiene directorio -> no toco el de SID.
    assert _sess(proj).is_dir(), "gano CLAUDE_SESSION_ID, que el arnes no setea"


def test_sin_ninguna_identidad_el_hook_no_hace_nada(tmp_path):
    proj = _proyecto(tmp_path, _pid_muerto())
    r = _correr(proj)
    assert r.returncode == 0
    assert _sess(proj).is_dir()
    assert _registradas(proj) == [SID]
