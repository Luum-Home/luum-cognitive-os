# SPDX-License-Identifier: MIT
"""Censo estatico de CONTENIDO muerto dentro de artefactos vivos.

La maquinaria de ciclo de vida del repo (manifests/primitive-lifecycle.yaml,
skill adr-tombstone) marca ARTEFACTOS. Este censo busca la clase que esa
maquinaria no puede nombrar: contenido muerto ADENTRO de un artefacto vivo.

Tres formas, todas decidibles sin ejecutar nada:

  A  campo-de-un-solo-valor : un campo presente en toda una poblacion de
     registros con exactamente un valor distinto -> cero informacion.
  B  referencia-colgante    : una entrada de manifiesto cuyo path no existe
     en disco (resolviendo symlinks, que este repo usa masivamente).
  C  variable-escrita-nunca-leida : una variable de shell asignada en un
     script y jamas leida en ese mismo script.

Read-only. Deterministico. Exit codes: 0 sin hallazgos / 1 hallazgos / 2 error.

Uso:
    python3 scripts/dead_content_census.py            # resumen
    python3 scripts/dead_content_census.py --json     # maquina
    python3 scripts/dead_content_census.py --form A   # una sola forma
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Poblaciones de registros a auditar por la forma A. Cada entrada es
# (etiqueta, glob, cargador). El cargador devuelve una lista de dicts.
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}

# Minimo de registros para que "un solo valor" signifique algo.
FORM_A_MIN_RECORDS = 20


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(suffixes):
                out.append(Path(dirpath) / name)
    return sorted(out)


def _load_records(path: Path) -> list[dict]:
    """Devuelve la poblacion de registros dict de un archivo de datos."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if path.suffix == ".jsonl":
        recs = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                recs.append(obj)
        return recs
    if path.suffix in (".yaml", ".yml"):
        # Solo YAML plano `clave: valor` (formato de los meta.yaml de lock).
        # Un parser completo no aporta: las poblaciones que interesan son planas.
        rec: dict = {}
        for line in text.splitlines():
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if m:
                rec[m.group(1)] = m.group(2).strip()
        return [rec] if rec else []
    if path.suffix == ".json":
        try:
            obj = json.loads(text)
        except ValueError:
            return []
        if isinstance(obj, list):
            return [o for o in obj if isinstance(o, dict)]
        if isinstance(obj, dict):
            # un dict cuyos valores son todos dicts tambien es una poblacion
            vals = list(obj.values())
            if len(vals) >= FORM_A_MIN_RECORDS and all(
                isinstance(v, dict) for v in vals
            ):
                return vals
        return []
    return []


def form_a_single_valued(roots: list[Path]) -> list[dict]:
    """Campos presentes en toda una poblacion con un unico valor distinto."""
    findings: list[dict] = []
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(_iter_files(root, (".json", ".jsonl", ".yaml", ".yml")))
        elif root.is_file():
            files.append(root)

    # Poblaciones distribuidas: muchos archivos chicos con el mismo nombre
    # (un `meta.yaml` por lock) forman UNA poblacion, no N poblaciones de 1.
    # La clave es (raiz escaneada, basename), no el directorio: los locks
    # viven cada uno en su propio subdirectorio.
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    root_of = {}
    for root in roots:
        for f in files:
            if root in f.parents or root == f:
                root_of.setdefault(f, root)
    for f in files:
        recs = _load_records(f)
        if not recs:
            continue
        if len(recs) >= FORM_A_MIN_RECORDS:
            findings.extend(_scan_population(str(f.relative_to(REPO)), recs))
        else:
            root = root_of.get(f, f.parent)
            grouped[(str(root), f.name)].extend(recs)

    for (root, name), recs in sorted(grouped.items()):
        if len(recs) >= FORM_A_MIN_RECORDS:
            try:
                label = f"{Path(root).relative_to(REPO)}/**/{name}"
            except ValueError:
                label = f"{root}/**/{name}"
            findings.extend(_scan_population(label, recs))
    return findings


def _scan_population(label: str, recs: list[dict]) -> list[dict]:
    total = len(recs)
    present: dict[str, int] = defaultdict(int)
    values: dict[str, set] = defaultdict(set)
    for r in recs:
        for k, v in r.items():
            present[k] += 1
            if len(values[k]) <= 2:
                try:
                    values[k].add(json.dumps(v, sort_keys=True))
                except (TypeError, ValueError):
                    values[k].add(repr(v))
    out = []
    for k, cnt in sorted(present.items()):
        if cnt != total or len(values[k]) != 1:
            continue
        only = next(iter(values[k]))
        if only in ("null", '""', "[]", "{}"):
            continue  # vacio en todos lados es otra clase de problema
        out.append(
            {
                "form": "A",
                "population": label,
                "field": k,
                "records": total,
                "distinct_values": 1,
                "only_value": only[:80],
            }
        )
    return out


# Un id referencia un path si contiene una barra. Exigir extension deja pasar
# justo los casos rotos: `scripts/cos-doctor-preserve` (el archivo real es
# `.sh`) y `scripts/cos_primitive_harvester` (el real es `.py`) son entradas
# colgantes que un filtro por extension nunca ve.
PATHY = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_.-]+$")


def form_b_dangling(manifests: list[Path]) -> list[dict]:
    """Entradas de manifiesto cuyo path referenciado no existe en disco.

    Resuelve symlinks: este repo proyecta hooks/ -> packages/*/hooks/ y una
    verificacion ingenua reporta falsos 'no existe'.
    """
    findings: list[dict] = []
    for man in manifests:
        if not man.exists():
            continue
        rel = str(man.relative_to(REPO))
        text = man.read_text(encoding="utf-8", errors="replace")
        seen: set[str] = set()
        for lineno, line in enumerate(text.splitlines(), 1):
            m = re.match(r"\s*-?\s*id:\s*[\"']?([^\"'\s#]+)[\"']?\s*$", line)
            if not m:
                continue
            ref = m.group(1)
            if not PATHY.match(ref) or ref in seen:
                continue
            seen.add(ref)
            target = REPO / ref
            # os.path.exists sigue symlinks; lexists los ve rotos.
            if not os.path.exists(target):
                findings.append(
                    {
                        "form": "B",
                        "manifest": rel,
                        "line": lineno,
                        "ref": ref,
                        "symlink_broken": os.path.lexists(target),
                    }
                )
    return findings


ASSIGN = re.compile(r"^\s*(?:local\s+|readonly\s+|export\s+|declare\s+-\w+\s+)?"
                    r"([A-Za-z_][A-Za-z0-9_]*)=")
SHELL_SPECIAL = {"IFS", "PATH", "PS1", "PS4", "LC_ALL", "LANG", "TMPDIR",
                 "HOME", "SHELL", "PWD", "OLDPWD", "REPLY", "TZ"}


def form_c_write_only_vars(roots: list[Path]) -> list[dict]:
    """Variables de shell asignadas y nunca leidas.

    El alcance de lectura NO es uniforme, y tratarlo como uniforme fabrica
    falsos positivos: `hooks/_lib/tool-outcome.sh` asigna TOOL_EXIT_CODE para
    que lo lea quien la sourcea (`hooks/error-learning.sh:24`). Por eso:

      - MAYUSCULAS  -> lectura buscada en TODO el repo (convencion de shell
        para variable exportada o de contrato entre libreria y consumidor).
      - minusculas  -> lectura buscada solo en el mismo archivo (variable
        local por convencion).
    """
    findings: list[dict] = []
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(_iter_files(root, (".sh",)))
        elif root.is_file():
            files.append(root)

    # Universo de lectura para variables de contrato (MAYUSCULAS).
    universe_files = _iter_files(REPO / "hooks", (".sh",)) + \
        _iter_files(REPO / "scripts", (".sh",)) + \
        _iter_files(REPO / "packages", (".sh",))
    universe = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in dict.fromkeys(p.resolve() for p in universe_files)
    )

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(f.resolve().relative_to(REPO)) if str(f.resolve()).startswith(
            str(REPO)) else str(f)
        assigns: dict[str, int] = {}
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            m = ASSIGN.match(line)
            if m:
                name = m.group(1)
                if name in SHELL_SPECIAL or name.startswith("COS_ALLOW"):
                    continue
                assigns.setdefault(name, lineno)
        for name, lineno in sorted(assigns.items(), key=lambda kv: kv[1]):
            haystack = universe if name.isupper() else text
            scope = "repo" if name.isupper() else "file"
            # lectura = $NAME, ${NAME...}, "$NAME"; tambien export/unset/${!x}
            reads = re.findall(r"\$\{?!?" + re.escape(name) + r"\b", haystack)
            byname = re.findall(
                r"\b(?:export|unset|readonly)\s+" + re.escape(name) + r"\b",
                haystack)
            quoted = re.findall(r"[\"'`]" + re.escape(name) + r"[\"'`]", haystack)
            if reads or byname or quoted:
                continue
            findings.append(
                {
                    "form": "C",
                    "file": rel,
                    "line": lineno,
                    "var": name,
                    "read_scope": scope,
                    "assignments": sum(
                        1 for ln in text.splitlines()
                        if (mm := ASSIGN.match(ln)) and mm.group(1) == name
                    ),
                }
            )
    return findings


DEFAULT_A_ROOTS = ["templates", "manifests", ".claude"]
DEFAULT_B_MANIFESTS = [
    "manifests/primitive-lifecycle.yaml",
    "manifests/hook-vitality-budget.yaml",
]
DEFAULT_C_ROOTS = ["scripts/_lib", "hooks/_lib"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--form", choices=["A", "B", "C"], action="append",
                    help="limitar a una forma (repetible)")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--path", action="append", default=[],
                    help="raiz extra a escanear (formas A y C)")
    args = ap.parse_args(argv)
    forms = set(args.form or ["A", "B", "C"])

    try:
        findings: list[dict] = []
        if "A" in forms:
            roots = [REPO / p for p in DEFAULT_A_ROOTS] + [
                Path(p) for p in args.path]
            findings += form_a_single_valued([r for r in roots if r.exists()])
        if "B" in forms:
            findings += form_b_dangling([REPO / p for p in DEFAULT_B_MANIFESTS])
        if "C" in forms:
            roots = [REPO / p for p in DEFAULT_C_ROOTS] + [
                Path(p) for p in args.path]
            findings += form_c_write_only_vars([r for r in roots if r.exists()])
    except Exception as exc:  # noqa: BLE001 - exit 2 contractual
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"findings": findings,
                          "counts": {f: sum(1 for x in findings if x["form"] == f)
                                     for f in sorted(forms)}}, indent=2))
    else:
        counts: dict[str, int] = defaultdict(int)
        for f in findings:
            counts[f["form"]] += 1
        names = {"A": "campo-de-un-solo-valor",
                 "B": "referencia-colgante",
                 "C": "variable-escrita-nunca-leida"}
        for form in sorted(forms):
            print(f"[{form}] {names[form]}: {counts[form]}")
        for f in findings:
            if f["form"] == "A":
                print(f"  A {f['population']}  campo '{f['field']}' "
                      f"= {f['only_value']} en los {f['records']} registros")
            elif f["form"] == "B":
                print(f"  B {f['manifest']}:{f['line']}  ref inexistente: {f['ref']}")
            else:
                print(f"  C {f['file']}:{f['line']}  ${f['var']} asignada "
                      f"{f['assignments']}x, leida 0x")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
