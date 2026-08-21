#!/usr/bin/env python3
# SCOPE: both
"""Censo de skips condicionales: cuáles declaran una dependencia opcional y
cuáles son un test que no existe.

Un `pytest.skip("X not found")` es una afirmación de ausencia con formato de
test verde: no pasa ni falla, y una suite llena de esos *se ve* verde. Es la
misma familia que "no hay" contra "no pude", en forma de test.

Un skip que nunca se dispara es CORRECTO: declara una dependencia opcional que
en esta máquina está presente. Un skip que se dispara SIEMPRE es un test que no
existe. Y el peor caso es el skip que se dispara porque busca el artefacto en el
lugar equivocado — la ausencia falsa, cometida por el propio test.

Este censo NO corre la suite. Clasifica estáticamente la condición de cada skip
y, para las condiciones que nombran una ruta literal, resuelve si el artefacto
existe: como está escrito, en otra ubicación (symlinks incluidos, vía
`scripts/locate_primitive.py`), o en ninguna. Lo que no puede resolver
estáticamente lo declara ciego, no lo cuenta como cero.

Exit codes: 0 sin hallazgos · 1 hay skips por ruta equivocada o ausencia real · 2 error.

Uso:
    python3 scripts/skip_absence_census.py
    python3 scripts/skip_absence_census.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locate_primitive import locate, repo_root  # noqa: E402

TEST_GLOBS = ("tests/**/*.py", "packages/*/tests/**/*.py")

# Orden de clasificación: el primero que matchea gana. Deliberadamente
# plataforma y dependencia opcional van ANTES que artefacto, porque un
# `shutil.which("docker")` bajo un guard de plataforma es plataforma.
PATTERNS: tuple[tuple[str, str], ...] = (
    ("plataforma", r"sys\.platform|platform\.system|platform\.machine|os\.name\b|IS_(MACOS|LINUX|WINDOWS)|darwin|win32"),
    ("dep_opcional", r"importorskip|find_spec|ImportError|ModuleNotFound|HAS_[A-Z_]+|_AVAILABLE\b|_INSTALLED\b"),
    ("entorno", r"os\.environ|getenv|environ\.get|\bCI\b|COS_[A-Z_]+"),
    ("servicio", r"socket\.|requests\.|urlopen|connect\(|ping\(|is_running|docker\b|valkey|redis|mlflow"),
    ("artefacto", r"\.exists\(\)|os\.path\.exists|os\.path\.is(file|dir)|\.is_file\(\)|\.is_dir\(\)|shutil\.which|\.glob\(|list\(.*glob"),
)

# Rutas literales dentro de la condición. Sólo literales: una ruta armada por
# concatenación no es resoluble estáticamente y va a ciegos.
_SUFFIXES = "py|sh|bash|yaml|yml|json|md|jsonl|toml|go|ts|txt|lock|bats"
PATHLIKE = re.compile(rf"""["']([A-Za-z0-9_./-]+\.(?:{_SUFFIXES}))["']""")
# La razón del skip suele nombrar el artefacto en prosa ("session-init.sh not
# found"): ahí no hay comillas pegadas, y exigirlas fue la primera versión de
# este censo declarando 333 ciegos que no lo eran.
BARELIKE = re.compile(rf"""\b([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:{_SUFFIXES}))\b""")
BINLIKE = re.compile(r"""shutil\.which\(\s*["']([A-Za-z0-9_.-]+)["']""")
ABSENCE_WORDS = re.compile(
    r"not found|not present|missing|does not exist|doesn't exist|no existe|"
    r"not installed|unavailable|no such|not available",
    re.IGNORECASE,
)


def classify(cond_src: str) -> str:
    for label, pat in PATTERNS:
        if re.search(pat, cond_src, re.IGNORECASE):
            return label
    return "otra"


def expand(cond_src: str, assigns: dict[str, str], depth: int = 2) -> str:
    """Sustituye nombres por su valor asignado, hasta `depth` niveles."""
    out = cond_src
    seen: set[str] = set()
    for _ in range(depth):
        names = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", out)) - seen
        added = [assigns[n] for n in sorted(names) if n in assigns and assigns[n] != out]
        if not added:
            break
        seen |= names
        out = out + " || " + " || ".join(added)
    return out


def _src(node: ast.AST, lines: list[str]) -> str:
    try:
        seg = ast.get_source_segment("\n".join(lines), node)
    except Exception:  # pragma: no cover
        seg = None
    return (seg or "").strip()


def _is_pytest_attr(node: ast.AST, *names: str) -> bool:
    """`pytest.skip`, `pytest.mark.skipif`, o el nombre suelto importado."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    dotted = ".".join(reversed(parts))
    return any(dotted == n or dotted.endswith("." + n) for n in names)


def collect(root: Path) -> list[dict]:
    """Una entrada por sitio de skip. Población = todos los sitios de skip."""
    entries: list[dict] = []
    files: list[Path] = []
    for g in TEST_GLOBS:
        files.extend(sorted(root.glob(g)))
    for f in files:
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except SyntaxError:
            entries.append({"file": str(f.relative_to(root)), "line": 0,
                            "kind": "no_parseable", "cond": "", "clase": "ciego_parseo"})
            continue
        lines = text.splitlines()
        parents: dict[int, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[id(child)] = parent

        # Indirección de un nivel: `hook = project_root / "hooks" / "x.sh"` y
        # después `if not hook.exists()`. Sin esto la condición no nombra
        # ninguna ruta y el censo se declara ciego sobre casos que sí puede ver.
        assigns: dict[str, str] = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                val = _src(n.value, lines)
                for tgt in n.targets:
                    if isinstance(tgt, ast.Name) and val:
                        assigns.setdefault(tgt.id, val)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
                assigns.setdefault(n.target.id, _src(n.value, lines))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            kind = cond = None
            if _is_pytest_attr(func, "importorskip"):
                kind = "importorskip"
                cond = _src(node, lines)
            elif _is_pytest_attr(func, "mark.skipif", "skipif"):
                kind = "skipif"
                cond = _src(node.args[0], lines) if node.args else ""
                if not cond:
                    for kw in node.keywords:
                        if kw.arg == "condition":
                            cond = _src(kw.value, lines)
            elif _is_pytest_attr(func, "mark.skip"):
                kind = "skip_incondicional"
                cond = ""
            elif _is_pytest_attr(func, "skip") and not _is_pytest_attr(func, "mark.skip"):
                kind = "skip"
                # Condición = el `if` que lo envuelve, subiendo por padres.
                cur: ast.AST | None = node
                cond = ""
                for _ in range(8):
                    p = parents.get(id(cur))
                    if p is None:
                        break
                    if isinstance(p, ast.If) and cond == "":
                        cond = _src(p.test, lines)
                        break
                    cur = p
                if cond == "":
                    # skip a nivel de módulo o dentro de except: la razón sirve.
                    reason = _src(node.args[0], lines) if node.args else ""
                    cond = reason
            if kind is None:
                continue
            reason = ""
            if node.args and kind in ("skip", "importorskip"):
                reason = _src(node.args[-1], lines)[:160]
            for kw in node.keywords:
                if kw.arg == "reason":
                    reason = _src(kw.value, lines)[:160]
            expanded = expand(cond, assigns)
            if kind == "importorskip":
                clase = "dep_opcional"
            elif kind == "skip_incondicional":
                clase = "incondicional"
            else:
                clase = classify(expanded)
                if clase in ("otra", "entorno") and ABSENCE_WORDS.search(reason) and \
                        (BARELIKE.search(reason) or BINLIKE.search(expanded)):
                    clase = "artefacto"
            entries.append(
                {
                    "file": str(f.relative_to(root)),
                    "line": node.lineno,
                    "kind": kind,
                    "cond": cond[:400],
                    "expanded": expanded[:800],
                    "reason": reason,
                    "clase": clase,
                }
            )
    return entries


def resolve_artifacts(root: Path, entries: list[dict]) -> None:
    """Para los skips de clase `artefacto`: ¿el artefacto existe, y dónde?

    Tres desenlaces, y el tercero es el hallazgo:
      presente_en_ruta   la ruta literal existe -> el skip NO se dispara
      otra_ubicacion     la ruta no existe pero el basename SÍ, en otro lado
      ausencia_real      no está en ninguna parte del árbol ni en el PATH
      (sin literal)      -> ciego: la condición no nombra una ruta resoluble
    """
    cache: dict[str, dict] = {}
    for e in entries:
        if e["clase"] != "artefacto":
            continue
        blob = e.get("expanded", e["cond"]) + " " + e.get("reason", "")
        refs = list(dict.fromkeys(PATHLIKE.findall(blob) + BARELIKE.findall(blob)))
        bins = list(dict.fromkeys(BINLIKE.findall(blob)))
        if not refs and not bins:
            e["resolucion"] = "sin_literal"
            continue
        outcomes: list[tuple[str, str, str]] = []
        for ref in refs[:4]:
            cand = _joined_candidate(blob, ref)
            base = Path(ref).name
            if base not in cache:
                cache[base] = locate(base, root=root, exact=True)
            found = cache[base]
            if (root / cand).exists() or (root / ref).exists() or _tail_of_real(cand, found):
                outcomes.append(("presente_en_ruta", cand, ""))
            elif found["found"]:
                where = found["hits"][0]["path"] if found["hits"] else (found["on_path"] or "")
                # Sólo es "ruta equivocada" si el test nombra una ruta de más de
                # un segmento y esa ruta no existe. Con un basename suelto no
                # se puede reconstruir la ruta que arma el test: es ciego.
                kind = "otra_ubicacion" if "/" in cand else "ambiguo_basename"
                outcomes.append((kind, cand, where))
            else:
                outcomes.append(("ausencia_real", cand, ""))
        for b in bins[:2]:
            if b not in cache:
                cache[b] = locate(b, root=root, exact=True)
            outcomes.append(
                ("presente_en_ruta" if cache[b]["found"] else "ausencia_real", b,
                 cache[b].get("on_path") or "")
            )
        if not outcomes:
            e["resolucion"] = "sin_literal"
            continue
        # Una ruta que cuelga del HOME del operador no es del repo: su ausencia
        # es un hecho sobre la máquina, no sobre el árbol.
        if re.search(r"Path\.home\(\)|\.home\(\)|expanduser", blob):
            e["resolucion"], e["ref"], e["donde"] = "fuera_del_repo", outcomes[0][1], ""
            continue
        kinds = {o[0] for o in outcomes}
        if len(kinds) > 1 and "presente_en_ruta" in kinds:
            # La condición nombra varias rutas y no todas fallan: el instrumento
            # no puede decir cuál manda. Ciego, no hallazgo.
            e["resolucion"], e["ref"], e["donde"] = "mixto_a_verificar", outcomes[0][1], outcomes[0][2]
            continue
        rank = {"otra_ubicacion": 0, "ausencia_real": 1, "ambiguo_basename": 2, "presente_en_ruta": 3}
        outcomes.sort(key=lambda o: rank[o[0]])
        e["resolucion"], e["ref"], e["donde"] = outcomes[0]


def _tail_of_real(cand: str, found: dict) -> bool:
    """`_lib/killswitch_check.sh` reconstruido desde `_HOOKS_DIR / "_lib" / ...`.

    El directorio venía de una variable, así que la ruta reconstruida es un
    SUFIJO de la real (`hooks/_lib/killswitch_check.sh`). Comparar por segmentos
    y no por texto: `cos_lib/x.py` NO termina en el segmento `lib`, aunque la
    cadena sí termine en `lib/x.py`.
    """
    segs = [s for s in cand.split("/") if s]
    if len(segs) < 2:
        return False
    for h in found.get("hits", []):
        real = [s for s in h["path"].split("/") if s]
        if len(real) >= len(segs) and real[-len(segs):] == segs:
            return True
    return False


def _joined_candidate(blob: str, ref: str) -> str:
    """Reconstruye `Path(root) / "hooks" / "x.sh"` como `hooks/x.sh`.

    Sin esto, un basename suelto se compara contra la raíz del repo y todo
    fixture que arme la ruta por segmentos se reporta como ruta equivocada:
    exactamente el falso positivo que este censo persigue.
    """
    if "/" in ref:
        return ref
    pat = re.compile(
        r"""((?:["'][A-Za-z0-9_.-]+["']\s*/\s*){0,4})["']""" + re.escape(ref) + r"""["']"""
    )
    m = pat.search(blob)
    if not m or not m.group(1).strip():
        return ref
    segs = re.findall(r"""["']([A-Za-z0-9_.-]+)["']""", m.group(1))
    return "/".join([*segs, ref])


def summarize(entries: list[dict]) -> dict:
    buckets: dict[str, int] = {}
    for e in entries:
        buckets[e["clase"]] = buckets.get(e["clase"], 0) + 1
    res: dict[str, int] = {}
    for e in entries:
        if e["clase"] == "artefacto":
            res[e.get("resolucion", "sin_literal")] = res.get(e.get("resolucion", "sin_literal"), 0) + 1
    return {"por_clase": buckets, "artefacto_resolucion": res, "total": len(entries)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Censo de skips condicionales que enmascaran ausencia.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=None)
    ap.add_argument("--show", default=None, help="listar entradas de una resolución (ej: otra_ubicacion)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else repo_root()
    if not root.is_dir():
        print(f"error: raíz inexistente: {root}", file=sys.stderr)
        return 2
    entries = collect(root)
    resolve_artifacts(root, entries)
    summary = summarize(entries)
    summary["how"] = "python3 scripts/skip_absence_census.py"
    summary["ciegos"] = {
        "condicion_no_resoluble_estaticamente": summary["artefacto_resolucion"].get("sin_literal", 0),
        "clase_otra": summary["por_clase"].get("otra", 0),
        "no_parseable": summary["por_clase"].get("ciego_parseo", 0),
    }

    if args.json:
        payload = {"resumen": summary}
        if args.show:
            payload["entradas"] = [e for e in entries if e.get("resolucion") == args.show]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"POBLACIÓN: {summary['total']} sitios de skip en tests/ y packages/*/tests/")
        for k, v in sorted(summary["por_clase"].items(), key=lambda kv: -kv[1]):
            print(f"  {k:16} {v}")
        print("ARTEFACTO — resolución:")
        for k, v in sorted(summary["artefacto_resolucion"].items(), key=lambda kv: -kv[1]):
            print(f"  {k:20} {v}")
        print("CIEGOS:", summary["ciegos"])
        if args.show:
            for e in entries:
                if e.get("resolucion") == args.show:
                    print(f"  {e['file']}:{e['line']}  ref={e.get('ref')}  donde={e.get('donde')}")

    bad = summary["artefacto_resolucion"].get("otra_ubicacion", 0) + \
        summary["artefacto_resolucion"].get("ausencia_real", 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
