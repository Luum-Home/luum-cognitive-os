#!/usr/bin/env python3
# SCOPE: both
"""¿Dónde vive X? — la pregunta que un `ls` contesta mal.

Origen: 2026-08-20. Un agente reportó que `metrics-rotation.sh` no existía. La
orquestación lo "verificó" con `ls scripts/metrics-rotation.sh`, no lo encontró,
y confirmó la ausencia. La realidad era:

    hooks/metrics-rotation.sh -> ../packages/context-optimization/hooks/metrics-rotation.sh

Dos confirmaciones independientes de una ausencia falsa, y ninguna de las dos
fue un descuido: `ls <un-path>` no contesta "¿existe X?", contesta "¿existe X
**ahí**?". La diferencia sólo se nota cuando el mismo artefacto puede vivir en
`hooks/`, `scripts/`, `packages/*/hooks/`, `packages/*/scripts/`, `cos_lib/` —
y cuando varios `cos_lib/*.py` y tres directorios enteros (`harness_adapter`,
`event_projections`, `providers`) son symlinks a `packages/*/lib/`.

Este script contesta la pregunta completa: barre el árbol siguiendo symlinks,
deduplica por destino real, y además mira el PATH por si "X" era un binario.
Read-only, determinista, sin estado de sesión.

Exit codes (convención de evidencia ejecutable):
    0  encontrado (al menos una ubicación)
    1  no encontrado en ninguna de las ubicaciones barridas
    2  error de uso

Uso:
    python3 scripts/locate_primitive.py metrics-rotation.sh
    python3 scripts/locate_primitive.py harness_adapter --json
    python3 scripts/locate_primitive.py 'metrics-*.sh' --glob
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
from pathlib import Path

# Directorios que no son código del repo. Se podan enteros: barrerlos cuesta
# segundos y no contesta la pregunta.
PRUNE = frozenset(
    {
        ".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", "target", "dist", "build", ".next",
        "site-packages", ".tox", "coverage", ".idea",
    }
)

# `.cognitive-os/` estuvo en PRUNE durante la primera versión de este script, y
# el primer censo que lo usó reportó `hook-timing.jsonl` y
# `agent-verification.jsonl` como ausentes: existen, pesan 7 MB, y se
# escribieron hoy. El instrumento contra la ausencia falsa cometió una ausencia
# falsa, por la misma causa de siempre — barrer menos árbol del que dice la
# conclusión. Podar el estado de runtime es exactamente podar lo que más se
# pregunta. Los 11k archivos que agrega cuestan décimas de segundo.


def repo_root(start: Path | None = None) -> Path:
    """Raíz del repo por presencia de `.git`, con el cwd como último recurso."""
    cur = (start or Path.cwd()).resolve()
    for cand in (cur, *cur.parents):
        if (cand / ".git").exists():
            return cand
    return cur


def _matches(name: str, needle: str, use_glob: bool, exact: bool) -> bool:
    if use_glob:
        return fnmatch.fnmatch(name, needle)
    if exact:
        return name == needle
    return name == needle or needle in name


def sweep(root: Path, needle: str, *, use_glob: bool = False, exact: bool = False) -> list[dict]:
    """Barrido del árbol que NO confunde 'no está acá' con 'no está'.

    Devuelve una entrada por ubicación encontrada, con:
      path      ruta relativa a la raíz tal como se la nombra
      real      destino tras resolver symlinks (absoluto)
      symlink   si la ruta encontrada es un enlace
      broken    symlink cuyo destino no existe (ausencia REAL, y de las caras)
      kind      file | dir
    """
    hits: list[dict] = []
    seen: set[tuple[str, str]] = set()
    # followlinks=False a propósito: los symlinks se detectan como entradas y se
    # resuelven con realpath. Seguirlos al caminar duplicaría subárboles enteros
    # (cos_lib/harness_adapter -> packages/.../lib/harness_adapter) y podría
    # ciclar.
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        here = Path(dirpath)
        for name in (*dirnames, *filenames):
            if not _matches(name, needle, use_glob, exact):
                continue
            p = here / name
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:  # pragma: no cover - p siempre cuelga de root
                rel = str(p)
            real = os.path.realpath(p)
            key = (rel, real)
            if key in seen:
                continue
            seen.add(key)
            is_link = p.is_symlink()
            hits.append(
                {
                    "path": rel,
                    "real": real,
                    "symlink": is_link,
                    "broken": is_link and not p.exists(),
                    "kind": "dir" if p.is_dir() else "file",
                }
            )
    hits.sort(key=lambda h: (h["path"].count("/"), h["path"]))
    return hits


def locate(needle: str, *, root: Path | None = None, use_glob: bool = False,
           exact: bool = False, check_path: bool = True) -> dict:
    root = root or repo_root()
    hits = sweep(root, needle, use_glob=use_glob, exact=exact)
    on_path = shutil.which(needle) if (check_path and not use_glob) else None
    distinct = {h["real"] for h in hits}
    return {
        "query": needle,
        "root": str(root),
        "found": bool(hits) or bool(on_path),
        "hits": hits,
        "distinct_targets": sorted(distinct),
        "on_path": on_path,
        "how": f"python3 scripts/locate_primitive.py {needle}",
    }


def render(result: dict) -> str:
    if not result["found"]:
        return (
            f"NO ENCONTRADO: {result['query']}\n"
            f"  barrido: {result['root']} (symlinks resueltos, {len(PRUNE)} dirs podados)\n"
            f"  PATH: sin coincidencias\n"
        )
    lines = [f"ENCONTRADO: {result['query']}"]
    for h in result["hits"]:
        mark = ""
        if h["broken"]:
            mark = "  [SYMLINK ROTO]"
        elif h["symlink"]:
            mark = f"  -> {h['real']}"
        lines.append(f"  {h['kind']:4}  {h['path']}{mark}")
    if result["on_path"]:
        lines.append(f"  PATH  {result['on_path']}")
    n_loc = len(result["hits"])
    n_real = len(result["distinct_targets"])
    if n_loc > n_real:
        lines.append(f"  ({n_loc} rutas, {n_real} artefacto(s) real(es): hay symlinks)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Contesta '¿dónde vive X?' barriendo el repo y siguiendo symlinks.",
    )
    ap.add_argument("name", help="basename, fragmento, o patrón con --glob")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--glob", action="store_true", help="tratar el nombre como patrón fnmatch")
    ap.add_argument("--exact", action="store_true", help="sólo basename idéntico")
    ap.add_argument("--root", default=None, help="raíz del barrido (default: raíz del repo)")
    ap.add_argument("--no-path", action="store_true", help="no consultar $PATH")
    args = ap.parse_args(argv)

    if not args.name.strip():
        print("error: nombre vacío", file=sys.stderr)
        return 2
    root = Path(args.root).resolve() if args.root else None
    if root is not None and not root.is_dir():
        print(f"error: raíz inexistente: {root}", file=sys.stderr)
        return 2

    result = locate(
        args.name, root=root, use_glob=args.glob, exact=args.exact,
        check_path=not args.no_path,
    )
    sys.stdout.write(json.dumps(result, indent=2) + "\n" if args.json else render(result))
    return 0 if result["found"] else 1


if __name__ == "__main__":
    sys.exit(main())
