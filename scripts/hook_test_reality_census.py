#!/usr/bin/env python3
# SCOPE: os-only
"""Censo de suites verdes sobre hooks sin actividad observable en produccion.

Cruza los ``behavior_tests`` de ``manifests/hook-quality.yaml`` contra la
telemetria real de cada hook (``hook-timing.jsonl`` VIVO + sus rotados ``.gz``)
y clasifica el cero. El punto del script es NO colapsar las tres causas
distintas de "cero filas":

  - roto            -> corrio y murio (exit != 0 y != 2, o signal/timeout)
  - nunca corrio    -> sin filas de telemetria, o todas las filas 'skipped'
  - silencioso      -> corrio, salio 0, nunca emitio bytes  <- INDETERMINADO

Un ``exit_code == 2`` NO es un error: en PreToolUse es la senal de bloqueo
deliberado que define el schema del harness. Contarlo como rotura fue el primer
bug de este mismo script, y es la misma falla que viene a medir.

El tercero NO es un hallazgo: desde la telemetria no se distingue "no tenia
nada que reportar" (sano) de "parsea mal y se calla" (roto). Va a ``blind``.

Solo se consideran los tests que NOMBRAN al script del hook: el mapeo
``behavior_tests`` del manifiesto es generado y asocia suites genericas a
muchos hooks, asi que cruzarlo crudo sobrecuenta por un orden de magnitud.

Uso:
    .venv/bin/python3 scripts/hook_test_reality_census.py [--json]

Exit: 0 sin hallazgos / 1 hallazgos / 2 error.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cos_lib.measurement import Census  # noqa: E402

MANIFEST = REPO / "manifests" / "hook-quality.yaml"
SETTINGS = REPO / ".claude" / "settings.json"
TIMING_LIVE = REPO / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
TIMING_ARCHIVE = REPO / ".cognitive-os" / "metrics" / ".archive"


def _timing_sources() -> list[Path]:
    """Vivo + rotados. Contar solo el vivo produce falsos 'nunca disparo'."""
    sources = [TIMING_LIVE] if TIMING_LIVE.exists() else []
    if TIMING_ARCHIVE.is_dir():
        sources += sorted(TIMING_ARCHIVE.glob("hook-timing-*.jsonl.gz"))
    return sources


def _read_timing(sources: list[Path]) -> dict[str, dict]:
    agg: dict[str, dict] = defaultdict(
        lambda: {"runs": 0, "died": 0, "blocked": 0, "skipped": 0, "emitted": 0}
    )
    for path in sources:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", errors="ignore") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except (ValueError, TypeError):
                    continue
                name = row.get("hook") or ""
                if not name:
                    continue
                slot = agg[name]
                slot["runs"] += 1
                code = row.get("exit_code")
                status = row.get("execution_status")
                if status == "skipped" or row.get("skipped"):
                    slot["skipped"] += 1
                elif code == 2:
                    slot["blocked"] += 1  # bloqueo deliberado, no rotura
                elif code not in (0, None) or status in ("signal", "timeout"):
                    slot["died"] += 1
                if (row.get("stdout_bytes") or 0) or (row.get("stderr_bytes") or 0):
                    slot["emitted"] += 1
    return agg


def _dedicated_tests(hook_name: str, script: str, tests: list[str]) -> list[str]:
    """Tests que nombran al hook. El resto del mapeo del manifiesto es ruido."""
    needles = {hook_name, Path(script).name, Path(script).stem}
    hits = []
    for rel in tests:
        path = REPO / rel
        if not path.exists():
            continue
        try:
            body = path.read_text(errors="ignore")
        except OSError:
            continue
        if any(n and n in body for n in needles):
            hits.append(rel)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args()

    try:
        import yaml

        manifest = yaml.safe_load(MANIFEST.read_text())
        settings_blob = SETTINGS.read_text() if SETTINGS.exists() else ""
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: no se pudo leer el manifiesto/settings: {exc}", file=sys.stderr)
        return 2

    sources = _timing_sources()
    if not sources:
        print("ERROR: sin telemetria de hook-timing (ni viva ni rotada)", file=sys.stderr)
        return 2
    timing = _read_timing(sources)

    buckets: dict[str, int] = defaultdict(int)
    blind: dict[str, int] = defaultdict(int)
    detail: dict[str, list] = defaultdict(list)

    for name, meta in sorted((manifest.get("hooks") or {}).items()):
        script = meta.get("script") or ""
        tests = _dedicated_tests(name, script, meta.get("behavior_tests") or [])
        if not tests:
            continue  # sin suite dedicada: fuera de la pregunta
        t = timing.get(name, {"runs": 0, "died": 0, "blocked": 0, "skipped": 0, "emitted": 0})
        registered = bool(script) and re.search(re.escape(Path(script).name), settings_blob) is not None
        row = {"hook": name, "tests": tests, "runs": t["runs"], "registered": registered,
               "emitted": t["emitted"], "died": t["died"], "blocked": t["blocked"],
               "skipped": t["skipped"]}

        if t["runs"] == 0:
            key = "cero_nunca_corrio_sin_registrar" if not registered else "cero_registrado_sin_telemetria"
            if registered:
                blind[key] += 1  # matcher que nunca matcheo vs wrapper ausente: no distinguible
            else:
                buckets[key] += 1
            detail[key].append(row)
        elif t["skipped"] == t["runs"]:
            buckets["cero_cuerpo_nunca_corrio_skipped"] += 1
            detail["cero_cuerpo_nunca_corrio_skipped"].append(row)
        elif t["died"]:
            buckets["cero_por_error_roto"] += 1
            detail["cero_por_error_roto"].append(row)
        elif t["blocked"] or t["emitted"]:
            buckets["emite_en_produccion"] += 1
            detail["emite_en_produccion"].append(row)
        else:
            blind["cero_silencioso_indeterminado"] += 1
            detail["cero_silencioso_indeterminado"].append(row)

    census = Census(
        subject="hooks con suite dedicada, por actividad observable en produccion",
        sources=tuple(str(p.relative_to(REPO)) for p in sources[:3]) + (f"(+{max(0, len(sources) - 3)} rotados mas)",),
        buckets=dict(buckets) or {"ninguno": 0},
        blind=dict(blind) or {"ninguna": 0},
        window="toda la telemetria retenida (viva + rotada)",
        notes=(
            "cero_silencioso_indeterminado NO es un hallazgo: la telemetria no "
            "distingue 'nada que reportar' de 'parsea mal y se calla'.",
            "exit_code==2 se cuenta como bloqueo deliberado (schema del harness), "
            "no como rotura; execution_status=='skipped' es cuerpo-nunca-corrio.",
            "Solo cuentan los tests que nombran al hook; el mapeo behavior_tests "
            "del manifiesto es generado y sobrecuenta.",
        ),
    )

    if args.json:
        print(json.dumps({
            "subject": census.subject, "sources": list(census.sources),
            "buckets": dict(census.buckets), "blind": dict(census.blind),
            "population": census.population, "blind_ratio": census.blind_ratio,
            "detail": {k: v for k, v in detail.items()},
        }, indent=2))
    else:
        print(f"CENSO: {census.subject}")
        print(f"  fuentes    : {len(sources)} archivos de hook-timing (vivo + rotados)")
        print(f"  poblacion  : {census.population} hooks con suite dedicada")
        print("  --- medible ---")
        for k, v in sorted(census.buckets.items()):
            print(f"    {k:38s} {v}")
        print("  --- ciego (no clasificable con esta telemetria) ---")
        for k, v in sorted(census.blind.items()):
            print(f"    {k:38s} {v}")
        ratio = census.blind_ratio
        print(f"  ceguera    : {ratio:.1%}" if ratio is not None else "  ceguera    : n/a")
        for key in ("cero_por_error_roto", "cero_cuerpo_nunca_corrio_skipped",
                    "cero_nunca_corrio_sin_registrar"):
            if detail.get(key):
                print(f"\n  [{key}]")
                for row in detail[key]:
                    print(f"    - {row['hook']}: runs={row['runs']} murio={row['died']} "
                          f"skip={row['skipped']} registrado={row['registered']} "
                          f"tests={len(row['tests'])}")

    findings = buckets.get("cero_por_error_roto", 0) + buckets.get("cero_nunca_corrio_sin_registrar", 0)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
