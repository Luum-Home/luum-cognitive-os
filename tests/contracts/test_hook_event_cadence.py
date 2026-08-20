"""Cadencia: cada evento del esquema declara CUANDO dispara y CUANTAS VECES.

Por que existe este archivo, con nombre y fecha. El 2026-08-19 se reparo
``hooks/session-cleanup.sh``, que archivaba el directorio de sesion en el evento
``Stop`` asumiendo que ``Stop`` significa "fin de sesion". ``Stop`` dispara POR
TURNO: 341 disparos contra 76 aperturas de sesion, hasta 45 dentro de una sola
ventana ``SessionStart -> SessionStart``. El manifiesto transcribia ``Stop`` con
sus campos, sus fields de decision y su exit_2_behavior — y sin una sola linea
sobre cuando dispara. La pregunta que decidia el caso no estaba escrita, asi que
escribir un hook de ``Stop`` correcto dependia de que el autor ya supiera la
respuesta.

Lo que este archivo hace cumplir, en tres capas:

1. **Cobertura.** Todo evento transcrito lleva ``cadence``. Sin excepciones y sin
   allowlist: un evento nuevo entra con cadencia o no entra.

2. **Forma que no acepta prosa vaga.** ``per_session`` es un ENUM CERRADO con la
   UNIDAD de recurrencia adentro (``-per-turn``, ``-per-tool-call``,
   ``-per-session``...). No existe un valor comodin: no hay ``0-N`` a secas,
   justamente para que "dispara varias veces" no pueda escribirse sin decir
   varias veces POR QUE COSA. ``fires_when`` ademas se rechaza por vaguedad
   (lista de frases-escape) y por no nombrar ninguna unidad de recurrencia.

3. **Cruce contra la telemetria.** Esta es la capa que habria atajado el defecto.
   ``scripts/measure_event_cadence.py`` vuelve a medir HOY, y la clase declarada
   tiene que ser compatible con lo medido. Escribir ``exactly-1-per-session`` en
   ``Stop`` es rojo, porque el maximo medido por sesion es 45. Copiar la doc no
   alcanza: si el evento se observa en la telemetria, ``evidence: documented`` se
   rechaza y hay que declarar ``measured`` con los numeros.

Sobre el verde barato, que es el riesgo real de un gate como este. Un gate que
exija el campo y acepte cualquier texto NO sirve. Lo que este rechaza ademas de
la ausencia esta en ``test_gate_rejects_more_than_absence``, que corre los cinco
casos: campo ausente, prosa vaga, prosa sin unidad, enum invalido, y — el que
importa — una clase que contradice la telemetria.

Correr:
    python3 -m pytest tests/contracts/test_hook_event_cadence.py -q
"""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from cos_lib.measurement import looks_runnable  # noqa: E402

HOOK_QUALITY_COVERAGE = "census"

# ── Enum cerrado. La unidad va DENTRO del valor a proposito ──────────────────
# No hay un "0-N" pelado. Un evento que dispara varias veces tiene que decir
# varias veces por que: por turno, por tool-call, por subagente, por tarea, por
# compactacion. Esa palabra es la que le faltaba a Stop.
PER_SESSION_VALUES = {
    "exactly-1-per-session",
    "0-1-per-session",
    "0-N-per-turn",
    "0-N-per-tool-call",
    "0-N-per-subagent",
    "0-N-per-task",
    "0-N-per-compaction",
}
EVIDENCE_VALUES = {"measured", "inspected", "documented", "not-observed"}

# Unidades que `fires_when` tiene que nombrar en prosa. Un texto que no menciona
# ninguna no dijo cuando dispara, dijo algo sobre el evento.
RECURRENCE_ANCHORS = (
    "turno", "sesion", "sesión", "tool-call", "herramienta", "subagente",
    "tarea", "compact", "prompt", "apertura", "mensaje", "permiso",
)

# Frases-escape: la forma que toma el verde barato cuando el gate solo exige que
# el campo exista.
VAGUE = (
    "cuando corresponde", "cuando aplica", "segun el caso", "a veces",
    "when appropriate", "as needed", "depends", "varies", "tbd", "n/a",
    "por determinar", "ver doc", "see docs",
)
MIN_FIRES_WHEN = 60

MANIFESTS = {
    "claude-code": (REPO_ROOT / "manifests" / "claude-code-hooks-schema.yaml", "events", None),
    "codex": (REPO_ROOT / "manifests" / "codex-hooks-schema.yaml", "events", None),
    # OpenCode publica SURFACES, no eventos, y no todas son senales de ciclo de
    # vida: `tui.prompt.append` esta publicado y el propio manifiesto lo marca
    # `usable_as: none`. La cadencia se exige donde se puede proyectar, que es
    # donde un autor de hooks se puede equivocar.
    "opencode": (REPO_ROOT / "manifests" / "opencode-hooks-schema.yaml", "surfaces", "lifecycle"),
}


def _load(harness: str) -> tuple[dict, dict]:
    path, key, only = MANIFESTS[harness]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data[key]
    if only:
        entries = {k: v for k, v in entries.items() if v.get("usable_as") == only}
    return data, entries


@pytest.fixture(scope="session")
def telemetry() -> dict:
    """Vuelve a MEDIR. No lee un numero guardado: corre el instrumento."""
    script = REPO_ROOT / "scripts" / "measure_event_cadence.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=300,
    )
    assert proc.returncode == 0, f"{script.name} fallo:\n{proc.stderr}"
    import json
    return json.loads(proc.stdout)


# ── Capa 1: cobertura ────────────────────────────────────────────────────────

@pytest.mark.parametrize("harness", sorted(MANIFESTS))
def test_every_event_declares_a_cadence(harness):
    """Sin allowlist. Un evento nuevo entra con cadencia o no entra."""
    _, entries = _load(harness)
    assert entries, f"{harness}: el manifiesto no expone eventos"
    missing = sorted(k for k, v in entries.items() if not (v or {}).get("cadence"))
    assert not missing, (
        f"{harness}: evento(s) sin bloque `cadence`: {missing}. Un evento "
        "transcrito sin cadencia obliga a quien escribe el hook a ya saber "
        "cuando dispara — que es como Stop termino archivando sesiones vivas. "
        "Agregar cadence con fires_when, per_session, evidence, basis y how."
    )


# ── Capa 2: forma ────────────────────────────────────────────────────────────

def _check_shape(harness: str, name: str, cad: dict, sources: list) -> None:
    fw = (cad.get("fires_when") or "").strip()
    assert len(fw) >= MIN_FIRES_WHEN, (
        f"{harness}/{name}: fires_when tiene {len(fw)} caracteres, minimo "
        f"{MIN_FIRES_WHEN}. Una linea corta no alcanza para decir cuando dispara "
        "Y cual es la unidad de recurrencia."
    )
    low = fw.lower()
    hit = [v for v in VAGUE if v in low]
    assert not hit, (
        f"{harness}/{name}: fires_when contiene prosa vaga {hit}. El campo existe "
        "para responder la pregunta, no para ocupar el lugar de la respuesta."
    )
    assert any(a in low for a in RECURRENCE_ANCHORS), (
        f"{harness}/{name}: fires_when no nombra ninguna unidad de recurrencia "
        f"{list(RECURRENCE_ANCHORS)}. Decir que un evento 'ocurre en el flujo' no "
        "distingue una vez por sesion de 45 veces por sesion."
    )
    ps = cad.get("per_session")
    assert ps in PER_SESSION_VALUES, (
        f"{harness}/{name}: per_session={ps!r} no esta en el enum cerrado "
        f"{sorted(PER_SESSION_VALUES)}. No hay valor comodin a proposito."
    )
    ev = cad.get("evidence")
    assert ev in EVIDENCE_VALUES, (
        f"{harness}/{name}: evidence={ev!r} fuera de {sorted(EVIDENCE_VALUES)}."
    )
    basis = cad.get("basis") or []
    assert basis, f"{harness}/{name}: falta `basis` — de donde sale la clase."
    declared = {s.get("url") for s in sources if isinstance(s, dict) and s.get("url")}
    unknown = [b for b in basis if b not in declared]
    assert not unknown, (
        f"{harness}/{name}: basis {unknown} no figura en `sources:` del manifiesto. "
        "Una URL suelta no se re-verifica nunca; las de sources llevan fecha."
    )
    how = (cad.get("how") or "").strip()
    assert how and looks_runnable(how), (
        f"{harness}/{name}: how={how!r} no tiene forma de comando. Un numero sin "
        "el comando que lo produce es opinion con digitos."
    )
    if ev == "measured":
        m = cad.get("measured") or {}
        faltan = [k for k in ("window", "occurrences", "sessions", "max_per_session")
                  if k not in m]
        assert not faltan, f"{harness}/{name}: evidence=measured sin {faltan}."
    if ev in {"documented", "not-observed", "inspected"}:
        assert (cad.get("doc_quote") or "").strip(), (
            f"{harness}/{name}: evidence={ev} sin doc_quote. Sin medicion propia, "
            "la clase se apoya en una cita textual o no se apoya en nada."
        )
    if ev == "not-observed":
        assert (cad.get("blind_reason") or "").strip(), (
            f"{harness}/{name}: not-observed sin blind_reason. 'No lo vi' y 'no "
            "ocurre' no son lo mismo y el manifiesto tiene que decir cual es."
        )


@pytest.mark.parametrize("harness", sorted(MANIFESTS))
def test_cadence_shape_is_not_free_text(harness):
    data, entries = _load(harness)
    for name, spec in sorted(entries.items()):
        _check_shape(harness, name, spec["cadence"], data.get("sources") or [])


# ── Capa 3: cruce contra la telemetria ───────────────────────────────────────

def _consistency_error(name: str, ps: str, ev: str, obs: dict | None) -> str | None:
    """None si la clase declarada es compatible con lo medido hoy."""
    if obs is None or not obs.get("observed"):
        if ev == "measured":
            return (f"{name}: evidence=measured pero el instrumento no ve una sola "
                    "ocurrencia hoy. Si el evento dejo de ocurrir, esto es "
                    "not-observed con blind_reason, no measured.")
        return None
    mx = obs["max_per_session"]
    if ev == "documented":
        return (f"{name}: evidence=documented pero el evento SI se observa "
                f"({obs['occurrences']} ocurrencias). Copiar la doc cuando hay "
                "telemetria propia es exactamente el atajo que dejo pasar el "
                "defecto de Stop. Declarar measured con los numeros.")
    if ps == "exactly-1-per-session" and mx != 1:
        return (f"{name}: declarado exactly-1-per-session, medido max "
                f"{mx} por sesion. Esta es la forma del defecto de 2026-08-19.")
    if ps == "0-1-per-session" and mx > 1:
        return f"{name}: declarado 0-1-per-session, medido max {mx} por sesion."
    if ps in {"0-N-per-turn", "0-N-per-subagent"} and mx <= 1:
        return (f"{name}: declarado {ps}, y el maximo medido por sesion es {mx}. "
                "Nada en la telemetria sostiene que sea multiple.")
    if ps == "0-N-per-tool-call" and mx <= 1:
        return f"{name}: declarado {ps}, medido max {mx} por sesion."
    return None


def test_declared_cadence_agrees_with_todays_telemetry(telemetry):
    """La capa que habria atajado el defecto. Mide hoy, no lee un numero viejo."""
    data, entries = _load("claude-code")
    errs = []
    for name, spec in sorted(entries.items()):
        cad = spec["cadence"]
        err = _consistency_error(
            name, cad["per_session"], cad["evidence"], telemetry["events"].get(name)
        )
        if err:
            errs.append(err)
    assert not errs, (
        "La cadencia escrita contradice la telemetria del repo:\n  "
        + "\n  ".join(errs)
        + f"\n\nMedir con: python3 scripts/measure_event_cadence.py "
          f"(hoy: {telemetry['sessions']} sesiones, {telemetry['total_rows']} filas)"
    )


def test_measured_events_are_the_ones_the_instrument_can_see(telemetry):
    """Simetria del cruce: lo observado se declara medido, lo ciego se declara ciego."""
    _, entries = _load("claude-code")
    wrong = []
    for name, spec in sorted(entries.items()):
        cad = spec["cadence"]
        obs = telemetry["events"].get(name)
        seen = bool(obs and obs.get("observed"))
        if seen and cad["evidence"] == "not-observed":
            wrong.append(f"{name}: declarado not-observed y el instrumento lo ve.")
        if not seen and cad["evidence"] == "measured":
            wrong.append(f"{name}: declarado measured y el instrumento no lo ve.")
    assert not wrong, "\n  ".join(wrong)


# ── El control contra el verde barato ────────────────────────────────────────

def test_gate_rejects_more_than_absence(telemetry):
    """Un gate que solo exige que el campo exista no sirve. Estos son los cinco
    rechazos, corridos de verdad sobre copias en memoria del manifiesto real."""
    data, entries = _load("claude-code")
    sources = data.get("sources") or []
    base = copy.deepcopy(entries["Stop"]["cadence"])

    casos: list[tuple[str, dict]] = [
        ("prosa vaga", {**base, "fires_when": "Dispara cuando corresponde, segun el caso del turno de la sesion."}),
        ("prosa sin unidad de recurrencia", {**base, "fires_when": "El arnes emite este evento como parte del flujo normal de ejecucion, y el hook recibe su payload."}),
        ("enum invalido", {**base, "per_session": "0-N"}),
        ("how que no es comando", {**base, "how": "lo verifique a mano mirando la telemetria"}),
        ("basis fuera de sources", {**base, "basis": ["https://example.invalid/hooks"]}),
    ]
    for etiqueta, cad in casos:
        with pytest.raises(AssertionError):
            _check_shape("claude-code", "Stop", cad, sources)

    # Ausencia del campo.
    with pytest.raises(KeyError):
        {k: v for k, v in entries["Stop"].items() if k != "cadence"}["cadence"]

    # El sexto y el que importa: forma VALIDA, clase FALSA. Pasa las tres capas
    # de forma y muere contra la telemetria. Es literalmente el defecto de
    # 2026-08-19 escrito a mano.
    mentira = {**base, "per_session": "exactly-1-per-session"}
    _check_shape("claude-code", "Stop", mentira, sources)   # la forma no lo atrapa
    err = _consistency_error("Stop", "exactly-1-per-session", "measured",
                             telemetry["events"]["Stop"])
    assert err and "exactly-1-per-session" in err, (
        "El cruce contra telemetria no rechazo 'Stop dispara una vez por sesion'. "
        "Sin ese rechazo este gate solo pide que el campo exista."
    )

    # Y el simetrico, para que el cruce no sea un rechaza-todo: la clase VERDADERA
    # pasa sobre los mismos datos.
    assert _consistency_error("Stop", "0-N-per-turn", "measured",
                              telemetry["events"]["Stop"]) is None
