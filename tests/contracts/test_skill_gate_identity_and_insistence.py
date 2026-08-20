# SCOPE: os-only
"""Contrato de la cadena de identidad + politica de insistencia del gate ADR-188.

Por que existe este archivo, y no una linea mas en el contrato viejo.

El gate `hooks/orchestrator-skill-invocation-gate.sh` estuvo 94 dias con cero
verdaderos positivos. La cadena tenia dos cortes y los dos habia que arreglarlos
juntos, porque arreglar uno solo deja el gate *igual de verde y mas inerte*:

  - el productor (`hooks/skill-router-prompt-suggest.sh`) escribia
    `session_id: "unknown"` para todos, asi que las 584 filas del log compartian
    UNA clave;
  - el consumidor (`cos_lib.skill_router.last_suggestion`) anclaba en el ultimo
    `user_prompt_submit` de la sesion; para `unknown` no habia ancla, tomaba el
    log entero y se quedaba con el maximo historico de confianza — una fila de
    julio exigida durante 48 dias.

Arreglar solo el consumidor deja `last_suggestion(<id real>)` devolviendo `None`
para todo id, porque el productor nunca escribio esa identidad: exit 0 siempre.
Por eso los tests de aca prueban la cadena PUNTA A PUNTA, corriendo el hook de
verdad, y no la funcion sola.

Los tests que empiezan con `test_mutante_` estan escritos para MATAR mutantes
concretos de la conducta que se agrego el 2026-08-20; se corren en lote con
`python3 scripts/mutation_check_skill_gate.py`.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.utils.harness_payload import payload, without  # noqa: E402

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
# Override para el corredor de mutacion: apunta el contrato a una COPIA mutada
# del hook sin tocar el original.
HOOK = Path(os.environ.get("COS_SKILL_GATE_HOOK") or (REPO_ROOT / "hooks" / "orchestrator-skill-invocation-gate.sh"))

SESSION = "sess-real-2026-08-20"


def _now(offset_seconds: float = 0.0) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=offset_seconds)).isoformat()


def _seed(
    workdir: Path,
    *,
    session_id: str | None,
    skill: str,
    confidence: float,
    ts: str | None = None,
    prompt_hash: str = "hash-aaaa",
) -> dict:
    metrics = workdir / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": ts or _now(),
        "session_id": session_id,
        "prompt_hash": prompt_hash,
        "skill_name": skill,
        "invoke_command": f"/{skill}",
        "confidence": confidence,
        "threshold_met": confidence >= 0.80,
    }
    with (metrics / "skill-suggestion.jsonl").open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def _run(
    workdir: Path,
    *,
    tool_name: str = "Agent",
    tool_input: dict | None = None,
    session_id: str | None = SESSION,
    env_extra: dict | None = None,
) -> subprocess.CompletedProcess:
    # El sobre lo arma el constructor fiel: un payload de dos campos hace que
    # el hook decida sobre menos informacion de la que el arnes le manda.
    # El caso "sin identidad" se expresa quitando `session_id` de un payload
    # completo, no omitiendo los otros cinco campos por descuido.
    body: dict = dict(tool_name=tool_name, tool_input=tool_input or {"prompt": "trabajo a medida"})
    if session_id is None:
        envelope = without("PreToolUse", "session_id", cwd=workdir, **body)
    else:
        envelope = payload("PreToolUse", cwd=workdir, session_id=session_id, **body)

    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(workdir)
    env["CLAUDE_PROJECT_DIR"] = str(workdir)
    # Higiene de entorno heredado. El conftest de la raiz redirige COS_METRICS_DIR
    # a un sandbox compartido; este contrato mide el destino derivado de
    # PROJECT_DIR, asi que descarta el redirect. Y descarta la identidad de la
    # sesion que CORRE los tests: si no, un caso "sin identidad" la heredaria y
    # probaria lo contrario de lo que dice su nombre.
    for var in (
        "COS_METRICS_DIR",
        "COGNITIVE_OS_METRICS_DIR",
        # La lista COMPLETA de la cadena de cos_session_id(), no las dos que uno
        # recuerda. `CLAUDE_CODE_SESSION_ID` es la que el arnes exporta de
        # verdad (env-vars.md:339) y es la que se filtraba: sin sacarla, un caso
        # "sin identidad" heredaba la sesion que CORRE los tests y probaba lo
        # contrario de lo que dice su nombre.
        "COGNITIVE_OS_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_HOST_SESSION_ID",
        "CODEX_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "COS_ALLOW_SKILL_BYPASS",
        "COS_SKILL_BYPASS_REASON",
        "COS_SKILL_SUGGESTION_TTL_SECONDS",
        "COS_SKILL_GATE_INSIST_THRESHOLD",
        "DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE",
    ):
        env.pop(var, None)
    if session_id is not None:
        env["COGNITIVE_OS_SESSION_ID"] = session_id
    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(envelope),
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )


def _audit(workdir: Path) -> list[dict]:
    path = workdir / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _anon(workdir: Path) -> list[dict]:
    path = workdir / ".cognitive-os" / "metrics" / "anonymous" / "skill-bypass-anonymous.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    (tmp_path / "cos_lib").mkdir()
    shutil.copy(REPO_ROOT / "cos_lib" / "skill_router.py", tmp_path / "cos_lib" / "skill_router.py")
    (tmp_path / "cos_lib" / "__init__.py").write_text("")
    return tmp_path


# ─── Caso 1: con identidad real, una sugerencia del prompt actual OBLIGA ─────


def test_identidad_real_obliga_y_bloquea_al_tercer_envio(workdir: Path):
    """Lo que el gate no pudo hacer ni una vez en 94 dias.

    Tres ENVIOS del mismo prompt (tres filas con `ts` distinto y el mismo
    `prompt_hash`), la skill nunca invocada ni anotada: aviso, aviso, BLOCK.
    """
    for i in range(3):
        _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95, ts=_now(i))
        res = _run(workdir)
        if i < 2:
            assert res.returncode == 0, res.stderr
            assert "WARN" in res.stderr
            assert f"({i + 1}/3" in res.stderr, res.stderr
        else:
            assert res.returncode == 2, f"el tercer envio tiene que bloquear: {res.stderr}"
            assert "BLOCK" in res.stderr

    filas = _audit(workdir)
    assert [f["outcome"] for f in filas] == ["bypass-unannotated", "bypass-unannotated", "blocked"]
    assert {f["session_id"] for f in filas} == {SESSION}, "la auditoria tiene que llevar la identidad real"


# ─── Caso 2: una sugerencia vieja NO obliga ──────────────────────────────────


def test_sugerencia_de_hace_40_dias_no_obliga(workdir: Path):
    """El bug medido: una fila de julio con 0.99 se exigia en agosto.

    Es de alta confianza y es de la MISMA sesion; lo unico que la descalifica es
    la edad. Si el TTL desaparece, este test cae.
    """
    vieja = _now(-40 * 24 * 3600)
    _seed(workdir, session_id=SESSION, skill="repo-forensics", confidence=0.99, ts=vieja)

    res = _run(workdir)
    assert res.returncode == 0, res.stderr
    assert "WARN" not in res.stderr
    assert _audit(workdir) == []


def test_sugerencia_vieja_no_gana_sobre_la_del_turno(workdir: Path):
    """La fila vieja tiene MAS confianza que la actual y aun asi no gana.

    Este es el escenario exacto del bug: el consumidor se quedaba con el maximo
    de confianza de todo el log. Con la ventana del turno, la que manda es la
    del prompt actual aunque puntue mas bajo.
    """
    _seed(workdir, session_id=SESSION, skill="repo-forensics", confidence=0.99,
          ts=_now(-40 * 24 * 3600), prompt_hash="hash-vieja")
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.93,
          ts=_now(), prompt_hash="hash-actual")

    res = _run(workdir)
    assert res.returncode == 0
    assert "repo-scout" in res.stderr, res.stderr
    assert "repo-forensics" not in res.stderr


# ─── Caso 3: la politica nueva, en sus dos mitades ───────────────────────────


def test_repetir_el_mismo_prompt_escala_y_cambiarlo_libera(workdir: Path):
    """Las dos mitades de la politica aprobada por el operador.

    Insistir con el MISMO prompt escala hasta el bloqueo; reformular la pedida
    vuelve el contador a cero — sin barrido ni comando de reset, porque el hash
    es parte del nombre del archivo de estado.
    """
    for i in range(2):
        _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95,
              ts=_now(i), prompt_hash="hash-insistente")
        assert _run(workdir).returncode == 0

    # Tercer envio del MISMO prompt -> BLOCK.
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95,
          ts=_now(2), prompt_hash="hash-insistente")
    assert _run(workdir).returncode == 2

    # Otro prompt, misma skill de alta confianza -> vuelve a 1/3.
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95,
          ts=_now(3), prompt_hash="hash-reformulado")
    res = _run(workdir)
    assert res.returncode == 0, f"cambiar de prompt tiene que liberar: {res.stderr}"
    assert "(1/3" in res.stderr, res.stderr


def test_muchas_tool_calls_del_mismo_envio_cuentan_una(workdir: Path):
    """La unidad es el ENVIO, no la herramienta.

    Es la diferencia entre medir insistencia y medir actividad: el contador
    viejo sumaba una unidad por tool call y por eso llego a 143.
    """
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95, ts=_now())
    for _ in range(6):
        res = _run(workdir)
        assert res.returncode == 0, res.stderr
        assert "(1/3" in res.stderr, res.stderr

    assert len(_audit(workdir)) == 1, "una fila de auditoria por envio, no por herramienta"


# ─── Caso 5: el contador latcheado de 143 no escala en el diseno nuevo ───────


def test_contador_viejo_de_143_no_tiene_efecto(workdir: Path):
    """El estado del operador queda en disco y nadie lo lee.

    `skill-bypass-counter-<sesion>` nacio el 2026-05-18 y llego a 143 contra un
    umbral de 3, sin codigo de reset: latcheado en BLOCK para siempre. No se
    borra —su existencia es la evidencia— pero ningun camino de codigo lo mira.
    """
    runtime = workdir / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    legacy = runtime / f"skill-bypass-counter-{SESSION}"
    legacy.write_text("143")

    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95, ts=_now())
    res = _run(workdir)

    assert res.returncode == 0, f"un contador viejo no puede bloquear: {res.stderr}"
    assert "(1/3" in res.stderr, res.stderr
    assert legacy.read_text() == "143", "el contador viejo se deja intacto, no se borra ni se pisa"


# ─── Mutantes ────────────────────────────────────────────────────────────────


def test_mutante_abstencion_sin_sesion_no_bloquea(workdir: Path):
    """M1. Sin identidad probada el gate NO decide, y no decidir es no bloquear.

    Un veredicto sin sujeto no es un veredicto. Si la abstencion se vuelve
    bloqueo, todo payload sin `session_id` —un test, una sonda de portabilidad,
    un replay— queda bloqueado.
    """
    _seed(workdir, session_id=None, skill="repo-scout", confidence=0.99, ts=_now())
    res = _run(workdir, session_id=None)
    assert res.returncode == 0, res.stderr
    assert "BLOCK" not in res.stderr


def test_mutante_abstencion_sin_sesion_deja_rastro(workdir: Path):
    """M2 y M3. La abstencion se registra en un bucket anonimo EXPLICITO.

    Una guarda que evalua y no registra es indistinguible de una guarda rota.
    Este test tambien mata el mutante que restaura `SESSION_ID="unknown"`: con
    la clave fabricada el hook nunca entra en la rama de abstencion, asi que la
    fila anonima no aparece.
    """
    _seed(workdir, session_id=None, skill="repo-scout", confidence=0.99, ts=_now())
    res = _run(workdir, session_id=None)
    assert res.returncode == 0, res.stderr

    filas = _anon(workdir)
    assert len(filas) == 1, f"falta el rastro de la abstencion: {filas}"
    assert filas[0]["session_id"] is None
    assert filas[0]["outcome"] == "abstained"
    assert filas[0]["tool_name"] == "Agent"
    # Y no contamina el log que consume scripts/skill_adherence_loop.py.
    assert _audit(workdir) == []


def test_mutante_sin_sesion_no_cae_en_el_bucket_unknown(workdir: Path):
    """M3. `unknown` no es "sin identidad": es una clave compartida.

    Se siembra la trampa exacta de produccion — una sugerencia 0.99 fresca
    escrita bajo `session_id: "unknown"` y el contador `-unknown` en 143. Si el
    hook vuelve a fabricar la clave, encuentra esa sugerencia y decide con
    estado ajeno.
    """
    runtime = workdir / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "skill-bypass-counter-unknown").write_text("143")
    _seed(workdir, session_id="unknown", skill="repo-forensics", confidence=0.99, ts=_now())

    res = _run(workdir, session_id=None)

    assert res.returncode == 0, res.stderr
    assert "repo-forensics" not in res.stderr
    assert _audit(workdir) == [], "no se decide con la identidad de nadie"
    assert len(_anon(workdir)) == 1
    assert not list(runtime.glob("skill-gate-insist-unknown*"))


def test_mutante_filtro_de_tool_name(workdir: Path):
    """M4. El gate gobierna Agent/Bash/task/delegate, no toda herramienta.

    Se deja el contador a un envio del umbral: si el filtro desaparece, un
    `Read` empuja al bloqueo y el test cae por returncode.
    """
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95, ts=_now(0))
    assert _run(workdir).returncode == 0
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95, ts=_now(1))
    assert _run(workdir).returncode == 0  # 2/3

    antes = len(_audit(workdir))
    _seed(workdir, session_id=SESSION, skill="repo-scout", confidence=0.95, ts=_now(2))
    res = _run(workdir, tool_name="Read", tool_input={"file_path": "x.txt"})

    assert res.returncode == 0, f"Read no esta gobernado por el gate: {res.stderr}"
    assert res.stderr == "", res.stderr
    assert len(_audit(workdir)) == antes, "un tool no gobernado no escribe auditoria"
