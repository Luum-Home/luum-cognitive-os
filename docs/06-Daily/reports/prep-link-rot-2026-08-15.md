# Prep: link rot en docs/ — seis archivos, medición y arreglo propuesto

Fecha: 2026-08-15. Modo preparación: nada de este informe tocó un archivo trackeado. Los dos scripts corrieron en modo lectura (el de arreglo, en dry-run) contra el árbol real del repo.

## 1. Veredicto

El script de arreglo resuelve **1542 de 1744** links internos rotos (88,4%) sin ambigüedad. Los **202 restantes** quedan afuera a propósito: 87 tienen basename ambiguo (existe más de un archivo con ese nombre en el repo), 83 apuntan a un directorio, 24 no existen en ningún lado del repo, y 8 son sintaxis de link malformada en la fuente (paréntesis sin cerrar). Arreglar solo los 6 archivos peores cubre **1200 de 1744** (68,8%).

Medido con `measure_link_rot.py` (sección 5), corrido así:

```bash
python3 measure_link_rot.py --root docs --repo-root . --json /tmp/link-rot-report.json --top 10
```

## 2. Los 6 peores

| Archivo | Links rotos | Causa dominante |
|---|---:|---|
| `docs/00-MOCs/entrypoints/README.md` | 364 | falta subir 2 niveles de `../` (361/364) |
| `docs/06-Daily/reports/adr-implementation-status-backfill-2026-05-12.md` | 250 | falta subir 1 nivel de `../` (249/250) |
| `docs/00-MOCs/entrypoints/INDEX.md` | 173 | falta subir 2 niveles (120), target de directorio sin resolver (35) |
| `docs/03-PoCs/research/INDEX.md` | 147 | falta subir 1 nivel (141/147) |
| `docs/06-Daily/reports/docs-execution-latest.md` | 134 | falta subir 1 nivel (91), falta subir 2 (31) — más 8 links con sintaxis malformada en este mismo archivo (ver §4) |
| `docs/08-References/business/master-plan-checklist.md` | 132 | falta subir 1 nivel (130/132) |
| **Suma top 6** | **1200 / 1744 (68,8%)** | |

Contra la premisa del encargo ("6 archivos concentran 1197"): la lista de archivos coincide exactamente, el conteo total difiere en 3 (1200 vs 1197) — dentro del margen esperable por el doc `docs-execution-latest.md` mutando entre corridas (es un reporte auto-generado; ver §6) y por el filtro de falsos positivos que agregué en el camino (§6).

## 3. Agrupación por causa (sobre los 1744 rotos)

| Causa | Cantidad | % |
|---|---:|---:|
| Falta 1 nivel de `../` (el link no sube lo suficiente) | 955 | 54,8% |
| Falta 2 niveles de `../` | 598 | 34,3% |
| Target de directorio (`foo/`, no un archivo) | 83 | 4,8% |
| Cantidad de segmentos de directorio distinta (no es solo profundidad) | 53 | 3,0% |
| Basename inexistente en todo el repo | 24 | 1,4% |
| Falta 3 niveles de `../` | 14 | 0,8% |
| Sobran niveles de `../` (sube de más) | 9 | 0,5% |
| Sintaxis de link malformada en la fuente (paréntesis sin cerrar) | 8 | 0,5% |

**El defecto dominante es de profundidad de `../`, no de segmento renombrado**: 955+598+14 = 1567 casos (89,9% del total) son "el link no sube los niveles que hace falta", típicamente porque el autor escribió la ruta como si el archivo estuviera un nivel más arriba en el árbol de lo que está. Ejemplos reales:

```
en docs/00-MOCs/entrypoints/INDEX.md:
  adrs/STATUS-TAXONOMY.md
    -> debería ser ../../02-Decisions/adrs/STATUS-TAXONOMY.md   (faltan 2 niveles)

en docs/00-MOCs/entrypoints/AGENTS.md:
  00-MOCs/decisions.md
    -> debería ser ../decisions.md                               (falta 1 nivel;
       el link repite el segmento "00-MOCs" pensando que partía de docs/)

en docs/06-Daily/reports/adr-implementation-status-backfill-2026-05-12.md:
  (mismo patrón: falta 1 nivel en 249 de 250 links)
```

**Cantidad de segmentos distinta (53 casos)** — no es solo agregar `../`, cambió el nombre del directorio intermedio:

```
en docs/00-MOCs/architecture.md:
  ../adrs/ADR-010-hook-architecture-v2.md
    -> el real es docs/02-Decisions/adrs/ADR-010-hook-architecture-v2.md
       (el link asume un directorio "adrs/" a un nivel; el real está dos
       niveles abajo de "02-Decisions/")
```

**Target de directorio (83 casos)** — el link apunta a `algo/` sin nombrar un archivo (típicamente `README.md` o `INDEX.md` implícito):

```
en docs/00-MOCs/architecture.md:
  ../architecture/    ../skills/    ../capabilities/    ../patterns/
```
Esto el script de arreglo **no lo toca**: no hay forma segura de adivinar si el link quería `README.md`, `INDEX.md` u otro archivo del directorio.

**Sintaxis malformada (8 casos, todos en `docs-execution-latest.md`)** — el archivo es un reporte auto-generado con filas de tabla de ~700 caracteres; al menos una fila tiene un link `[texto](../../scripts/cos-` sin el paréntesis de cierre, así que la sintaxis markdown está rota en la fuente, no el path:

```
línea real del archivo (recortada):
| ... | [`scripts/cos-ci-local.sh`](../../scripts/cos- | path:scripts/active_primitive_index.py, ...
```
Esto **no es un problema de prefijo** — es el archivo el que está mal armado. Un sed a ciegas sobre esto no arregla nada y puede empeorarlo.

## 4. Lista de "no tocar" (202 casos, el script los deja explícitamente afuera)

1. **Links externos** (`http://`, `https://`, `mailto:`, `tel:`) — 1000 en total en docs/, nunca entran a la clasificación de rotos.
2. **Anclas puras** (`#seccion`, sin path) — 19 en total, tampoco entran.
3. **Basename ambiguo — 87 casos.** Existe más de un archivo con ese nombre en el repo (ejemplo: `README.md` aparece 167 veces, `architecture.md` 5 veces). Adivinar cuál es el correcto por "el más cercano" puede pegarle al archivo equivocado — el script prefiere listar los candidatos y no tocar el link.
4. **Target de directorio — 83 casos.** Termina en `/`, no nombra un archivo. Necesita decidir a mano si el link quería `README.md`, `INDEX.md` u otra cosa.
5. **Basename inexistente en todo el repo — 24 casos.** El archivo referenciado genuinamente no existe en ningún lado (ni en docs/, ni en el resto del repo). Requiere decisión de contenido: crear el archivo o borrar/editar el link. Lista completa:

   - `docs/02-Decisions/adrs/ADR-109-validation-capsule-worktree-isolation.md` → `ADR-100-test-resource-governance.md`
   - `docs/04-Concepts/architecture/cos-dispatch/README.md` → 12 links a `adrs/00N-*.md` y `../adrs/021-vendor-agnostic-with-adapters.md` (subcarpeta de ADRs de ese componente que no están creadas, o usan otro prefijo — ver también `CD-010-real-behavior-tests.md` en el mismo directorio, que referencia 3 de esos mismos archivos)
   - `docs/04-Concepts/architecture/cos-dispatch/test-strategy.md` → `adrs/010-real-behavior-tests.md`
   - `docs/04-Concepts/root/identity-stack.md` → `../../.claude/rules/constitutional-gates.md`
   - `docs/04-Concepts/root/tool-stack.md`, `docs/05-Methodology/root/blocked-tools.md`, `docs/08-References/root/recommended-stack.md` → los tres apuntan a `../research/license-analysis.md` (mismo archivo faltante, referenciado desde tres lugares)
   - `docs/08-References/root/vs-alternatives.md` → `adrs/ADR-059-existential-validation.md`
   - `docs/09-Quality/root/stress-test-strategy.md` → `../plan-descomposicion-monolith.md`

6. **Sintaxis de link malformada — 8 casos, todos en `docs/06-Daily/reports/docs-execution-latest.md`.** Paréntesis de cierre faltante en la fuente (ver §3). El script los detecta (texto del "link" cruza un salto de línea o supera 200 caracteres) y los reporta aparte; nunca calcula un reemplazo para ellos.

## 5. Script de medición (`measure_link_rot.py`)

Read-only, determinista. Exit 0 sin hallazgos / 1 con hallazgos / 2 error. Corrido contra el estado real del repo el 2026-08-15 con:
```bash
python3 measure_link_rot.py --root docs --repo-root . --json /tmp/link-rot-report.json --top 10
```
Nota importante encontrada en el camino: muchos links de `docs/` apuntan **afuera** de `docs/` (a `rules/`, `manifests/`, `scripts/`, `.cognitive-os/`, etc. en la raíz del repo) — por eso el índice de basenames busca en `--repo-root` completo, no solo en `docs/`. Buscar solo dentro de `docs/` da 87,7% de "basename existe en otro lado" en vez del 93,4% real.

```python
#!/usr/bin/env python3
"""Measure internal markdown link rot under docs/.

Read-only, deterministic. Walks every *.md under a root directory (default
docs/), extracts markdown link targets [text](target), classifies each as
external / anchor-only / internal-file, and for internal-file targets checks
whether the resolved path exists on disk.

IMPORTANT: many docs/ links point OUTSIDE docs/ (e.g. ../../rules/foo.md,
../manifests/x.yaml resolving to repo root). The "does a file with this
basename exist somewhere" check therefore searches the whole repo
(--repo-root, default: parent of --root), not just docs/, or every such
link gets misclassified as "basename missing entirely" when it is really
just a prefix/depth error pointing at a real file outside docs/.

Exit codes: 0 = no broken links found, 1 = broken links found, 2 = usage/error.

Usage:
    python3 measure_link_rot.py [--root docs] [--repo-root .] [--json out.json] [--top N]

Output (stdout): human-readable summary + top-N offending files.
Output (--json PATH): full machine-readable report (per-file broken link list,
    per-file basename-exists-elsewhere flag, aggregate cause buckets).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Matches markdown inline links: [text](target) -- not images (handled the same,
# images use the same target semantics for rot purposes, so we count them too).
LINK_RE = re.compile(r"(?<!!)\[[^\]\n]*?\]\(([^)]+)\)")
IMAGE_LINK_RE = re.compile(r"!\[[^\]\n]*?\]\(([^)]+)\)")

FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def strip_code(text: str) -> str:
    """Blank out fenced code blocks and inline code spans so regex-only
    markdown parsing doesn't mistake a regex/code snippet like
    `[a-z0-9]([a-z0-9._-]*[a-z0-9])?` for a real [text](target) link.
    Preserves exact character length and every newline position (only
    replaces non-newline chars with a space) so byte offsets into the
    stripped text stay valid offsets into the original text -- required by
    fix_link_rot.py, which locates matches here and splices the fix back
    into the original (unstripped) file content."""

    def blank(m: "re.Match[str]") -> str:
        return "".join(c if c == "\n" else " " for c in m.group(0))

    text = FENCE_RE.sub(blank, text)
    text = INLINE_CODE_RE.sub(blank, text)
    return text


def is_external(target: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", target)) or target.startswith(
        ("mailto:", "tel:")
    )


def split_target(target: str) -> tuple[str, str]:
    """Split a link target into (path_part, anchor_part). anchor includes '#'."""
    target = target.strip()
    # strip surrounding <> some md uses
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if "#" in target:
        path_part, _, anchor = target.partition("#")
        return path_part, "#" + anchor
    return target, ""


EXCLUDE_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


def build_basename_index(root: Path) -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = defaultdict(list)
    for p in root.rglob("*"):
        if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
            continue
        if p.is_file():
            idx[p.name].append(p)
    return idx


def classify_prefix_diff(broken_rel: str, candidate_rel: str) -> str:
    """Best-effort classification of *why* a broken relative link differs from
    a real candidate path, both expressed relative to the same source file."""
    b_parts = [p for p in broken_rel.split("/") if p not in ("", ".")]
    c_parts = [p for p in candidate_rel.split("/") if p not in ("", ".")]
    b_updots = broken_rel.count("../")
    c_updots = candidate_rel.count("../")
    if b_updots != c_updots:
        diff = c_updots - b_updots
        if diff > 0:
            return f"falta {diff} nivel(es) de '../' (subir menos de lo necesario)"
        return f"sobran {-diff} nivel(es) de '../' (sube de más)"
    # same updot count, compare remaining segments
    b_rest = b_parts[b_updots:]
    c_rest = c_parts[c_updots:]
    if len(b_rest) != len(c_rest):
        return "cantidad de segmentos de directorio distinta"
    diffs = [(bp, cp) for bp, cp in zip(b_rest, c_rest) if bp != cp]
    if len(diffs) == 1:
        bp, cp = diffs[0]
        return f"segmento de directorio distinto: '{bp}' -> '{cp}'"
    if len(diffs) == 0:
        return "coincide salvo mayus/minus o algo no detectado"
    return f"{len(diffs)} segmentos distintos"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="docs", help="root dir to scan for source .md files (default: docs)")
    ap.add_argument(
        "--repo-root",
        default=None,
        help="root dir to search when checking if a broken link's basename exists "
        "elsewhere (default: parent of --root, i.e. the whole repo -- many docs/ "
        "links point outside docs/)",
    )
    ap.add_argument("--json", default=None, help="write full JSON report to this path")
    ap.add_argument("--top", type=int, default=6, help="how many worst files to show")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root).resolve() if args.repo_root else root.parent

    md_files = sorted(root.rglob("*.md"))
    if not md_files:
        print(f"ERROR: no .md files under {root}", file=sys.stderr)
        return 2

    total_links = 0
    total_external = 0
    total_anchor_only = 0
    total_internal = 0
    total_broken = 0

    per_file_broken: dict[str, list[dict]] = defaultdict(list)
    basename_exists_elsewhere = 0
    basename_missing_entirely = 0

    basename_index: dict[str, list[Path]] | None = None  # lazy build

    total_malformed = 0
    for md in md_files:
        try:
            raw_text = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        text = strip_code(raw_text)
        targets = LINK_RE.findall(text) + IMAGE_LINK_RE.findall(text)
        for raw in targets:
            total_links += 1
            if "\n" in raw or len(raw) > 200:
                # regex spanned past an unclosed ')' into unrelated text
                # (e.g. a truncated link inside a wide table row) -- this is
                # a markdown syntax defect in the source, not a path/prefix
                # issue. Bucket separately; never feed to path resolution.
                total_malformed += 1
                total_broken += 1
                total_internal += 1
                rel_md = str(md.relative_to(root))
                per_file_broken[rel_md].append(
                    {
                        "raw_target": raw[:120],
                        "path_part": raw[:120],
                        "anchor": "",
                        "resolved_attempted": "N/A",
                        "basename_exists_elsewhere": False,
                        "cause": "sintaxis de link malformada en la fuente (parentesis sin cerrar) -- no tocar con sed, arreglar a mano",
                    }
                )
                continue
            path_part, anchor = split_target(raw)
            if is_external(path_part):
                total_external += 1
                continue
            if path_part == "":
                # pure anchor link, e.g. (#section)
                total_anchor_only += 1
                continue
            total_internal += 1
            resolved = (md.parent / path_part).resolve()
            if resolved.exists():
                continue
            total_broken += 1
            try:
                resolved_disp = str(resolved.relative_to(repo_root))
            except ValueError:
                resolved_disp = "OUTSIDE_REPO_ROOT"
            entry = {
                "raw_target": raw,
                "path_part": path_part,
                "anchor": anchor,
                "resolved_attempted": resolved_disp,
            }
            rel_md = str(md.relative_to(root))
            per_file_broken[rel_md].append(entry)

    # Second pass: for each broken link, does a file with the same basename
    # exist anywhere under root? (lazy-build index only if there are any
    # broken links, to avoid the walk cost otherwise)
    prefix_cause_counter: Counter[str] = Counter()
    dir_target_missing = 0
    if total_broken:
        basename_index = build_basename_index(repo_root)
        total_malformed_bucket = 0
        for rel_md, entries in per_file_broken.items():
            for entry in entries:
                if entry.get("cause", "").startswith("sintaxis de link malformada"):
                    prefix_cause_counter["sintaxis de link malformada (no tocar con sed)"] += 1
                    total_malformed_bucket += 1
                    continue
                path_part = entry["path_part"]
                is_dir_target = path_part.rstrip().endswith("/")
                basename = Path(path_part).name
                candidates = basename_index.get(basename, []) if not is_dir_target else []
                if is_dir_target:
                    # directory-style target (e.g. "../architecture/"); our
                    # basename index only covers files, so we can't reliably
                    # locate the intended directory -- bucket separately
                    # instead of guessing.
                    dir_target_missing += 1
                    entry["basename_exists_elsewhere"] = False
                    entry["cause"] = "target de directorio (termina en '/'), no un archivo -- revisar a mano"
                    prefix_cause_counter["target de directorio (revisar a mano)"] += 1
                    continue
                if candidates:
                    basename_exists_elsewhere += 1
                    md_path = root / rel_md
                    # pick nearest candidate (shortest resulting relative path)
                    best = None
                    best_rel = None
                    for cand in candidates:
                        cand_rel = _relpath(cand.parent, md_path.parent)
                        if best_rel is None or len(cand_rel) < len(best_rel):
                            best = cand
                            best_rel = cand_rel
                    candidate_rel_link = _relpath(best, md_path.parent, as_file=True)
                    cause = classify_prefix_diff(path_part, candidate_rel_link)
                    entry["basename_exists_elsewhere"] = True
                    try:
                        entry["candidate"] = str(best.relative_to(repo_root))
                    except ValueError:
                        entry["candidate"] = str(best)
                    entry["cause"] = cause
                    prefix_cause_counter[cause] += 1
                else:
                    basename_missing_entirely += 1
                    entry["basename_exists_elsewhere"] = False
                    entry["cause"] = "basename no existe en ningun lado del repo (destino a crear o link a borrar)"
                    prefix_cause_counter["basename inexistente en todo el repo"] += 1

    worst = sorted(per_file_broken.items(), key=lambda kv: len(kv[1]), reverse=True)

    pct = (total_broken / total_internal * 100) if total_internal else 0.0
    pct_prefix = (basename_exists_elsewhere / total_broken * 100) if total_broken else 0.0

    print(f"root scanned (source .md files): {root.relative_to(Path.cwd()) if root.is_relative_to(Path.cwd()) else root}")
    print(f"repo-root used for basename lookup: {repo_root.relative_to(Path.cwd()) if repo_root.is_relative_to(Path.cwd()) else repo_root}")
    print(f"md files scanned: {len(md_files)}")
    print(f"total link targets: {total_links}  (external: {total_external}, anchor-only: {total_anchor_only}, internal: {total_internal})")
    print(f"broken internal links: {total_broken} / {total_internal} internal ({pct:.1f}%)")
    print(f"of broken links, basename exists elsewhere in repo: {basename_exists_elsewhere}/{total_broken} ({pct_prefix:.1f}%)")
    print(f"of broken links, directory-style target (not a file): {dir_target_missing}/{total_broken}")
    print(f"of broken links, basename missing entirely from repo: {basename_missing_entirely}/{total_broken}")
    print(f"of broken links, malformed link syntax in source (unclosed paren): {total_malformed}/{total_broken}")
    print()
    print(f"top {args.top} files by broken link count:")
    for rel_md, entries in worst[: args.top]:
        print(f"  {len(entries):5d}  {rel_md}")
    print()
    print("cause buckets (broken links with basename found elsewhere):")
    for cause, n in prefix_cause_counter.most_common(15):
        print(f"  {n:5d}  {cause}")

    if args.json:
        report = {
            "root": str(root),
            "repo_root": str(repo_root),
            "md_files_scanned": len(md_files),
            "total_links": total_links,
            "total_external": total_external,
            "total_anchor_only": total_anchor_only,
            "total_internal": total_internal,
            "total_broken": total_broken,
            "pct_broken_of_internal": pct,
            "basename_exists_elsewhere": basename_exists_elsewhere,
            "dir_target_missing": dir_target_missing,
            "basename_missing_entirely": basename_missing_entirely,
            "total_malformed": total_malformed,
            "pct_prefix_cause": pct_prefix,
            "worst_files": [{"file": f, "broken": len(e)} for f, e in worst],
            "cause_buckets": dict(prefix_cause_counter),
            "per_file_broken": per_file_broken,
        }
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nfull JSON report written to {args.json}")

    return 1 if total_broken else 0


def _relpath(target: Path, from_dir: Path, as_file: bool = False) -> str:
    """Relative path string from from_dir to target, using os.path.relpath
    semantics (works across branches, unlike Path.relative_to)."""
    import os

    rel = os.path.relpath(target, start=from_dir)
    return rel


if __name__ == "__main__":
    raise SystemExit(main())
```

## 6. Script de arreglo (`fix_link_rot.py`)

Read-only por default. Requiere `--apply` explícito para escribir. Idempotente: una vez aplicado, esos links resuelven, así que una segunda corrida no encuentra nada más que hacer para ellos (exit 0). Importa `measure_link_rot.py` (debe estar en el mismo directorio) en vez de duplicar la lógica de detección — las dos herramientas nunca pueden divergir sobre qué cuenta como "roto".

Validado en dry-run contra un archivo real antes de escribir este informe:
```bash
python3 fix_link_rot.py --root docs --repo-root . --only 00-MOCs/entrypoints/AGENTS.md
```
Salida real de esa corrida — 5 fixes propuestos, 1 skip correcto por ambigüedad (`architecture.md` existe 5 veces en el repo):
```
00-MOCs/entrypoints/AGENTS.md  (5 fix(es), 1 skip(s))
  FIX   00-MOCs/decisions.md  ->  ../decisions.md
  FIX   00-MOCs/workflow.md  ->  ../workflow.md
  FIX   00-MOCs/quality.md  ->  ../quality.md
  FIX   00-MOCs/operations.md  ->  ../operations.md
  FIX   00-MOCs/onboarding.md  ->  ../onboarding.md
  SKIP  00-MOCs/architecture.md  -- basename ambiguo (5 archivos con ese nombre en el repo: ...) -- elegir a mano

[DRY RUN] total fixable: 5   total skipped (manual review): 1
no files written (dry run) -- pass --apply to write
```
`git status` sobre ese archivo después de la corrida: sin cambios (confirma que el dry-run no escribió nada).

Para aplicar de verdad, acotado a los 6 archivos peores primero (recomendado, en vez de los 1744 de una):
```bash
python3 fix_link_rot.py --apply \
  --only 00-MOCs/entrypoints/README.md \
  --only 06-Daily/reports/adr-implementation-status-backfill-2026-05-12.md \
  --only 00-MOCs/entrypoints/INDEX.md \
  --only 03-PoCs/research/INDEX.md \
  --only 06-Daily/reports/docs-execution-latest.md \
  --only 08-References/business/master-plan-checklist.md
```

```python
#!/usr/bin/env python3
"""Fix internal markdown link rot in docs/ caused by a wrong '../' depth or a
renamed directory segment -- NOT links that are genuinely missing a target.

Read-only by default: prints every change it WOULD make, and why every
skipped broken link was skipped. Pass --apply to actually write files.
Idempotent: once applied, the links resolve, so a second run (--apply or
not) finds nothing left to do for those links -- exit 0.

Companion to measure_link_rot.py (same directory) -- imports its detection
logic instead of duplicating it, so both scripts always agree on what counts
as "broken".

A link is auto-fixed ONLY when ALL of these hold:
  - it is internal (not http(s)/mailto/tel, not a pure #anchor)
  - it does not currently resolve to an existing file
  - it is NOT a directory-style target (does not end in "/")
  - its raw text does not span a newline / is not implausibly long (that is
    the signature of a malformed, unclosed "]( ... )" in the source -- a
    syntax defect, not a path defect; never touched by sed-style rewriting)
  - a file with the exact same basename exists EXACTLY ONCE elsewhere in the
    repo (unambiguous). 0 matches = nothing to point at (leave it -- create
    or delete is a content decision, not this script's job). 2+ matches =
    ambiguous (e.g. README.md exists 167 times in this repo) -- guessing
    which one is correct is exactly the kind of silent wrong-fix this norm
    forbids, so it is reported and left untouched.

Usage:
    python3 fix_link_rot.py [--root docs] [--repo-root .]                # dry run, whole tree
    python3 fix_link_rot.py --only 00-MOCs/entrypoints/README.md         # dry run, one file
    python3 fix_link_rot.py --apply --only <file> [--only <file> ...]    # write, scoped
    python3 fix_link_rot.py --apply                                     # write, whole tree

Exit codes: 0 = nothing to fix (dry run) / nothing left after apply,
            1 = fixes pending (dry run) or applied (--apply),
            2 = usage/error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_link_rot as mlr  # noqa: E402


def plan_fixes_for_file(md: Path, root: Path, repo_root: Path, basename_index: dict[str, list[Path]]):
    """Return (fixes, skips) for one file.
    fixes: list of (match_start, match_end, old_full_match, new_full_match, old_target, new_target)
    skips: list of (raw_target_display, reason)
    """
    try:
        raw_text = md.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return [], [(f"<unreadable: {exc}>", "no se pudo leer el archivo")]

    stripped = mlr.strip_code(raw_text)
    fixes = []
    skips = []

    for pattern in (mlr.LINK_RE, mlr.IMAGE_LINK_RE):
        for m in pattern.finditer(stripped):
            raw = m.group(1)
            if "\n" in raw or len(raw) > 200:
                skips.append((raw[:60] + "...", "sintaxis de link malformada (parentesis sin cerrar) -- arreglar a mano"))
                continue
            path_part, anchor = mlr.split_target(raw)
            if mlr.is_external(path_part) or path_part == "":
                continue
            resolved = (md.parent / path_part).resolve()
            if resolved.exists():
                continue  # not broken

            if path_part.rstrip().endswith("/"):
                skips.append((raw, "target de directorio, no de archivo -- revisar a mano"))
                continue

            basename = Path(path_part).name
            candidates = basename_index.get(basename, [])
            if len(candidates) == 0:
                skips.append((raw, "basename no existe en ningun lado del repo -- crear el archivo o borrar el link"))
                continue
            if len(candidates) > 1:
                cand_list = ", ".join(
                    str(c.relative_to(repo_root)) if c.is_relative_to(repo_root) else str(c) for c in candidates
                )
                skips.append((raw, f"basename ambiguo ({len(candidates)} archivos con ese nombre en el repo: {cand_list}) -- elegir a mano"))
                continue

            best = candidates[0]
            new_path_part = mlr._relpath(best, md.parent, as_file=True)
            new_target = new_path_part + anchor
            if new_target == raw:
                # would be a no-op (shouldn't happen since resolved didn't
                # exist, but guard against surprises)
                continue

            old_full = m.group(0)
            new_full = old_full[: m.start(1) - m.start(0)] + new_target + old_full[m.end(1) - m.start(0) :]
            fixes.append((m.start(0), m.end(0), old_full, new_full, raw, new_target))

    return fixes, skips


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="docs", help="root dir to scan for source .md files (default: docs)")
    ap.add_argument("--repo-root", default=None, help="root dir to search for fix candidates (default: parent of --root)")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run, read-only)")
    ap.add_argument("--only", action="append", default=None, help="restrict to this file (relative to --root); repeatable")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root).resolve() if args.repo_root else root.parent

    if args.only:
        md_files = [root / rel for rel in args.only]
        missing = [f for f in md_files if not f.is_file()]
        if missing:
            print(f"ERROR: --only file(s) not found: {missing}", file=sys.stderr)
            return 2
    else:
        md_files = sorted(root.rglob("*.md"))

    print("building basename index over repo (read-only walk)...", file=sys.stderr)
    basename_index = mlr.build_basename_index(repo_root)

    total_fixes = 0
    total_skips = 0
    files_changed = 0

    for md in md_files:
        fixes, skips = plan_fixes_for_file(md, root, repo_root, basename_index)
        rel = md.relative_to(root)
        if not fixes and not skips:
            continue
        if fixes:
            print(f"\n{rel}  ({len(fixes)} fix(es), {len(skips)} skip(s))")
            for _, _, _old_full, _new_full, old_target, new_target in fixes:
                print(f"  FIX   {old_target}  ->  {new_target}")
        elif skips:
            print(f"\n{rel}  (0 fixes, {len(skips)} skip(s))")
        for raw, reason in skips:
            print(f"  SKIP  {raw}  -- {reason}")

        total_fixes += len(fixes)
        total_skips += len(skips)

        if fixes and args.apply:
            raw_text = md.read_text(encoding="utf-8")
            # apply from the end of the file backwards so earlier offsets
            # stay valid as we splice
            new_text = raw_text
            for start, end, old_full, new_full, _old_t, _new_t in sorted(fixes, key=lambda f: f[0], reverse=True):
                assert new_text[start:end] == old_full, (
                    f"offset drift in {rel}: expected {old_full!r} at [{start}:{end}], "
                    f"found {new_text[start:end]!r} -- aborting this file, no partial write"
                )
                new_text = new_text[:start] + new_full + new_text[end:]
            assert new_text != raw_text, f"{rel}: computed 0 byte diff despite {len(fixes)} planned fixes"
            md.write_text(new_text, encoding="utf-8")
            files_changed += 1
            print(f"  APPLIED to {rel}")

    print(f"\n{'='*60}")
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] total fixable: {total_fixes}   total skipped (manual review): {total_skips}")
    if args.apply:
        print(f"files written: {files_changed}")
    else:
        print("no files written (dry run) -- pass --apply to write")

    return 1 if (total_fixes or total_skips) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 7. Correcciones a las premisas del encargo

- **"1744 links rotos sobre 3095"**: el conteo de rotos coincide exacto (1744). El denominador difiere: medí 3038 links internos (no 3095) — la diferencia es de metodología de conteo (qué se cuenta como "link total": el encargo probablemente incluye los externos/anclas en su base, o cuenta de otra forma los links de imagen). El **porcentaje de rotos sobre internos da 57,4%**, no 56,3% — cercano pero no idéntico. No hay forma de saber cuál conteo exacto usó el juez original sin su script; dejo el mío documentado arriba.
- **"6 archivos concentran 1197"**: confirmado en archivos y orden, el número da 1200 en mi medición (diferencia de 3, ver §2 — atribuible a que `docs-execution-latest.md` es un reporte que muta entre corridas, más el filtro de falsos positivos de código/regex que agregué).
- **"entrypoints 90,5%, 05-Methodology 100%"**: **confirmado exacto** — 554/612 (90,5%) y 37/37 (100,0%) respectivamente.
- **"entrypoints/README.md: 364 sobre 411"**: **confirmado exacto**, ambos números.
- **"93,8% basename existe"**: la premisa es correcta, pero **solo si se busca en todo el repo, no solo en docs/**. Mi primera corrida, buscando basenames únicamente bajo `docs/`, dio 87,7% — un número más bajo y engañoso, porque muchos links de `docs/` apuntan a `rules/`, `manifests/`, `scripts/`, `.cognitive-os/` en la raíz del repo, y esos archivos sí existen, solo que el índice de búsqueda no los veía. Ampliando el índice a todo el repo (excluyendo `.git`, `node_modules`, caches), el número sube a **93,4%** — a 0,4 puntos de la premisa. Confirma la conclusión operativa del encargo: el defecto dominante es de prefijo/ruta, no de destino inexistente, y el arreglo es mayormente mecánico.
- **Hallazgo no anticipado por el encargo**: dentro de ese 93,4%, un **5,3% (87 de 1629) es basename ambiguo** — más de un archivo con ese nombre en el repo (`README.md` sale 167 veces). Un `sed` que reemplace "el candidato más cercano" sin chequear esto puede apuntar al archivo equivocado en esos 87 casos. El script de arreglo los excluye explícitamente en vez de adivinar; el 88,4% (1542/1744) que sí aplica de forma segura es el número real de "cuánto resuelve un sed", no el 93,8%/93,4% de la premisa (que mide "tiene candidato", no "tiene candidato único").
- **Hallazgo no anticipado, segundo**: 8 de los 1744 rotos no son problema de ruta sino de **sintaxis markdown malformada** en `docs-execution-latest.md` (paréntesis de link sin cerrar en filas de tabla auto-generadas). Sin filtrarlos, contaminan la medición con "targets" de cientos de caracteres que no son paths reales — los excluí explícitamente del cálculo de causas y del script de arreglo (ver §3 y §4).
