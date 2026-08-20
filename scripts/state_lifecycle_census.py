#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Censo forense del estado de runtime: quien lo escribe, quien lo LEE para DECIDIR,
y si alguien lo resetea.

Contesta en un comando las cuatro preguntas que el informe
docs/06-Daily/reports/forense-estado-sin-ciclo-de-vida-2026-08-20.md abrio a mano:

  1. quien escribe cada superficie de estado (ruta:linea),
  2. quien la lee, y si la lectura GOBIERNA una decision o solo REPORTA,
  3. si tiene ciclo de vida (reaper declarado en manifests/state-retention.yaml,
     o codigo de reset/rm/truncate encontrado en el repo),
  4. cuanto hace que existe y cuanto pesa.

El cruce produce cuatro cubetas: gobierna-sin-reset (el hallazgo),
gobierna-con-ciclo (sano), solo-reporta, nadie-lo-lee (deuda).

READ-ONLY sobre .cognitive-os/. No escribe, no borra, no toca estado de runtime.

Exit codes: 0 sin hallazgos / 1 hay superficies que gobiernan sin reset / 2 error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cos_lib.measurement import Census  # noqa: E402

RUNTIME = REPO / ".cognitive-os" / "runtime"
METRICS = REPO / ".cognitive-os" / "metrics"
METRICS_ARCHIVE = METRICS / ".archive"
MANIFEST = REPO / "manifests" / "state-retention.yaml"

# Superficies de codigo donde puede vivir un escritor o un lector.
CODE_DIRS = (
    "hooks",
    "scripts",
    "cos_lib",
    "lib",
    "tests",
    "packages",
    "templates",
    "cmd",
    "commands",
    "skills",
    ".claude",
    ".codex",
    ".opencode",
)
CODE_EXT = {".py", ".sh", ".bash", ".go", ".js", ".ts", ".json", ".yaml", ".yml", ".toml"}

# Un token identificatorio mas corto que esto produce falsos positivos por
# substring (p.ej. "locks" aparece en cualquier lado).
MIN_TOKEN = 8

# Ruido dinamico que hay que colapsar para que 34 snapshots sean UNA familia.
DYNAMIC = [
    (re.compile(r"toolu_[A-Za-z0-9]{8,}"), "*"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "*"),
    (re.compile(r"\b[0-9a-f]{12,}\b"), "*"),
    (re.compile(r"\b\d{6,}\b"), "*"),
]

# Un lector GOBIERNA si el codigo que lo lee puede negar, bloquear, cortar o
# comparar contra un umbral. Es una heuristica que ESTRECHA: marca candidatos
# para confirmacion humana, no dicta el veredicto.
GOVERN_PAT = re.compile(
    r"exit\s+2\b|\bdeny\b|\bblock(ed|ing)?\b|permissionDecision|"
    r"hookSpecificOutput|\bBLOCK\b|-ge\s|-gt\s|>=\s*\d|"
    r"sys\.exit\(\s*2|\bthreshold\b|\bumbral\b|should_throttle|\bstale\b",
    re.IGNORECASE,
)
WRITE_PAT = re.compile(
    r">>?\s*[\"']?\$?\{?[A-Za-z_./]|\btee\b|write_text|json\.dump|\bmkdir\b|\btouch\b|"
    r"open\([^)]*[\"']w|\bcp\b|\bmv\b|Path\([^)]*\)\.write|f\.write",
)
RESET_PAT = re.compile(r"\brm\b|\bunlink\b|\brmtree\b|\btruncate\b|:\s*>\s|\breset\b|\bprune\b|\bmissing_ok\b")


def norm_family(name: str) -> str:
    out = name
    for pat, rep in DYNAMIC:
        out = pat.sub(rep, out)
    out = re.sub(r"\*+", "*", out)
    return out


def token_of(family: str) -> str:
    """Prefijo estable buscable en el codigo."""
    head = family.split("*")[0].rstrip("-_.")
    return head


def stat_of(path: Path) -> dict:
    try:
        st = path.stat()
    except OSError:
        return {}
    birth = getattr(st, "st_birthtime", st.st_ctime)
    if path.is_dir():
        size = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
        count = sum(1 for p in path.rglob("*") if p.is_file())
    else:
        size = st.st_size
        count = 1
    return {"birth": int(birth), "mtime": int(st.st_mtime), "bytes": size, "members": count}


def load_code() -> list[tuple[str, list[str]]]:
    files: list[tuple[str, list[str]]] = []
    for d in CODE_DIRS:
        root = REPO / d
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [x for x in dirnames if x not in {"node_modules", ".git", "__pycache__"}]
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    if p.suffix.lower() not in CODE_EXT:
                        # Ceguera corregida 2026-08-20: scripts/cos-graphify-* no
                        # tienen extension y quedaban fuera del barrido, lo que
                        # inventaba dos "nadie lo lee" que si tenian productor.
                        if p.suffix or not os.access(p, os.X_OK):
                            continue
                        with p.open("rb") as fh:
                            if fh.read(2) != b"#!":
                                continue
                    if p.stat().st_size > 2_000_000:
                        continue
                    files.append(
                        (str(p.relative_to(REPO)), p.read_text(errors="replace").splitlines())
                    )
                except OSError:
                    continue
    return files


def registered_surfaces() -> list[dict]:
    try:
        import yaml
    except ImportError:
        return []
    data = yaml.safe_load(MANIFEST.read_text())
    return data.get("surfaces", []) or []


def manifest_covers(rel: str, surfaces: list[dict]) -> str | None:
    from fnmatch import fnmatch

    for s in surfaces:
        pat = str(s.get("path", ""))
        if not pat.startswith(".cognitive-os"):
            continue
        if fnmatch(rel, pat) or fnmatch(rel, pat.rstrip("/") + "/*"):
            return s["id"]
    return None


def archived_rotations(stem: str) -> int:
    """Ceguera #1: contar solo el archivo vivo inventa 'nunca se escribio'."""
    if not METRICS_ARCHIVE.exists():
        return 0
    return sum(1 for p in METRICS_ARCHIVE.glob(f"{stem}*.jsonl.gz"))


def build() -> dict:
    surfaces = registered_surfaces()
    code = load_code()

    population: dict[str, dict] = {}

    def add(path: Path, area: str) -> None:
        rel = str(path.relative_to(REPO))
        fam = norm_family(path.name)
        key = f"{area}:{norm_family(rel)}"
        entry = population.setdefault(
            key,
            {
                "area": area,
                "family": fam,
                "pattern": norm_family(rel),
                "token": token_of(fam),
                "instances": 0,
                "bytes": 0,
                "members": 0,
                "birth": None,
                "mtime": None,
                "example": rel,
                "is_dir": path.is_dir(),
            },
        )
        st = stat_of(path)
        entry["instances"] += 1
        entry["bytes"] += st.get("bytes", 0)
        entry["members"] += st.get("members", 0)
        b = st.get("birth")
        if b and (entry["birth"] is None or b < entry["birth"]):
            entry["birth"] = b
        m = st.get("mtime")
        if m and (entry["mtime"] is None or m > entry["mtime"]):
            entry["mtime"] = m
        if entry.get("surface") is None:
            entry["surface"] = manifest_covers(rel, surfaces)

    for p in sorted(RUNTIME.iterdir()) if RUNTIME.exists() else []:
        add(p, "runtime")
    for p in sorted(METRICS.glob("*.jsonl")):
        add(p, "metrics")

    for entry in population.values():
        tok = entry["token"]
        entry["writers"] = []
        entry["readers"] = []
        entry["governing"] = []
        entry["resetters"] = []
        if len(tok) < MIN_TOKEN:
            entry["token_too_short"] = True
            continue
        entry["token_too_short"] = False
        for relfile, lines in code:
            for i, line in enumerate(lines, 1):
                if tok not in line:
                    continue
                ref = f"{relfile}:{i}"
                is_test = relfile.startswith("tests/")
                if WRITE_PAT.search(line):
                    entry["writers"].append(ref)
                else:
                    entry["readers"].append(ref)
                if RESET_PAT.search(line):
                    entry["resetters"].append(ref)
                # Gobierna: la decision se toma cerca de la lectura.
                ctx = "\n".join(lines[max(0, i - 4) : i + 8])
                if not is_test and GOVERN_PAT.search(ctx):
                    entry["governing"].append(ref)
        if entry["area"] == "metrics":
            entry["rotations"] = archived_rotations(Path(entry["example"]).stem)

    for entry in population.values():
        has_reader = bool(entry["readers"]) or bool(entry["governing"])
        governs = bool(entry["governing"])
        has_cycle = bool(entry["surface"]) or bool(entry["resetters"])
        if entry["token_too_short"]:
            entry["bucket"] = "indeterminado-token-corto"
        elif not has_reader and not entry["writers"]:
            entry["bucket"] = "nadie-lo-lee"
        elif not has_reader:
            entry["bucket"] = "nadie-lo-lee"
        elif governs and not has_cycle:
            entry["bucket"] = "gobierna-sin-reset"
        elif governs:
            entry["bucket"] = "gobierna-con-ciclo"
        else:
            entry["bucket"] = "solo-reporta"

    return population


HOW = "python3 scripts/state_lifecycle_census.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--bucket", help="filtrar por cubeta")
    args = ap.parse_args()

    pop = build()
    buckets: dict[str, int] = {}
    for e in pop.values():
        buckets[e["bucket"]] = buckets.get(e["bucket"], 0) + 1

    blind = {
        "decide-vs-reporta-es-heuristica": sum(
            1 for e in pop.values() if e["bucket"].startswith("gobierna")
        ),
        "token-demasiado-corto-para-buscar": sum(
            1 for e in pop.values() if e.get("token_too_short")
        ),
        "sesiones-vivas-escribiendo-durante-la-medicion": 1,
        "lectores-fuera-del-repo-operador-scripts-ad-hoc": 0,
    }

    census = Census(
        subject="superficies de estado en .cognitive-os/runtime y /metrics",
        sources=(
            ".cognitive-os/runtime/ (entradas de primer nivel, familias normalizadas)",
            ".cognitive-os/metrics/*.jsonl (vivos) + .archive/*.jsonl.gz (rotados)",
            "manifests/state-retention.yaml (reapers declarados)",
            "codigo: " + ", ".join(CODE_DIRS),
        ),
        buckets=buckets,
        blind=blind,
        how=HOW,
        notes=(
            "La familia, no el archivo, es la unidad: 34 suppress-agent-snapshot-toolu_* "
            "son UNA superficie con una politica, no 34 problemas.",
            "GOVERN_PAT estrecha candidatos; el veredicto 'gobierna' se confirma leyendo "
            "el lector. Un falso positivo sobra en el informe, un falso negativo se pierde.",
        ),
    )

    if args.json:
        out = {
            "census": {k: v for k, v in asdict(census).items()},
            "surfaces": pop,
        }
        print(json.dumps(out, indent=2, sort_keys=True, default=str))
    else:
        print(f"# {census.subject}")
        print(f"# how: {census.how}")
        print(f"# poblacion: {sum(buckets.values())} familias")
        for k in sorted(census.sources):
            print(f"#   fuente: {k}")
        print()
        for name, n in sorted(buckets.items(), key=lambda kv: -kv[1]):
            print(f"{n:4d}  {name}")
        print()
        for name, n in sorted(blind.items()):
            print(f"ciego  {name}: {n}")
        print()
        for e in sorted(pop.values(), key=lambda x: (x["bucket"], x["pattern"])):
            if args.bucket and e["bucket"] != args.bucket:
                continue
            if e["bucket"] not in ("gobierna-sin-reset", "nadie-lo-lee") and not args.bucket:
                continue
            print(f"[{e['bucket']}] {e['pattern']}")
            print(
                f"    instancias={e['instances']} miembros={e['members']} "
                f"bytes={e['bytes']} surface={e['surface']}"
            )
            if e["writers"]:
                print(f"    escribe: {', '.join(e['writers'][:3])}")
            if e["governing"]:
                print(f"    gobierna: {', '.join(e['governing'][:3])}")
            if e["resetters"]:
                print(f"    resetea: {', '.join(e['resetters'][:3])}")

    return 1 if buckets.get("gobierna-sin-reset") else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
