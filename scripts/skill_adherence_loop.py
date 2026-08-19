#!/usr/bin/env python3
# SCOPE: os-only
"""Cierra —o declara que no puede cerrar— el lazo de adherencia de skills.

RULES-COMPACT.md §11 dice que una sugerencia de skill de alta confianza es
"mandatory or require audited bypass". Este script mide ese mandato por sesión:

    sugerida de alta confianza -> invocada
                               -> bypasseada con razón escrita
                               -> SIN RASTRO            <- el hallazgo

POR QUE NO ALCANZA CON CONTAR INVOCACIONES
------------------------------------------
Un cero en ``skill-invocations.jsonl`` tiene dos causas indistinguibles a simple
vista: nadie invocó nada, o el logger no estaba grabando. Reportar el primero
cuando el caso es el segundo convierte ceguera en un número que se lee como
adherencia. Por eso cada sugerencia de alta confianza cae en CUATRO cubetas y no
en tres: ``CLOSED``, ``BYPASSED``, ``UNTRACED`` (acusación real) y
``UNMEASURABLE`` (el instrumento no estaba grabando en esa ventana, así que el
script se abstiene). La tasa de adherencia se publica SOLO sobre el denominador
medible, y la ceguera se publica al lado, sin mezclarse.

Una sugerencia sólo se clasifica ``UNTRACED`` cuando hay prueba positiva de que
el logger emitió al menos una fila DENTRO de esa misma ventana de sesión. Si el
logger estuvo mudo en la ventana —aunque haya grabado en otro momento— el
veredicto es ``UNMEASURABLE``. Es deliberadamente conservador: acusar de no
adherir requiere un testigo vivo en la escena.

FUENTES (todas de sólo lectura; cada número declara de dónde sale)
------------------------------------------------------------------
  suggestions : .cognitive-os/metrics/skill-suggestion.jsonl
                (hooks/skill-router-prompt-suggest.sh)
  invocations : .cognitive-os/metrics/skill-invocations.jsonl
                (hooks/skill-invocation-logger.sh, PostToolUse sobre Skill)
  bypasses    : .cognitive-os/metrics/skill-bypass.jsonl
                (hooks/orchestrator-skill-invocation-gate.sh; puede no existir)
  events      : .cognitive-os/sessions/events.jsonl — fuente corroborante que el
                gate consulta buscando event_type ``skill-invoked``. Se lee para
                REPORTAR si esa vía tiene datos, porque el gate depende de ella.

AGRUPAMIENTO POR SESION
-----------------------
``session_id`` está en el esquema pero el hook lo toma de la variable de entorno
``COGNITIVE_OS_SESSION_ID``, que en la práctica no está seteada. Cuando el
``session_id`` grabado es degenerado (``unknown``/vacío/``null``) el script
deriva la sesión por hueco temporal y marca la cubeta como ``derived``. Una
sesión derivada NO es una sesión grabada y la salida lo dice en cada fila.

Sólo lectura. Determinista para el mismo corpus. No depende del cwd ni del
estado de sesión: el repo se resuelve desde ``__file__``.

Exit codes:
  0  sin hallazgos
  1  hallazgos (>=1 UNTRACED, o ceguera con --fail-on-blind)
  2  error
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# El gate que efectivamente bloquea (hooks/orchestrator-skill-invocation-gate.sh)
# actúa en >= 0.90. El hook que loguea marca `threshold_met` en >= 0.80. Son dos
# umbrales distintos en dos archivos distintos; acá manda el del gate, porque es
# el que impone el mandato que §11 dice que hay que verificar.
DEFAULT_THRESHOLD = 0.90

DEGENERATE_SESSION_IDS = {"", "unknown", "null", "none", "-"}

# Veredictos de liveness del instrumento, por ventana de sesión.
LIVE = "LIVE"                    # el logger emitió filas DENTRO de la ventana
SILENT = "SILENT"                # grabó antes y después, pero no acá
DEAD_OUT_OF_SPAN = "DEAD_OUT_OF_SPAN"  # la ventana cae fuera del tramo que grabó
DEAD_NO_ROWS = "DEAD_NO_ROWS"    # el logger no grabó nunca, en ningún momento

BLIND_STATES = {SILENT, DEAD_OUT_OF_SPAN, DEAD_NO_ROWS}

CLOSED = "CLOSED"
BYPASSED = "BYPASSED"
UNTRACED = "UNTRACED"
UNMEASURABLE = "UNMEASURABLE"


class LoopError(RuntimeError):
    """Error irrecuperable de lectura o de parseo estructural."""


# --------------------------------------------------------------------------- #
# Lectura
# --------------------------------------------------------------------------- #
def parse_ts(raw: Any) -> datetime | None:
    """Acepta los tres formatos que conviven en la telemetría real.

    ``2026-08-19T18:53:24.689811+00:00`` (suggestion / invocations),
    ``2026-08-15T14:18:02Z`` (bypass) y variantes sin zona (se asumen UTC).
    Devuelve ``None`` en vez de romper: una fila con ts ilegible se cuenta como
    malformada, no tumba la corrida.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], int, bool]:
    """Devuelve (filas, malformadas, existe). Un archivo ausente no es un error.

    Que el ledger de bypass no exista es un dato del dominio —nadie bypasseó con
    razón escrita, o el gate nunca llegó a escribir— y no una falla del script.
    """
    if not path.exists():
        return [], 0, False
    rows: list[dict[str, Any]] = []
    malformed = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
                else:
                    malformed += 1
    except OSError as exc:  # pragma: no cover - depende del filesystem
        raise LoopError(f"no se pudo leer {path}: {exc}") from exc
    return rows, malformed, True


def normalize_session(raw: Any) -> str | None:
    """``None`` cuando el session_id grabado no identifica nada."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text.lower() in DEGENERATE_SESSION_IDS:
        return None
    return text


def load_suggestions(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        ts = parse_ts(row.get("ts") or row.get("timestamp"))
        skill = row.get("skill_name")
        if ts is None or not skill:
            # skill_name null = el router no encontró match; no es una sugerencia.
            continue
        confidence = row.get("confidence")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        out.append(
            {
                "ts": ts,
                "skill": str(skill),
                "confidence": confidence,
                "prompt_hash": row.get("prompt_hash") or "",
                "session_id": normalize_session(row.get("session_id")),
            }
        )
    out.sort(key=lambda r: r["ts"])
    return out


def load_invocations(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        ts = parse_ts(row.get("timestamp") or row.get("ts"))
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        skill = payload.get("skill_name") or payload.get("skill") or row.get("skill_name")
        if ts is None or not skill:
            continue
        out.append(
            {
                "ts": ts,
                "skill": str(skill),
                "session_id": normalize_session(payload.get("session_id") or row.get("session_id")),
            }
        )
    out.sort(key=lambda r: r["ts"])
    return out


def load_bypasses(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        ts = parse_ts(row.get("ts") or row.get("timestamp"))
        skill = row.get("suggested_skill") or row.get("skill")
        if ts is None or not skill:
            continue
        reason = (row.get("reason") or "").strip()
        out.append(
            {
                "ts": ts,
                "skill": str(skill),
                "prompt_hash": row.get("prompt_hash") or "",
                "reason": reason,
                # Un bypass sin razón escrita no cumple §11: es un bypass a secas.
                "audited": bool(reason),
                "session_id": normalize_session(row.get("session_id")),
            }
        )
    out.sort(key=lambda r: r["ts"])
    return out


def count_events_skill_invoked(path: Path) -> tuple[int, bool]:
    """Cuenta event_type ``skill-invoked``/``skill_invoked`` en events.jsonl.

    Es la vía que consulta el gate para decidir si una skill se invocó. Se cuenta
    por separado y se reporta: si acá hay cero, el fallback del gate es inerte y
    eso hay que decirlo, no descubrirlo.
    """
    if not path.exists():
        return 0, False
    hits = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                event_type = str(obj.get("event_type") or "").lower()
                if event_type in ("skill-invoked", "skill_invoked", "skill.invoked"):
                    hits += 1
    except OSError as exc:  # pragma: no cover
        raise LoopError(f"no se pudo leer {path}: {exc}") from exc
    return hits, True


# --------------------------------------------------------------------------- #
# Sesionizacion
# --------------------------------------------------------------------------- #
def build_sessions(
    suggestions: list[dict[str, Any]], gap: timedelta
) -> list[dict[str, Any]]:
    """Agrupa por session_id grabado; deriva por hueco temporal cuando no lo hay.

    Las cubetas derivadas quedan marcadas ``source="derived"`` para que nadie las
    lea como sesiones reales.
    """
    sessions: list[dict[str, Any]] = []

    recorded: dict[str, list[dict[str, Any]]] = {}
    degenerate: list[dict[str, Any]] = []
    for sug in suggestions:
        if sug["session_id"]:
            recorded.setdefault(sug["session_id"], []).append(sug)
        else:
            degenerate.append(sug)

    for sid in sorted(recorded):
        items = sorted(recorded[sid], key=lambda r: r["ts"])
        sessions.append({"id": f"rec:{sid}", "source": "recorded", "suggestions": items})

    bucket: list[dict[str, Any]] = []
    for sug in degenerate:  # ya viene ordenado por ts
        if bucket and (sug["ts"] - bucket[-1]["ts"]) > gap:
            sessions.append({"source": "derived", "suggestions": bucket})
            bucket = []
        bucket.append(sug)
    if bucket:
        sessions.append({"source": "derived", "suggestions": bucket})

    derived_n = 0
    for session in sessions:
        if session["source"] == "derived":
            derived_n += 1
            session["id"] = f"derived:{derived_n:03d}"
        items = session["suggestions"]
        session["start"] = items[0]["ts"]
        session["end"] = items[-1]["ts"]
    sessions.sort(key=lambda s: s["start"])
    return sessions


def logger_liveness(
    session: dict[str, Any],
    invocations: list[dict[str, Any]],
    pair_window: timedelta,
) -> tuple[str, int]:
    """Veredicto sobre el instrumento para ESTA ventana, no para el corpus."""
    if not invocations:
        return DEAD_NO_ROWS, 0

    lo = session["start"] - pair_window
    hi = session["end"] + pair_window
    in_window = [inv for inv in invocations if lo <= inv["ts"] <= hi]
    if in_window:
        return LIVE, len(in_window)

    corpus_first = invocations[0]["ts"]
    corpus_last = invocations[-1]["ts"]
    if hi < corpus_first or lo > corpus_last:
        return DEAD_OUT_OF_SPAN, 0
    return SILENT, 0


# --------------------------------------------------------------------------- #
# Clasificacion
# --------------------------------------------------------------------------- #
def classify(
    suggestions: list[dict[str, Any]],
    invocations: list[dict[str, Any]],
    bypasses: list[dict[str, Any]],
    threshold: float,
    pair_window: timedelta,
    session_gap: timedelta,
) -> dict[str, Any]:
    sessions = build_sessions(suggestions, session_gap)

    session_reports: list[dict[str, Any]] = []
    totals = {CLOSED: 0, BYPASSED: 0, UNTRACED: 0, UNMEASURABLE: 0}
    findings: list[dict[str, Any]] = []

    for session in sessions:
        liveness, live_rows = logger_liveness(session, invocations, pair_window)
        high = [s for s in session["suggestions"] if s["confidence"] >= threshold]
        low_n = len(session["suggestions"]) - len(high)

        verdicts: list[dict[str, Any]] = []
        for sug in high:
            lo, hi = sug["ts"], sug["ts"] + pair_window
            paired = next(
                (
                    inv
                    for inv in invocations
                    if inv["skill"] == sug["skill"] and lo <= inv["ts"] <= hi
                ),
                None,
            )
            bypass = next(
                (
                    byp
                    for byp in bypasses
                    if byp["skill"] == sug["skill"]
                    and byp["audited"]
                    and (
                        (byp["prompt_hash"] and byp["prompt_hash"] == sug["prompt_hash"])
                        or lo <= byp["ts"] <= hi
                    )
                ),
                None,
            )

            if paired is not None:
                verdict, evidence = CLOSED, "skill-invocations.jsonl"
            elif bypass is not None:
                verdict, evidence = BYPASSED, "skill-bypass.jsonl"
            elif liveness == LIVE:
                verdict, evidence = UNTRACED, "logger LIVE en la ventana y sin fila"
            else:
                verdict, evidence = UNMEASURABLE, f"logger {liveness} en la ventana"

            totals[verdict] += 1
            record = {
                "session": session["id"],
                "session_source": session["source"],
                "ts": sug["ts"].isoformat(),
                "skill": sug["skill"],
                "confidence": round(sug["confidence"], 4),
                "prompt_hash": sug["prompt_hash"],
                "verdict": verdict,
                "evidence": evidence,
            }
            verdicts.append(record)
            if verdict == UNTRACED:
                findings.append(record)

        session_reports.append(
            {
                "id": session["id"],
                "source": session["source"],
                "start": session["start"].isoformat(),
                "end": session["end"].isoformat(),
                "logger_state": liveness,
                "logger_rows_in_window": live_rows,
                "suggestions_total": len(session["suggestions"]),
                "suggestions_high_conf": len(high),
                "suggestions_below_threshold": low_n,
                "verdicts": {
                    key: sum(1 for v in verdicts if v["verdict"] == key)
                    for key in (CLOSED, BYPASSED, UNTRACED, UNMEASURABLE)
                },
                "detail": verdicts,
            }
        )

    high_total = sum(totals.values())
    measurable = totals[CLOSED] + totals[BYPASSED] + totals[UNTRACED]
    adherence = (
        round((totals[CLOSED] + totals[BYPASSED]) / measurable, 4) if measurable else None
    )
    blind_ratio = round(totals[UNMEASURABLE] / high_total, 4) if high_total else None

    return {
        "sessions": session_reports,
        "totals": dict(totals),
        "high_confidence_total": high_total,
        "measurable_denominator": measurable,
        "adherence_over_measurable": adherence,
        "blind_ratio": blind_ratio,
        "findings": findings,
    }


# --------------------------------------------------------------------------- #
# Salida
# --------------------------------------------------------------------------- #
def render(report: dict[str, Any]) -> str:
    src = report["sources"]
    res = report["result"]
    out: list[str] = []
    add = out.append

    add("LAZO DE ADHERENCIA DE SKILLS")
    add("=" * 68)
    add(f"umbral de alta confianza : {report['threshold']:.2f}")
    add(f"ventana de apareo        : {report['pair_window_min']} min")
    add(f"hueco de sesion derivada : {report['session_gap_min']} min")
    add("")
    add("FUENTES (cada numero declara de donde sale)")
    for name, info in src.items():
        state = "presente" if info["exists"] else "AUSENTE"
        add(
            f"  {name:<14} {state:<9} filas={info['rows']:<6} "
            f"usables={info.get('usable', info['rows']):<6} "
            f"malformadas={info['malformed']:<4} {info['path']}"
        )
    add("")

    add("SALUD DEL INSTRUMENTO")
    inst = report["instrument"]
    add(f"  logger de invocaciones : {inst['logger_verdict']}")
    if inst["logger_first"]:
        add(f"  tramo grabado          : {inst['logger_first']} .. {inst['logger_last']}")
    add(
        f"  events.jsonl skill-invoked : {inst['events_skill_invoked']} "
        f"(la via que consulta el gate; 0 = fallback inerte)"
    )
    add("")

    add("SESIONES")
    add(
        f"  {'sesion':<14} {'origen':<9} {'logger':<18} {'alta':>5} "
        f"{'clos':>5} {'byp':>5} {'untr':>5} {'nomed':>6}"
    )
    for session in res["sessions"]:
        v = session["verdicts"]
        add(
            f"  {session['id']:<14} {session['source']:<9} {session['logger_state']:<18} "
            f"{session['suggestions_high_conf']:>5} {v[CLOSED]:>5} {v[BYPASSED]:>5} "
            f"{v[UNTRACED]:>5} {v[UNMEASURABLE]:>6}"
        )
    if not res["sessions"]:
        add("  (ninguna sugerencia en el corpus)")
    add("")

    t = res["totals"]
    add("TOTALES")
    add(f"  sugerencias de alta confianza : {res['high_confidence_total']}")
    add(f"  CLOSED       (invocada)       : {t[CLOSED]}")
    add(f"  BYPASSED     (razon escrita)  : {t[BYPASSED]}")
    add(f"  UNTRACED     (SIN RASTRO)     : {t[UNTRACED]}   <- hallazgo")
    add(f"  UNMEASURABLE (instrumento mudo): {t[UNMEASURABLE]}")
    add("")

    if res["measurable_denominator"]:
        add(
            f"  adherencia sobre lo medible : "
            f"{res['adherence_over_measurable']:.2%} "
            f"({t[CLOSED] + t[BYPASSED]}/{res['measurable_denominator']})"
        )
    else:
        add("  adherencia sobre lo medible : NO CALCULABLE (denominador medible = 0)")
    if res["blind_ratio"] is not None:
        add(f"  ceguera                     : {res['blind_ratio']:.2%} del total")
    add("")

    if t[UNMEASURABLE]:
        add(
            "  AVISO: hay sugerencias que este script NO puede juzgar. No se cuentan\n"
            "  como no-adherencia ni como adherencia. Un cero en UNTRACED con ceguera\n"
            "  alta NO es un lazo cerrado: es un lazo no observado."
        )
        add("")

    if res["findings"]:
        add(f"HALLAZGOS ({len(res['findings'])})")
        for f in res["findings"][:40]:
            add(
                f"  [{f['session']}] {f['ts']} {f['skill']} conf={f['confidence']} "
                f"prompt={f['prompt_hash']}"
            )
        if len(res["findings"]) > 40:
            add(f"  ... y {len(res['findings']) - 40} mas (ver --json)")
    else:
        add("HALLAZGOS: ninguno")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Entrada
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill_adherence_loop.py",
        description=(
            "Mide por sesion el lazo sugerida-de-alta-confianza -> invocada / "
            "bypasseada con razon / sin rastro, distinguiendo 'no invocada' de "
            "'no medible porque el logger no estaba grabando'."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=None,
        help="directorio de telemetria (default: <repo>/.cognitive-os/metrics)",
    )
    parser.add_argument(
        "--events-file",
        type=Path,
        default=None,
        help="events.jsonl a corroborar (default: <repo>/.cognitive-os/sessions/events.jsonl)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=(
            f"confianza minima para considerar la sugerencia mandatoria "
            f"(default: {DEFAULT_THRESHOLD}, el umbral del gate que bloquea)"
        ),
    )
    parser.add_argument(
        "--pair-window-min",
        type=int,
        default=30,
        help="minutos para aparear sugerencia con invocacion o bypass (default: 30)",
    )
    parser.add_argument(
        "--session-gap-min",
        type=int,
        default=30,
        help="hueco que separa dos sesiones derivadas (default: 30)",
    )
    parser.add_argument(
        "--fail-on-blind",
        action="store_true",
        help="salir 1 tambien cuando haya sugerencias UNMEASURABLE",
    )
    parser.add_argument("--json", action="store_true", help="emitir JSON en vez de texto")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not 0.0 <= args.threshold <= 1.0:
        print("error: --threshold debe estar entre 0.0 y 1.0", file=sys.stderr)
        return 2
    if args.pair_window_min < 0 or args.session_gap_min < 0:
        print("error: las ventanas en minutos no pueden ser negativas", file=sys.stderr)
        return 2

    metrics_dir = args.metrics_dir or (PROJECT_ROOT / ".cognitive-os" / "metrics")
    events_file = args.events_file or (
        PROJECT_ROOT / ".cognitive-os" / "sessions" / "events.jsonl"
    )

    sug_path = metrics_dir / "skill-suggestion.jsonl"
    inv_path = metrics_dir / "skill-invocations.jsonl"
    byp_path = metrics_dir / "skill-bypass.jsonl"

    try:
        sug_rows, sug_bad, sug_exists = read_jsonl(sug_path)
        inv_rows, inv_bad, inv_exists = read_jsonl(inv_path)
        byp_rows, byp_bad, byp_exists = read_jsonl(byp_path)
        events_hits, events_exists = count_events_skill_invoked(events_file)
    except LoopError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not sug_exists:
        print(
            f"error: no existe la fuente de sugerencias {sug_path}. Sin ella no hay "
            "lazo que medir; esto no es 'cero hallazgos'.",
            file=sys.stderr,
        )
        return 2

    suggestions = load_suggestions(sug_rows)
    invocations = load_invocations(inv_rows)
    bypasses = load_bypasses(byp_rows)

    pair_window = timedelta(minutes=args.pair_window_min)
    session_gap = timedelta(minutes=args.session_gap_min)

    result = classify(
        suggestions, invocations, bypasses, args.threshold, pair_window, session_gap
    )

    if not invocations:
        logger_verdict = (
            "MUDO — cero filas usables. Un cero en las cubetas de invocacion NO "
            "prueba que no hubo invocaciones."
        )
    else:
        logger_verdict = f"vivo en algun tramo ({len(invocations)} filas usables)"

    report = {
        "schema": "skill-adherence-loop/1",
        "threshold": args.threshold,
        "pair_window_min": args.pair_window_min,
        "session_gap_min": args.session_gap_min,
        "sources": {
            "suggestions": {
                "path": str(sug_path),
                "exists": sug_exists,
                "rows": len(sug_rows),
                "usable": len(suggestions),
                "malformed": sug_bad,
            },
            "invocations": {
                "path": str(inv_path),
                "exists": inv_exists,
                "rows": len(inv_rows),
                "usable": len(invocations),
                "malformed": inv_bad,
            },
            "bypasses": {
                "path": str(byp_path),
                "exists": byp_exists,
                "rows": len(byp_rows),
                "usable": len(bypasses),
                "malformed": byp_bad,
            },
            "events": {
                "path": str(events_file),
                "exists": events_exists,
                "rows": events_hits,
                "usable": events_hits,
                "malformed": 0,
            },
        },
        "instrument": {
            "logger_verdict": logger_verdict,
            "logger_first": invocations[0]["ts"].isoformat() if invocations else None,
            "logger_last": invocations[-1]["ts"].isoformat() if invocations else None,
            "events_skill_invoked": events_hits,
        },
        "result": result,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print(render(report))

    if result["totals"][UNTRACED] > 0:
        return 1
    if args.fail_on_blind and result["totals"][UNMEASURABLE] > 0:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(2)
