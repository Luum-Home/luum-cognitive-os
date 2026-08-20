# SCOPE: os-only
"""La telemetria del operador no la escribe un test.

Prueba las dos capas del conftest de la raiz y el arreglo de identidad del gate
de ADR-188. Ver `conftest.py` en la raiz para el porque.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests.utils.harness_payload import without  # noqa: E402
HOOKS = sorted((REPO / "hooks").glob("*.sh"))
GATE = REPO / "hooks" / "orchestrator-skill-invocation-gate.sh"
SCOPE_GATE = REPO / "hooks" / "scope-marker-portability-gate.sh"


def _root_conftest():
    """Importa el conftest de la raiz como modulo para probar sus funciones.

    No se puede `import conftest`: pytest ya lo tiene cargado como plugin con
    otro nombre, y el de `tests/` colisiona.
    """
    spec = importlib.util.spec_from_file_location("_cos_root_conftest", REPO / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# ─── Capa 2: deteccion por filesystem ────────────────────────────────────────


def test_guard_catches_a_hand_written_direct_append(tmp_path: Path) -> None:
    """La escritura que NO pasa por ningun helper del repo tambien se atrapa.

    Este es el caso que un interceptor de `subprocess` o de una funcion helper
    deja pasar: un `open(..., "a")` en el propio proceso del test. La capa 2 mira
    el filesystem, asi que no lo distingue de cualquier otra escritura — que es
    exactamente la propiedad que se le pide.
    """
    conftest = _root_conftest()
    metrics = tmp_path / "metrics"
    metrics.mkdir()
    (metrics / "skill-bypass.jsonl").write_text('{"ts": "x"}\n', encoding="utf-8")

    before = conftest.fingerprint_metrics_dir(metrics)

    with open(metrics / "skill-bypass.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"ts": "escrito a mano, sin helper"}\n')

    after = conftest.fingerprint_metrics_dir(metrics)
    grew = conftest.diff_growth(before, after)

    assert [name for name, _, _ in grew] == ["skill-bypass.jsonl"]
    assert grew[0][2] > grew[0][1]


def test_guard_catches_a_brand_new_file(tmp_path: Path) -> None:
    """Estrenar un .jsonl en el directorio del operador tambien es escribir."""
    conftest = _root_conftest()
    metrics = tmp_path / "metrics"
    metrics.mkdir()
    before = conftest.fingerprint_metrics_dir(metrics)
    (metrics / "inventado.jsonl").write_text("{}\n", encoding="utf-8")
    grew = conftest.diff_growth(before, conftest.fingerprint_metrics_dir(metrics))
    assert grew == [("inventado.jsonl", 0, 3)]


def test_guard_does_not_flag_rotation(tmp_path: Path) -> None:
    """Un archivo que ENCOGIO es rotacion, no escritura de un test.

    Sin esta distincion el guard se dispararia con el rotador de metricas del
    propio SO y seria ruido, que es como se termina apagando un gate.
    """
    conftest = _root_conftest()
    metrics = tmp_path / "metrics"
    metrics.mkdir()
    target = metrics / "grande.jsonl"
    target.write_text("x" * 500, encoding="utf-8")
    before = conftest.fingerprint_metrics_dir(metrics)
    target.write_text("x" * 10, encoding="utf-8")
    assert conftest.diff_growth(before, conftest.fingerprint_metrics_dir(metrics)) == []


def test_sandbox_env_is_exported_to_every_test() -> None:
    """Capa 1: el redirect lo hereda cualquier subproceso, sin parchear Popen."""
    sandbox = os.environ.get("COS_METRICS_DIR", "")
    assert sandbox, "el conftest de la raiz no exporto COS_METRICS_DIR"
    assert not sandbox.startswith(str(REPO / ".cognitive-os" / "metrics"))


# ─── Ratchets: la clase, no el caso ──────────────────────────────────────────

_FABRICATES_IDENTITY = re.compile(
    r'SESSION_ID[^=\n]*=[^\n]*"(?:unknown|anonymous|default|none)"'
)
# Estado indexado por identidad que NO es un directorio por sesion: contadores y
# marcadores sueltos bajo `runtime/` o `/tmp`. Es la forma que presta estado
# entre procesos distintos, porque la clave es un nombre de archivo compartido.
_KEYS_LOOSE_STATE_ON_IDENTITY = re.compile(
    r'^\s*[A-Za-z_]+="(?:[^"\n]*(?:RUNTIME_DIR|/tmp)[^"\n]*)-\$\{?SESSION_ID\}?"',
    re.MULTILINE,
)


def _code_only(text: str) -> str:
    """Descarta lineas de comentario.

    Los ratchets buscan formas de CODIGO. Sin esto, el comentario que explica
    por que se saco `SESSION_ID="unknown"` hace fallar al ratchet que verifica
    que ya no este — el gate se muerde la cola con su propia documentacion.
    """
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def test_no_hook_keys_governing_state_on_a_fabricated_identity() -> None:
    """La clase cerrada, no solo el agujero.

    Medido el 2026-08-20: 30 hooks fabricaban una identidad de reemplazo, pero
    solo UNO la usaba para indexar estado persistente que decide
    (`orchestrator-skill-invocation-gate.sh`, contador -> BLOCK). En los otros 29
    el valor fabricado es una ETIQUETA en una fila de log: arruina la atribucion,
    no presta estado.

    Este ratchet impide que aparezca un segundo. Fabricar la etiqueta sigue
    permitido; lo que no se puede es fabricar la etiqueta Y ademas usarla como
    clave de un archivo de estado SUELTO (contador/marcador bajo `runtime/` o
    `/tmp`), que es la forma que presta estado entre procesos.

    Ceguera declarada: no cubre `~/.cognitive-os/sessions/$SESSION_ID/...`. Ahi
    la identidad fabricada tambien crea un bucket compartido (`sessions/unknown/`)
    y hay 7 hooks en esa forma —completion-gate, post-agent-verify,
    pre-agent-snapshot, rate-limit-detector, state-heartbeat, session-learning,
    agent-launch-confirmed—, pero ninguno se audito todavia para saber si LEE ese
    estado para decidir o solo escribe log ahi. Cerrarlo requiere auditar los 7;
    queda escrito en el informe, no tapado con un assert que no midio nada.
    """
    offenders = []
    for hook in HOOKS:
        text = _code_only(hook.read_text(encoding="utf-8", errors="replace"))
        if _FABRICATES_IDENTITY.search(text) and _KEYS_LOOSE_STATE_ON_IDENTITY.search(text):
            offenders.append(hook.name)
    assert offenders == [], (
        "estos hooks fabrican una identidad y ademas la usan como clave de estado "
        f"en disco, que es el bucket por defecto compartido: {offenders}"
    )


def test_cos_metrics_dir_adoption_only_goes_up() -> None:
    """Piso de adopcion de COS_METRICS_DIR entre los hooks que escriben metricas.

    Medido el 2026-08-20: 3 de 111. El numero es bajo y por eso hace falta la
    capa 2 del guard. El ratchet existe para que el proximo hook que escriba
    metricas nazca honrando la convencion en vez de hardcodear la ruta.
    """
    writers = [h for h in HOOKS if "cognitive-os/metrics" in h.read_text(errors="replace")]
    honoring = [h for h in writers if "COS_METRICS_DIR" in h.read_text(errors="replace")]
    assert len(writers) >= 100, "cambio la poblacion; revisar el censo antes de tocar el piso"
    assert len(honoring) >= 4, (
        f"solo {len(honoring)}/{len(writers)} hooks honran COS_METRICS_DIR. "
        "El piso baja unicamente con una decision escrita, no para apagar un rojo."
    )


# ─── El gate: las dos direcciones ────────────────────────────────────────────


def _run_gate(env_extra: dict, payload: dict, cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # La cadena COMPLETA de cos_session_id(), no las dos que uno recuerda.
    # `CLAUDE_CODE_SESSION_ID` es la que el arnes exporta de verdad
    # (env-vars.md:339); sin sacarla, este test hereda la sesion que CORRE la
    # suite, el gate resuelve identidad y deja de probar el caso anonimo.
    for key in (
        "COGNITIVE_OS_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_HOST_SESSION_ID",
        "CODEX_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "COS_ALLOW_SKILL_BYPASS",
    ):
        env.pop(key, None)
    env["DISABLE_HOOK_ORCHESTRATOR_SKILL_INVOCATION_GATE"] = "0"
    env.update(env_extra)
    return subprocess.run(
        ["/bin/bash", str(GATE)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(cwd),
        timeout=25,
        check=False,
    )


def test_payload_without_identity_cannot_touch_operator_state(tmp_path: Path) -> None:
    """La contaminacion, cerrada: sin identidad no se lee ni se escribe lo ajeno.

    Se invoca al hook EXACTAMENTE como lo hacia el llamador que contamino: sin
    `session_id` en el payload, sin override de PROJECT_DIR y con cwd en el
    repo, para que `git rev-parse --show-toplevel` resuelva al repo real. Antes
    de este arreglo esa llamada leia e incrementaba
    `.cognitive-os/runtime/skill-bypass-counter-unknown` y agregaba una fila a
    `.cognitive-os/metrics/skill-bypass.jsonl`.
    """
    counter = REPO / ".cognitive-os" / "runtime" / "skill-bypass-counter-unknown"
    audit = REPO / ".cognitive-os" / "metrics" / "skill-bypass.jsonl"
    counter_before = counter.read_bytes() if counter.exists() else None
    audit_before = audit.stat().st_size if audit.exists() else None

    anon_root = tmp_path / "metrics"
    result = _run_gate(
        {"COS_METRICS_DIR": str(anon_root)},
        without("PreToolUse", "session_id", tool_name="Bash",
                tool_input={"command": "echo hola"}, cwd=REPO),
        cwd=REPO,
    )

    assert result.returncode == 0, f"el gate decidio sin sujeto: {result.stderr}"

    counter_after = counter.read_bytes() if counter.exists() else None
    audit_after = audit.stat().st_size if audit.exists() else None
    assert counter_after == counter_before, "el payload anonimo movio el contador del operador"
    assert audit_after == audit_before, "el payload anonimo escribio en la auditoria del operador"

    rows = (anon_root / "anonymous" / "skill-bypass-anonymous.jsonl").read_text(encoding="utf-8")
    entry = json.loads(rows.strip().splitlines()[-1])
    assert entry["outcome"] == "abstained"
    assert entry["session_id"] is None


def test_the_fabricated_identity_is_gone_from_the_gate() -> None:
    """Nadie vuelve a poner `unknown` como clave: el verde barato de esta parte."""
    text = _code_only(GATE.read_text(encoding="utf-8"))
    assert '[ -z "$SESSION_ID" ] && SESSION_ID="unknown"' not in text
    assert 'SESSION_ID="unknown"' not in text
    assert 'SESSION_ID:-unknown' not in text

    # 2026-08-20 — el contador por sesion no "perdio el unknown": desaparecio.
    # Sumaba +1 por tool call de por vida y sin reset, asi que llego a 143 contra
    # un umbral de 3 y quedo latcheado desde el 2026-05-18. Lo reemplaza un
    # contador de insistencia cuya CLAVE incluye el prompt_hash, que es lo que
    # hace que el reset sea estructural: cambiar de prompt cambia el archivo.
    assert "skill-bypass-counter-" not in text, (
        "el contador de por vida volvio al codigo; era el mecanismo latcheado"
    )
    insist = [ln for ln in text.splitlines() if "skill-gate-insist-" in ln and "=" in ln]
    assert insist, "desaparecio el contador de insistencia; revisar este test antes que el hook"
    assert "_gate_key" in insist[0], (
        "la clave del contador tiene que incluir el prompt_hash, o vuelve a ser "
        "un acumulado por sesion con otro nombre"
    )
    assert "PROMPT_HASH" in text


# ─── ADR-241: cos_bypass_audit y el directorio de metricas ──────────────────


def _run_scope_gate_with_bypass(sandbox: Path) -> subprocess.CompletedProcess:
    """Ejerce un bypass real via `scope-marker-portability-gate.sh`.

    Este hook llama `cos_bypass_audit` (definida en `hooks/_lib/bypass-resolver.sh`)
    cuando `unproven_scope_both` esta activo. Es el mismo camino que dispara
    cualquier `git commit` real con el bypass prendido -- no un stub.
    """
    env = os.environ.copy()
    env.pop("COS_BYPASS", None)
    env["COS_METRICS_DIR"] = str(sandbox)
    env["COS_ALLOW_UNPROVEN_SCOPE_BOTH"] = "1"
    env["COS_UNPROVEN_SCOPE_REASON"] = "test_bypass_audit_honors_cos_metrics_dir"
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m test"}}
    return subprocess.run(
        ["/bin/bash", str(SCOPE_GATE)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(REPO),
        timeout=25,
        check=False,
    )


def test_bypass_audit_honors_cos_metrics_dir(tmp_path: Path) -> None:
    """`cos_bypass_audit` no puede tocar la telemetria REAL del operador.

    Medido el 2026-08-20 antes del arreglo: ejercer este mismo bypass con
    `COS_METRICS_DIR` apuntado a un temporal igual escribia +231 bytes
    deterministas en `.cognitive-os/metrics/bypass-activation.jsonl` -- el
    temporal quedaba con la metrica del hook (que si honra la variable) pero
    NO con la auditoria del bypass, que `hooks/_lib/bypass-resolver.sh:76`
    calculaba a mano con `_cos_bypass_project_dir()/.cognitive-os/metrics`.

    La trampa a evitar: si este test derivara la ruta esperada con ese mismo
    criterio (`_cos_bypass_project_dir()/.cognitive-os/metrics`), un bug en
    ese calculo certificaria en verde exactamente lo que hay que vigilar. Por
    eso la asercion viene de una fuente distinta: `conftest.fingerprint_metrics_dir`
    mira el filesystem REAL de `.cognitive-os/metrics/` con `os.scandir` --
    la misma capa 2 que ya prueba `test_guard_catches_a_hand_written_direct_append`
    mas arriba -- sin pasar por ninguna funcion de `bypass-resolver.sh`.
    """
    conftest = _root_conftest()
    operator_metrics = REPO / ".cognitive-os" / "metrics"
    before = conftest.fingerprint_metrics_dir(operator_metrics)

    sandbox = tmp_path / "sandboxed-metrics"
    sandbox.mkdir()
    result = _run_scope_gate_with_bypass(sandbox)
    assert result.returncode == 0, f"el hook no corrio limpio: {result.stderr}"

    after = conftest.fingerprint_metrics_dir(operator_metrics)
    grew = conftest.diff_growth(before, after)
    assert grew == [], (
        "cos_bypass_audit escribio en la telemetria REAL del operador aunque "
        f"COS_METRICS_DIR apuntaba a un sandbox: {grew}"
    )

    sandboxed_audit = sandbox / "bypass-activation.jsonl"
    assert sandboxed_audit.exists(), (
        "el bypass no dejo auditoria en NINGUN lado -- eso no prueba aislamiento, "
        "prueba que cos_bypass_audit no corrio"
    )
    row = json.loads(sandboxed_audit.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["bypass_key"] == "unproven_scope_both"
    assert row["hook"] == "scope-marker-portability-gate"


# ---------------------------------------------------------------------------
# Discriminador ruido-de-operador vs escritura-de-la-suite (2026-08-20)
#
# El gate cazo dos crecimientos y los reporto IDENTICOS:
#     coverage-history.jsonl  +2910   <- lo escribia la suite
#     session-watchdog.jsonl   +335   <- crece sola, daemon con PPID=1
# Medido en una ventana ociosa de 20s sin un solo test: el primero +0, el
# segundo +335. Un gate que grita por ruido propio del operador se bypassea, y
# el hallazgo real se va con el bypass.
#
# El riesgo del arreglo es simetrico y peor: al callar el falso positivo se
# puede callar tambien el verdadero, y las dos cosas producen la MISMA salida
# verde. Por eso la primera prueba de abajo es la que tiene que quedar roja si
# alguien afloja el discriminador.
# ---------------------------------------------------------------------------


def test_un_escritor_no_mapeado_sigue_fallando_el_gate() -> None:
    """LA FALSACION. Un crecimiento sin daemon que lo reclame es 'suite', no 'ruido'.

    Si esto se pone verde del lado equivocado, el discriminador dejo de
    discriminar y el gate quedo apagado con cara de arreglado.
    """
    conftest = _root_conftest()
    noise, suite = conftest._classify_growth([("unmapped-writer.jsonl", 100, 400)])
    assert noise == [], f"acredito como ruido a un escritor que nadie reclama: {noise}"
    assert suite == [("unmapped-writer.jsonl", 100, 400)]


def test_un_daemon_ajeno_y_vivo_cuenta_como_ruido(tmp_path: Path) -> None:
    """El caso legitimo: proceso vivo, cmdline que coincide, ajeno a esta corrida."""
    conftest = _root_conftest()
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)  # marcador_daemon_de_prueba"]
    )
    try:
        (tmp_path / "falso.pid").write_text(str(proc.pid), encoding="utf-8")
        ok, why = conftest._daemon_owns_this_growth(
            "falso.jsonl",
            runtime_dir=tmp_path,
            pidfile_map={"falso.jsonl": ("falso.pid", "marcador_daemon_de_prueba")},
        )
        assert ok, f"no acredito un daemon vivo, ajeno y con cmdline coincidente: {why}"
        assert str(proc.pid) in why
    finally:
        proc.kill()
        proc.wait(timeout=10)


def test_un_pid_muerto_cae_al_bucket_estricto(tmp_path: Path) -> None:
    """Falla cerrada: 'no pude verificar' NUNCA es 'es ruido del operador'."""
    conftest = _root_conftest()
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(timeout=10)
    (tmp_path / "muerto.pid").write_text(str(proc.pid), encoding="utf-8")
    ok, _ = conftest._daemon_owns_this_growth(
        "muerto.jsonl",
        runtime_dir=tmp_path,
        pidfile_map={"muerto.jsonl": ("muerto.pid", "python")},
    )
    assert not ok, "acredito como ruido a un PID muerto: el guard falla ABIERTO"


def test_un_cmdline_que_no_coincide_cae_al_bucket_estricto(tmp_path: Path) -> None:
    """Bloquea la suplantacion por reuso de PID.

    Un pidfile viejo cuyo numero fue reasignado a otro proceso no puede acreditar
    ruido: el sistema operativo recicla PIDs y el pidfile no caduca solo.
    """
    conftest = _root_conftest()
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        (tmp_path / "otro.pid").write_text(str(proc.pid), encoding="utf-8")
        ok, _ = conftest._daemon_owns_this_growth(
            "otro.jsonl",
            runtime_dir=tmp_path,
            pidfile_map={"otro.jsonl": ("otro.pid", "un_comando_que_no_corre_nadie")},
        )
        assert not ok, "acredito ruido a un proceso vivo cuyo cmdline no coincide"
    finally:
        proc.kill()
        proc.wait(timeout=10)


def test_un_pidfile_ausente_cae_al_bucket_estricto(tmp_path: Path) -> None:
    """Sin pidfile no hay forma de saber, y no-saber va al bucket estricto."""
    conftest = _root_conftest()
    ok, _ = conftest._daemon_owns_this_growth(
        "fantasma.jsonl",
        runtime_dir=tmp_path,
        pidfile_map={"fantasma.jsonl": ("no-existe.pid", "lo-que-sea")},
    )
    assert not ok, "sin pidfile acredito ruido igual: el guard falla ABIERTO"
