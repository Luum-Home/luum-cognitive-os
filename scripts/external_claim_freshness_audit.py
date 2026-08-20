#!/usr/bin/env python3
# SCOPE: os-only
"""Censo de frescura de las afirmaciones que este repo hace sobre sistemas AJENOS.

LA DISTINCION QUE ORDENA TODO. Una afirmacion sobre nuestro propio arbol se
puede DERIVAR: si dudo de "hay 47 hooks registrados", cuento los hooks. Una
afirmacion sobre un sistema ajeno solo se puede FECHAR: "opencode soporta
tool.execute.before" no se deriva de nada que tengamos, y el dia que opencode
lo cambie, nuestro archivo sigue diciendo lo mismo con la misma cara. Las
segundas son las perecederas y son el objeto de este script.

QUE MIDE Y QUE NO, dicho arriba para que nadie confie de mas. Mide si la
afirmacion DECLARA cuando se verifico y COMO. No mide si es verdadera: para eso
hay que salir a la red, y este script es read-only y determinista a proposito.
Un `verified: 2026-08-15` recien puesto sin haber mirado la fuente pasa este
audit y miente igual. El audit hace visible la omision, no la falsedad.

EL ERROR QUE ESTE SCRIPT SE NIEGA A COMETER. Un manifest sin fecha de
verificacion no esta "al dia" ni esta "vencido": NO SE PUEDE JUZGAR. Colapsarlo
en cualquiera de los dos lados es la falla que produjo cos_lib/measurement.py.
Por eso las sin fecha van a `blind`, no a un bucket, y por eso el script sale
con codigo 1 cuando la ceguera domina: "0 vencidas" sobre un censo 96% ciego no
es un verde, es un no-observado, y publicarlo como verde seria exactamente el
defecto que el instrumento existe para prevenir.

SIN LISTA FIJA. El censo se deriva del arbol en cada corrida. Una lista escrita
a mano de que archivos revisar nace desactualizada: es la misma forma del
defecto que este instrumento persigue.

Codigos de salida: 0 sin hallazgos / 1 hallazgos / 2 error.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cos_lib.measurement import Census  # noqa: E402

CONFIG_REL = "manifests/external-claim-freshness.yaml"
MANIFEST_DIR_REL = "manifests"

_URL_RE = re.compile(r"https?://([A-Za-z0-9._-]+)")
_DATE_RE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})")

# Hosts que no son "un sistema ajeno": nombrarlos no crea una afirmacion
# perecedera porque no hay nadie del otro lado que pueda cambiarlos.
LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "example.com",
    "www.example.com",
    "host.docker.internal",
}

# Claves cuyo valor afirma algo de un sistema ajeno sin necesidad de URL.
# `license` de un paquete de terceros, la version base de un arnes, el nombre
# con el que se instala desde un registry publico: los tres cambian del otro
# lado sin avisarnos.
ANCHOR_KEYS = {
    "license",
    "licenses",
    "spdx",
    "spdx_id",
    "package_names",
    "package_name",
    "pypi",
    "npm",
    "version_baseline",
    "upstream_version",
    "official_sources",
}

VERIFIED_KEYS = ("verified", "verified_at", "verified_on", "last_verified", "verified_date")
HOW_KEYS = ("how", "verification_command", "verified_how", "how_verified")


class AuditError(RuntimeError):
    """Falla del instrumento, no hallazgo del audit. Sale con 2."""


# ── lectura ──────────────────────────────────────────────────────────────────
def _load_config(repo: Path) -> dict[str, Any]:
    import yaml

    path = repo / CONFIG_REL
    if not path.exists():
        raise AuditError(f"falta {CONFIG_REL}: el umbral vive ahi, no en el codigo")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AuditError(f"{CONFIG_REL} no es un mapping")
    for key in ("default_max_age_days", "blind_ratio_threshold", "default_rationale"):
        if key not in data:
            raise AuditError(f"{CONFIG_REL}: falta {key}")
    for system, entry in (data.get("systems") or {}).items():
        if not isinstance(entry, dict) or not entry.get("cadence_evidence"):
            raise AuditError(
                f"{CONFIG_REL}: systems[{system!r}] fija un umbral sin "
                "cadence_evidence. Un umbral sin la evidencia de cadencia que "
                "lo justifica es un numero inventado con formato de dato."
            )
    return data


def _parse_structured(path: Path) -> Any:
    import yaml

    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


# ── derivacion del censo ─────────────────────────────────────────────────────
def _scalar_anchor(key: str, value: Any) -> str | None:
    """Ancla externa directa de un par clave/valor, o None.

    Devuelve el identificador del sistema ajeno (host de la URL, o la clave que
    lo ancla). No mira mappings anidados: cada mapping se juzga por lo suyo,
    para que una afirmacion no se cuente dos veces en su padre y en su hijo.
    """
    scalars: list[Any] = []
    if isinstance(value, (str, int, float)):
        scalars = [value]
    elif isinstance(value, list) and value and all(
        isinstance(v, (str, int, float)) for v in value
    ):
        scalars = list(value)
    else:
        return None

    for item in scalars:
        if not isinstance(item, str):
            continue
        m = _URL_RE.search(item)
        if m and m.group(1) not in LOCAL_HOSTS:
            return m.group(1)
    if key in ANCHOR_KEYS and any(str(s).strip() for s in scalars):
        return key
    return None


def _first_key(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        m = _DATE_RE.match(value)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                return None
    return None


def _walk(node: Any, path: str, ancestors: tuple[dict[str, Any], ...]) -> Iterator[dict[str, Any]]:
    """Emite un registro por cada mapping con ancla externa DIRECTA."""
    if isinstance(node, dict):
        anchors = []
        for key, value in node.items():
            anchor = _scalar_anchor(str(key), value)
            if anchor:
                anchors.append(anchor)
        chain = ancestors + (node,)
        if anchors:
            verified = None
            how = None
            for scope in reversed(chain):
                if verified is None:
                    verified = _as_date(_first_key(scope, VERIFIED_KEYS))
                if how is None:
                    raw_how = _first_key(scope, HOW_KEYS)
                    how = raw_how if isinstance(raw_how, str) and raw_how.strip() else None
            yield {
                "path": path or "<root>",
                "systems": sorted(set(anchors)),
                "verified": verified,
                "how": how,
            }
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}" if path else str(key), chain)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            yield from _walk(item, f"{path}[{idx}]", ancestors)


def collect_structured_claims(repo: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Recorre el arbol de manifests. Devuelve (registros, archivos ilegibles)."""
    root = repo / MANIFEST_DIR_REL
    if not root.is_dir():
        return [], []
    records: list[dict[str, Any]] = []
    unreadable: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".yaml", ".yml", ".json"} or not path.is_file():
            continue
        rel = path.relative_to(repo).as_posix()
        try:
            data = _parse_structured(path)
        except Exception:  # noqa: BLE001 - cualquier parseo roto es ceguera, no cero
            unreadable.append(rel)
            continue
        for record in _walk(data, "", ()):
            record["file"] = rel
            records.append(record)
    return records, unreadable


def collect_prose_docs(repo: Path, config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Documentos vigentes que citan un sistema externo, y los fechados por construccion."""
    prose = config.get("prose") or {}
    roots = prose.get("roots") or []
    excluded_globs = prose.get("dated_by_construction_globs") or []
    standing: list[str] = []
    dated: list[str] = []
    for root_name in roots:
        root = repo / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            hosts = {h for h in _URL_RE.findall(text) if h not in LOCAL_HOSTS}
            if not hosts:
                continue
            rel = path.relative_to(repo).as_posix()
            if any(fnmatch.fnmatch(rel, g) for g in excluded_globs):
                dated.append(rel)
            else:
                standing.append(rel)
    return standing, dated


def _doc_declares_verification(repo: Path, rel: str) -> bool:
    text = (repo / rel).read_text(encoding="utf-8", errors="replace")
    return bool(re.search(r"^\s*(verified|verified_at|last_verified|Verificado)\s*:", text, re.M))


# ── censos ───────────────────────────────────────────────────────────────────
def _max_age_for(record: dict[str, Any], config: dict[str, Any]) -> tuple[int, str]:
    systems = config.get("systems") or {}
    for system in record["systems"]:
        if system in systems:
            return int(systems[system]["max_age_days"]), system
    return int(config["default_max_age_days"]), "<default>"


def build_censuses(
    repo: Path, config: dict[str, Any], as_of: date
) -> tuple[Census, Census, Census, list[dict[str, Any]]]:
    records, unreadable = collect_structured_claims(repo)
    detail: list[dict[str, Any]] = []
    fresh = stale = undated = 0
    with_how = without_how = 0

    for record in records:
        max_age, source = _max_age_for(record, config)
        verified: date | None = record["verified"]
        if verified is None:
            undated += 1
            verdict, age = "sin_fecha_declarada", None
        else:
            age = (as_of - verified).days
            verdict = "vencida" if age > max_age else "fresca"
            if verdict == "fresca":
                fresh += 1
            else:
                stale += 1
            if record["how"]:
                with_how += 1
            else:
                without_how += 1
        detail.append(
            {
                "file": record["file"],
                "path": record["path"],
                "systems": record["systems"],
                "verified": verified.isoformat() if verified else None,
                "age_days": age,
                "max_age_days": max_age,
                "threshold_source": source,
                "has_verification_command": bool(record["how"]),
                "verdict": verdict,
            }
        )

    structured = Census(
        subject="afirmaciones perecederas estructuradas (manifests/**)",
        how=f".venv/bin/python3 scripts/external_claim_freshness_audit.py --as-of {as_of.isoformat()}",
        sources=(f"{MANIFEST_DIR_REL}/**/*.{{yaml,yml,json}}", CONFIG_REL),
        window=f"as_of={as_of.isoformat()}",
        buckets={"fresca": fresh, "vencida": stale},
        blind={"sin_fecha_declarada": undated, "archivo_ilegible": len(unreadable)},
        notes=(
            "unidad = registro: el mapping mas interno que ancla un sistema ajeno "
            "por URL o por clave externa (license, version_baseline, package_names...)",
            "sin_fecha_declarada NO es 'al dia' ni 'vencida': es no juzgable",
            "el audit mide la DECLARACION de frescura, no la verdad de la afirmacion",
        ),
    )

    method = Census(
        subject="metodo de verificacion reproducible declarado",
        how=f".venv/bin/python3 scripts/external_claim_freshness_audit.py --as-of {as_of.isoformat()}",
        sources=(f"{MANIFEST_DIR_REL}/**/*.{{yaml,yml,json}}",),
        window=f"as_of={as_of.isoformat()}",
        buckets={"con_comando": with_how, "sin_comando": without_how},
        blind={"sin_fecha_no_aplica": undated, "archivo_ilegible": len(unreadable)},
        notes=("solo se juzga el metodo de las que SI declaran fecha",),
    )

    standing, dated = collect_prose_docs(repo, config)
    declares = sum(1 for rel in standing if _doc_declares_verification(repo, rel))
    prose = Census(
        subject="documentos vigentes en prosa que citan un sistema externo",
        how=f".venv/bin/python3 scripts/external_claim_freshness_audit.py --as-of {as_of.isoformat()}",
        sources=("docs/**/*.md", "rules/**/*.md"),
        window=f"as_of={as_of.isoformat()}",
        buckets={"declara_verificacion": declares, "no_declara": len(standing) - declares},
        blind={"fechado_por_construccion": len(dated)},
        notes=(
            "unidad = documento, NO comparable con el censo estructurado",
            "el instrumento no puede localizar la afirmacion adentro de la prosa: "
            "solo ve si el documento declara una marca de verificacion",
            "reportes diarios y ADR quedan fuera del juicio: llevan su fecha en el "
            "nombre y son registros historicos, no afirmaciones vigentes",
        ),
    )
    return structured, method, prose, detail


# ── salida ───────────────────────────────────────────────────────────────────
def _render(structured: Census, method: Census, prose: Census, detail, config) -> str:
    out = [structured.render(), ""]
    out.append(f"  vencidas: {structured.describe('vencida')}")
    out.append(f"  frescas : {structured.describe('fresca')}")
    out.append("")
    out.append(method.render())
    out.append("")
    out.append(prose.render())
    out.append("")
    out.append(
        f"umbral por defecto: {config['default_max_age_days']} dias "
        f"({CONFIG_REL}: default_rationale)"
    )
    sin_fecha = Counter(
        r["file"] for r in detail if r["verdict"] == "sin_fecha_declarada"
    )
    if sin_fecha:
        out.append("")
        out.append("archivos con afirmaciones externas sin fecha de verificacion:")
        for name, count in sin_fecha.most_common():
            out.append(f"  {count:4d}  {name}")
    vencidas = [r for r in detail if r["verdict"] == "vencida"]
    if vencidas:
        out.append("")
        out.append("afirmaciones vencidas:")
        for r in vencidas:
            out.append(
                f"  {r['file']}#{r['path']}  verificada {r['verified']} "
                f"({r['age_days']}d > {r['max_age_days']}d, umbral {r['threshold_source']})"
            )
    if not structured.is_a_finding("vencida"):
        out.append("")
        out.append(
            "AVISO: 0 vencidas NO es un verde. La ceguera domina el censo "
            f"({structured.blind_total} de {structured.population} sin fecha declarada): "
            "el instrumento no pudo juzgar la mayoria de las afirmaciones."
        )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-dir", default=str(REPO))
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="fecha de referencia YYYY-MM-DD; explicitala para reproducir una corrida",
    )
    parser.add_argument("--json", action="store_true", help="salida JSON")
    args = parser.parse_args(argv)

    try:
        repo = Path(args.project_dir).resolve()
        as_of = date.fromisoformat(args.as_of)
        config = _load_config(repo)
        structured, method, prose, detail = build_censuses(repo, config, as_of)
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "as_of": as_of.isoformat(),
                    "structured": structured.to_dict(),
                    "method": method.to_dict(),
                    "prose": prose.to_dict(),
                    "claims": detail,
                    "default_max_age_days": config["default_max_age_days"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(_render(structured, method, prose, detail, config))

    blind_limit = float(config["blind_ratio_threshold"])
    blind_ratio = structured.blind_ratio or 0.0
    findings = structured.count("vencida") > 0 or blind_ratio > blind_limit
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
