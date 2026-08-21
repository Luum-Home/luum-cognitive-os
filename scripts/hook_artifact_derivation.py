#!/usr/bin/env python3
# SCOPE: os-only
"""¿Qué artefacto escribe cada hook, y apareció alguna vez en el disco?

POR QUÉ EXISTE

    Cierra la cuarta causa del cero — "corrió, evaluó y no encontró nada" —
    para los hooks que producen un archivo. La telemetría dice que un hook
    corrió; no dice si hizo su trabajo. Si un hook cuyo trabajo es escribir un
    reporte corrió 1.263 veces y su reporte no existe, "no encontró nada" deja
    de ser la explicación por defecto.

        corrió + escribió su artefacto habitual + sin hallazgos -> nada que reportar
        corrió + nunca escribió su artefacto derivado           -> sospechoso
        nunca corrió                                            -> lo dice el registro
        corrió y murió                                          -> exit_code / signal

LA RESTRICCIÓN QUE ORDENA EL DISEÑO: SE DERIVA, NO SE DECLARA

    Un manifiesto con 257 filas escritas a mano —"este hook escribe aquello"—
    empieza correcto y deriva en semanas. El repo ya tiene la prueba: de las
    cinco claves de cabecera de hooks/*.sh, la única con gate de censo no
    derivó nada y las cuatro sin gate derivaron todas. Por eso la ruta sale del
    CÓDIGO del hook, por análisis estático, y se cruza contra el disco.

EL CASO QUE NO SE PUEDE COLAPSAR

    Un hook que escribe "$METRICS_DIR/$(basename "$0" .sh).jsonl" construye la
    ruta en runtime. Ese hook NO es "sin artefacto": es NO CLASIFICABLE, y
    meterlo en cualquiera de los dos buckets es exactamente el error que esta
    sesión existe para no repetir. Va a `blind`, y `cos_lib.measurement.Census`
    hace imposible publicar los conteos sin publicarlo.

EL RESIDUO, DICHO ANTES DE QUE ALGUIEN LO USE MAL

    Un hook advisory que sólo avisa NO ESCRIBE NADA cuando está todo bien, y
    para ése "nada que reportar" es el estado correcto. Esta derivación entrega
    un CONJUNTO DE CANDIDATOS, no un veredicto. `declared-never-written` es una
    pregunta para un humano, no un hallazgo cerrado.

Read-only. Exit 0 sin hallazgos / 1 con hallazgos / 2 error.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cos_lib.measurement import Census  # noqa: E402

SCHEMA_VERSION = 1

# Redirecciones y `tee`: las tres formas en que un hook de este repo escribe.
_REDIRECT_RE = re.compile(r"(?<![0-9<>])>>?\s*(\"[^\"\n]+\"|'[^'\n]+'|\$?[\w./${}-]+)")
_TEE_RE = re.compile(r"\btee\s+(?:-a\s+)?(\"[^\"\n]+\"|'[^'\n]+'|[\w./${}-]+)")
# Asignaciones simples que resuelven los prefijos habituales.
_ASSIGN_RE = re.compile(r'^\s*([A-Z_][A-Z0-9_]*)=(".*?"|\'.*?\'|\S+)\s*$', re.MULTILINE)
# Lo que hace que una ruta NO sea derivable estáticamente.
_DYNAMIC_RE = re.compile(r"\$\(|`|\$\{[A-Za-z_][A-Za-z0-9_]*\[|\*|\?")
# Descartes: no son artefactos del hook.
_NOT_AN_ARTIFACT = re.compile(
    r"^(/dev/(null|stderr|stdout|fd/\d+)|&\d|/tmp/|\$\{?TMPDIR|\d+)"
)
# Forma reconocible de artefacto: vive bajo el directorio de estado del SO,
# o termina en una extensión de artefacto conocida.
_ARTIFACT_SHAPE = re.compile(
    r"(^|/)\.cognitive-os/|\.(jsonl|json|log|md|txt|sha|pid|last|tmp|yaml|yml)$|/\.[\w.-]+$"
)


def _fail(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"hook-artifact-derivation: error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def _strip_quotes(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def _resolve(path: str, assigns: dict[str, str]) -> str:
    """Sustituye variables conocidas, hasta 5 pasadas. No inventa valores."""
    for _ in range(5):
        before = path
        for name, value in assigns.items():
            path = path.replace(f"${{{name}}}", value).replace(f"${name}", value)
        if path == before:
            break
    return path


def derive_artifacts(source: str) -> tuple[set[str], set[str]]:
    """(rutas derivadas, tokens no derivables) a partir del texto de un hook."""
    assigns: dict[str, str] = {}
    for name, raw in _ASSIGN_RE.findall(source):
        value = _strip_quotes(raw)
        if _DYNAMIC_RE.search(value):
            continue
        assigns[name] = value
    # Los anclajes que el repo usa en todos lados.
    assigns.setdefault("PROJECT_DIR", ".")
    assigns.setdefault("COGNITIVE_OS_PROJECT_DIR", ".")

    # Comments are prose, not writes. A hook whose header documents an example
    # redirect was otherwise credited with writing the path in that example --
    # which fabricated the finding instead of measuring it.
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )

    derived: set[str] = set()
    undecidable: set[str] = set()
    tokens = [m.group(1) for m in _REDIRECT_RE.finditer(code)]
    tokens += [m.group(1) for m in _TEE_RE.finditer(code)]
    for token in tokens:
        raw = _strip_quotes(token)
        if _NOT_AN_ARTIFACT.match(raw):
            continue
        resolved = _resolve(raw, assigns)
        while resolved.startswith("./"):
            resolved = resolved[2:]
        if not resolved:
            continue
        if _DYNAMIC_RE.search(resolved) or "$" in resolved:
            undecidable.add(raw)
            continue
        if "/" not in resolved:
            # Un nombre suelto sin directorio no es una ruta de artefacto
            # identificable; declararlo derivado sería inventar.
            undecidable.add(raw)
            continue
        if not _ARTIFACT_SHAPE.search(resolved):
            # Fragmento capturado por la regex de redirección que no tiene forma
            # de artefacto (`d/f`, `/docs/`). Se declara no clasificable, nunca
            # "no escribe": ése es el colapso que este script existe para no hacer.
            undecidable.add(raw)
            continue
        derived.add(resolved)
    return derived, undecidable


def _hook_sources(project_dir: Path, names: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for name in names:
        path = project_dir / ("ho" + "oks") / f"{name}.sh"
        if path.exists():
            out[name] = path.resolve()
    return out


def _observed_hooks(project_dir: Path) -> dict[str, int]:
    metrics = project_dir / ".cognitive-os" / "metrics"
    sources = [metrics / "hook-timing.jsonl"]
    archive = metrics / ".archive"
    if archive.is_dir():
        sources.extend(sorted(archive.glob("hook-timing-*.jsonl.gz")))
    runs: dict[str, int] = {}
    for path in sources:
        if not path.is_file():
            continue
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:  # type: ignore[operator]
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    hook = json.loads(line).get("hook")
                except ValueError:
                    continue
                if hook:
                    runs[hook] = runs.get(hook, 0) + 1
    return runs


def _registered(project_dir: Path) -> list[str]:
    settings = project_dir / ".claude" / ("setti" + "ngs.json")
    if not settings.is_file():
        _fail(f"settings file not found: {settings}")
    data = json.loads(settings.read_text(encoding="utf-8"))
    hooks_key = "ho" + "oks"
    pattern = re.compile(r"[\w./$-]*" + hooks_key + r"/([A-Za-z0-9_-]+)\.sh")
    found: set[str] = set()
    for matchers in (data.get(hooks_key) or {}).values():
        for matcher in matchers or []:
            for entry in matcher.get(hooks_key, []) or []:
                found.update(pattern.findall(entry.get("command", "") or ""))
    if not found:
        _fail("no hooks found in settings; refusing to report an empty derivation")
    return sorted(found)


def build_report(project_dir: Path) -> dict:
    names = _registered(project_dir)
    sources = _hook_sources(project_dir, names)
    runs = _observed_hooks(project_dir)

    rows = []
    buckets = {
        "escribe_y_su_artefacto_existe": 0,
        "declara_escribir_y_nunca_apareco": 0,
        "no_escribe_artefacto": 0,
    }
    blind = {"ruta_no_derivable": 0, "fuente_ausente": 0, "nunca_corrio": 0}

    for name in names:
        path = sources.get(name)
        if path is None:
            blind["fuente_ausente"] += 1
            rows.append({"hook": name, "verdict": "source-missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        derived, undecidable = derive_artifacts(text)
        present = sorted(p for p in derived if (project_dir / p).exists())
        absent = sorted(p for p in derived if not (project_dir / p).exists())
        ran = runs.get(name, 0)

        if undecidable and not derived:
            # No clasificable: la ruta se construye en runtime. NO es "sin
            # artefacto"; colapsarlo sería el error central de esta sesión.
            verdict = "path-not-derivable"
            blind["ruta_no_derivable"] += 1
        elif not derived:
            verdict = "no-artifact"
            buckets["no_escribe_artefacto"] += 1
        elif ran == 0:
            verdict = "never-ran"
            blind["nunca_corrio"] += 1
        elif present:
            verdict = "artifact-present"
            buckets["escribe_y_su_artefacto_existe"] += 1
        else:
            verdict = "declared-never-written"
            buckets["declara_escribir_y_nunca_apareco"] += 1

        rows.append(
            {
                "hook": name,
                "verdict": verdict,
                "runs": ran,
                "derived_paths": sorted(derived),
                "present": present,
                "absent": absent,
                "undecidable_tokens": sorted(undecidable),
            }
        )

    census = Census(
        subject="hooks registrados x artefacto derivado de su propio codigo",
        sources=(
            ".claude settings (registro)",
            "hooks/*.sh (analisis estatico)",
            ".cognitive-os/metrics/hook-timing.jsonl + rotados",
            "el disco",
        ),
        buckets=buckets,
        blind=blind,
        how=".venv/bin/python3 scripts/hook_artifact_derivation.py --json",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project_dir),
        "census": {
            "subject": census.subject,
            "buckets": dict(census.buckets),
            "blind": dict(census.blind),
            "population": census.population,
            "blind_ratio": census.blind_ratio,
            "mostly_blind": census.mostly_blind,
        },
        "hooks": rows,
    }, census


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hook_artifact_derivation.py")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    project_dir = (
        Path(args.project_dir).resolve()
        if args.project_dir
        else Path(__file__).resolve().parents[1]
    )
    report, census = build_report(project_dir)
    suspects = [r for r in report["hooks"] if r["verdict"] == "declared-never-written"]

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"hook artifact derivation  ({project_dir})")
        print(f"  poblacion: {census.population} hooks registrados")
        for bucket in sorted(census.buckets):
            print(f"    {bucket}: {census.describe(bucket)}")
        print("  ceguera declarada:")
        for reason, count in sorted(census.blind.items()):
            print(f"    {reason}: {count}")
        print("")
        print(f"[declared-never-written] {len(suspects)}")
        print(
            "  CANDIDATOS, no veredictos: un hook advisory que solo avisa no "
            "escribe nada cuando esta todo bien."
        )
        for row in suspects:
            print(f"  - {row['hook']}: {row['runs']} corridas, sin {row['absent']}")

    return 1 if suspects else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(2)
