#!/usr/bin/env python3
# SCOPE: os-only
"""Cadencia medida de cada evento del arnés: cuántas veces dispara, por sesión.

Por qué existe. El 2026-08-19 se reparó `hooks/session-cleanup.sh`, que archivaba
el directorio de sesión en el evento `Stop` asumiendo que `Stop` significa "fin de
sesión". `Stop` dispara POR TURNO. El manifiesto transcribía el evento sin decir
cuándo dispara, así que el dato que decidía el caso no estaba escrito en ninguna
parte y el autor tenía que ya saber la respuesta — que es exactamente lo que no
pasó. Este script es el instrumento que produce ese dato, y
`tests/contracts/test_hook_event_cadence.py` lo cruza contra lo que el manifiesto
declara: una cadencia escrita a mano que contradiga la telemetría queda en rojo.

Metodología, y por qué no es contar filas.

  `hook-timing.jsonl` tiene UNA FILA POR HOOK, no por evento. Sumar filas de
  `Stop` da 7.810 y no significa nada: son 24 hooks registrados multiplicados por
  las veces que el evento ocurrió. La ocurrencia del EVENTO se cuenta eligiendo un
  hook TESTIGO —el que más filas tiene sobre ese evento— y contando SUS filas. Un
  hook registrado sin matcher corre en cada ocurrencia, así que sus filas son las
  ocurrencias. Los hooks con menos filas que el testigo se declaran como ceguera
  parcial (matcher, skip del dispatcher, o registración posterior), no se promedian.

  Las sesiones se cuentan igual, con el testigo de `SessionStart`. No se usa
  `session_id`: está vacío en la mayoría de las filas (se verifica y se reporta).

  El archivo ROTA. Contar sólo el archivo vivo produce falsos "nunca disparó" —
  falla #1 de `cos_lib/measurement.py`. Este script lee el vivo MÁS
  `.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz`, y nombra las dos
  fuentes en cada censo.

  Un evento con cero filas NO es "no dispara". Puede estar registrado y envuelto
  por el wrapper y simplemente no haber ocurrido en esta ventana (TaskCreated,
  TeammateIdle), o no estar proyectado (TaskCompleted). Los tres casos salen como
  ceguera declarada, nunca como conteo.

Uso:
    python3 scripts/measure_event_cadence.py                 # tabla legible
    python3 scripts/measure_event_cadence.py --json          # censos completos
    python3 scripts/measure_event_cadence.py --event Stop    # un solo evento

Códigos de salida: 0 siempre que la medición corra (es un instrumento, no un
gate). El gate vive en tests/contracts/test_hook_event_cadence.py.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from cos_lib.measurement import Census  # noqa: E402

METRICS = REPO_ROOT / ".cognitive-os" / "metrics"
LIVE = METRICS / "hook-timing.jsonl"
ARCHIVE_GLOB = "hook-timing-*.jsonl.gz"

HOW = "python3 scripts/measure_event_cadence.py --json"

# El evento que delimita la ventana de sesión. No es configurable a propósito:
# es el único evento del que el arnés promete exactamente una ocurrencia por
# apertura de sesión.
SESSION_EVENT = "SessionStart"


def _read_rows() -> tuple[list[dict], dict[str, int]]:
    """Filas de las DOS fuentes, más el recuento de lo que no se pudo leer."""
    rows: list[dict] = []
    blind: Counter = Counter()
    files: list[tuple[Path, bool]] = []
    if LIVE.exists():
        files.append((LIVE, False))
    files.extend(sorted((p, True) for p in (METRICS / ".archive").glob(ARCHIVE_GLOB)))
    for path, gz in files:
        opener = gzip.open if gz else open
        try:
            with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        blind["fila-no-parseable"] += 1
        except OSError as exc:  # archivo rotado a mitad de lectura, disco, etc.
            blind[f"archivo-ilegible:{path.name}"] += 1
            print(f"[aviso] {path}: {exc}", file=sys.stderr)
    rows.sort(key=lambda r: (r.get("timestamp") or "", r.get("hook") or ""))
    return rows, dict(blind)


def _witness(rows: list[dict], event: str) -> tuple[str | None, int]:
    """Hook testigo del evento y su cantidad de filas."""
    c: Counter = Counter()
    for r in rows:
        if r.get("event") == event:
            c[r.get("hook") or "?"] += 1
    if not c:
        return None, 0
    hook, n = c.most_common(1)[0]
    return hook, n


def measure(rows: list[dict], read_blind: dict[str, int], events: list[str]) -> dict:
    session_witness, sessions = _witness(rows, SESSION_EVENT)

    # Ventanas: cada fila del testigo de SessionStart abre una. Lo anterior a la
    # primera no pertenece a ninguna sesión observable y se declara ciego.
    windows: list[Counter] = []
    orphan: Counter = Counter()
    cur: Counter | None = None
    for r in rows:
        ev, hook = r.get("event"), r.get("hook")
        if ev == SESSION_EVENT and hook == session_witness:
            cur = Counter()
            windows.append(cur)
            # La fila que ABRE la ventana cuenta DENTRO de ella: si no, el propio
            # SessionStart mediría 0 por sesión, que es el error opuesto al que
            # este script existe para evitar.
        (cur if cur is not None else orphan)[(ev, hook)] += 1

    empty_session_id = sum(1 for r in rows if not (r.get("session_id") or "").strip())

    out: dict = {
        "total_rows": len(rows),
        "sources": [str(LIVE.relative_to(REPO_ROOT)),
                    str((METRICS / ".archive" / ARCHIVE_GLOB).relative_to(REPO_ROOT))],
        "sessions": sessions,
        "session_witness": session_witness,
        "rows_with_empty_session_id": empty_session_id,
        "events": {},
    }

    for event in events:
        hook, n = _witness(rows, event)
        per_window = sorted(w[(event, hook)] for w in windows) if hook else []
        blind: dict[str, int] = dict(read_blind)
        if hook is None:
            # Cero filas. No es un conteo: es una no-observación.
            blind["evento-sin-una-sola-fila-en-esta-ventana"] = 1
            census = Census(
                subject=f"cadencia de {event}",
                sources=tuple(out["sources"]),
                buckets={"ocurrencias-observadas": 0},
                blind=blind,
                how=HOW,
                window=f"{sessions} sesiones observadas",
                notes=(
                    "Cero filas. Puede estar registrado y envuelto y no haber "
                    "ocurrido, o no estar proyectado. Ninguna de las dos cosas "
                    "es 'el evento no dispara'.",
                ),
            )
            out["events"][event] = {
                "witness_hook": None,
                "occurrences": 0,
                "max_per_session": None,
                "median_per_session": None,
                "sessions_without_it": None,
                "census": census.to_dict(),
                "observed": False,
            }
            continue

        # Hooks del mismo evento que vieron MENOS ocurrencias que el testigo: el
        # faltante es ceguera parcial (matcher, skip, registración tardía).
        others: Counter = Counter()
        for r in rows:
            if r.get("event") == event:
                others[r.get("hook") or "?"] += 1
        partial = sum(max(0, n - v) for k, v in others.items() if k != hook)
        if partial:
            blind["ocurrencias-que-otros-hooks-del-evento-no-vieron"] = partial
        orphan_n = sum(v for (e, h), v in orphan.items() if e == event and h == hook)
        if orphan_n:
            blind["filas-antes-del-primer-SessionStart"] = orphan_n
        blind.setdefault("ninguna-otra", 0)

        census = Census(
            subject=f"cadencia de {event}",
            sources=tuple(out["sources"]),
            buckets={"ocurrencias-observadas": n},
            blind=blind,
            how=HOW,
            window=f"{sessions} sesiones observadas",
            notes=(f"hook testigo: {hook}",),
        )
        out["events"][event] = {
            "witness_hook": hook,
            "occurrences": n,
            "max_per_session": (per_window[-1] if per_window else 0),
            "median_per_session": (per_window[len(per_window) // 2] if per_window else 0),
            "sessions_without_it": sum(1 for v in per_window if v == 0),
            "census": census.to_dict(),
            "observed": True,
        }
    return out


def default_events(rows: list[dict]) -> list[str]:
    seen = {r.get("event") for r in rows if r.get("event")}
    return sorted(seen)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="censos completos en JSON")
    ap.add_argument("--event", action="append", help="medir sólo este evento (repetible)")
    args = ap.parse_args()

    rows, read_blind = _read_rows()
    if not rows:
        print("sin telemetría legible en .cognitive-os/metrics/", file=sys.stderr)
        return 0

    events = args.event or default_events(rows)
    result = measure(rows, read_blind, events)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"filas leídas: {result['total_rows']}  |  sesiones observadas: {result['sessions']} "
          f"(testigo: {result['session_witness']})")
    print(f"filas con session_id vacío: {result['rows_with_empty_session_id']} "
          f"— por eso la ventana se deriva de {SESSION_EVENT}, no del campo\n")
    print(f"{'evento':<20}{'ocurr.':>8}{'/sesión':>9}{'mediana':>9}{'máx':>7}  testigo")
    for ev in events:
        d = result["events"][ev]
        if not d["observed"]:
            print(f"{ev:<20}{'—':>8}{'—':>9}{'—':>9}{'—':>7}  NO OBSERVADO (ceguera, no ausencia)")
            continue
        per = d["occurrences"] / result["sessions"] if result["sessions"] else 0
        print(f"{ev:<20}{d['occurrences']:>8}{per:>9.1f}{d['median_per_session']:>9}"
              f"{d['max_per_session']:>7}  {d['witness_hook']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
