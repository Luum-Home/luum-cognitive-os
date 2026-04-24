#!/usr/bin/env python3
"""invariant-check-helper — propose pytest invariants between numeric constant pairs.

Reads two file paths (typically an ADR and a Python implementation). Extracts
numeric constants, pairs them by name similarity, and emits pytest assertions
to stdout that enforce the relationship.

Usage:
    python3 scripts/invariant_check_helper.py <file-a> <file-b> [--min-similarity 0.5]

Exit 0 on success. Non-zero only when BOTH inputs are unreadable.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable


# Python-style assignment: NAME = <number>
PY_ASSIGN_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z_][\w\[\], ]*)?\s*=\s*"
    r"(?P<value>-?\d+(?:\.\d+)?)\b"
)

# ADR-style: backtick name near a number on the same line, e.g. `threshold_pct=5.0`
# Also catches prose like "threshold is 5.0 %".
ADR_TOKEN_RE = re.compile(
    r"`?(?P<name>[A-Za-z_][A-Za-z0-9_]*)`?\s*[=:]\s*(?P<value>-?\d+(?:\.\d+)?)"
)
ADR_NEAR_RE = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_ ]{2,40}?)[^A-Za-z0-9_]{1,20}?"
    r"(?P<value>-?\d+(?:\.\d+)?)\s*(?:%|min|s|ms|seconds|minutes|percent|pct)"
)


@dataclass(frozen=True)
class Constant:
    name: str
    value: float
    source: str  # "py" or "adr"
    line: int
    file: str
    raw: str


def extract_python(path: str) -> list[Constant]:
    out: list[Constant] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, start=1):
                m = PY_ASSIGN_RE.match(line)
                if not m:
                    continue
                try:
                    val = float(m.group("value"))
                except ValueError:
                    continue
                out.append(
                    Constant(
                        name=m.group("name"),
                        value=val,
                        source="py",
                        line=i,
                        file=path,
                        raw=line.rstrip("\n"),
                    )
                )
    except OSError:
        pass
    return out


def extract_adr(path: str) -> list[Constant]:
    out: list[Constant] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, start=1):
                for m in ADR_TOKEN_RE.finditer(line):
                    try:
                        val = float(m.group("value"))
                    except ValueError:
                        continue
                    name = m.group("name").strip()
                    if not name or name.lower() in {"s", "ms", "min"}:
                        continue
                    out.append(
                        Constant(
                            name=name,
                            value=val,
                            source="adr",
                            line=i,
                            file=path,
                            raw=line.rstrip("\n"),
                        )
                    )
                for m in ADR_NEAR_RE.finditer(line):
                    try:
                        val = float(m.group("value"))
                    except ValueError:
                        continue
                    name = m.group("name").strip().replace(" ", "_")
                    if len(name) < 3:
                        continue
                    out.append(
                        Constant(
                            name=name,
                            value=val,
                            source="adr",
                            line=i,
                            file=path,
                            raw=line.rstrip("\n"),
                        )
                    )
    except OSError:
        pass
    return out


def normalize(name: str) -> str:
    """Normalize constant name for similarity: lowercase, strip leading underscores,
    drop common suffixes like _PCT, _S, _MS, _COUNT."""
    n = name.lower().lstrip("_")
    for suf in ("_pct", "_percent", "_pc", "_s", "_ms", "_count", "_seconds"):
        if n.endswith(suf):
            n = n[: -len(suf)]
            break
    return n


def similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    # Substring boost: "cpu_idle_threshold" vs "threshold_pct" -> overlap
    if na in nb or nb in na:
        return max(0.75, SequenceMatcher(None, na, nb).ratio())
    return SequenceMatcher(None, na, nb).ratio()


def pair_constants(
    py: Iterable[Constant], adr: Iterable[Constant], min_sim: float
) -> list[tuple[Constant, Constant, float]]:
    py_list = list(py)
    adr_list = list(adr)
    pairs: list[tuple[Constant, Constant, float]] = []
    used_adr: set[int] = set()
    for p in py_list:
        best: tuple[int, float] | None = None
        for idx, a in enumerate(adr_list):
            if idx in used_adr:
                continue
            sim = similarity(p.name, a.name)
            if sim >= min_sim and (best is None or sim > best[1]):
                best = (idx, sim)
        if best is not None:
            used_adr.add(best[0])
            pairs.append((p, adr_list[best[0]], best[1]))
    return pairs


def slugify(name: str) -> str:
    n = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return n or "invariant"


def adr_id(path: str) -> str:
    base = os.path.basename(path)
    m = re.search(r"ADR-(\d+)", base, re.IGNORECASE)
    return m.group(1) if m else "unknown"


def module_path(path: str) -> str:
    """Convert a Python file path to a dotted import path, relative to cwd
    or to the first 'lib/'/'packages/'/'src/' segment found."""
    rel = path
    if rel.endswith(".py"):
        rel = rel[:-3]
    rel = rel.replace(os.sep, "/")
    # Try to make relative to cwd first
    cwd = os.getcwd().replace(os.sep, "/").rstrip("/")
    if rel.startswith(cwd + "/"):
        rel = rel[len(cwd) + 1:]
    # Anchor on common source roots
    for anchor in ("lib/", "packages/", "src/", "tests/"):
        idx = rel.find("/" + anchor)
        if idx >= 0:
            rel = rel[idx + 1:]
            break
        if rel.startswith(anchor):
            break
    parts = [p for p in rel.split("/") if p and p != "." and not p.startswith(".")]
    return ".".join(parts)


def emit_test(p: Constant, a: Constant, adr_file: str) -> str:
    aid = adr_id(adr_file)
    fn_base = slugify(p.name.lstrip("_"))
    test_name = f"test_{fn_base}_matches_adr_{aid}"
    mod = module_path(p.file)
    rel = "=="
    note = ""
    if p.value != a.value:
        rel = "=="
        note = f"  # DRIFT DETECTED: py={p.value} adr={a.value} — confirm direction"
    lines = [
        f"def {test_name}():",
        f'    """Invariant (ADR-{aid} line {a.line}): {p.name} must equal ADR value.',
        f"    Py source:  {p.file}:{p.line}",
        f"    ADR source: {a.file}:{a.line}",
        f'    """',
        f"    from {mod} import {p.name}",
        f"    ADR_VALUE = {a.value!r}",
        f"    assert {p.name} {rel} ADR_VALUE{note}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="invariant-check-helper",
        description="Propose pytest invariants between numeric constant pairs.",
    )
    p.add_argument("file_a", help="First file (typically an ADR .md)")
    p.add_argument("file_b", help="Second file (typically a Python lib .py)")
    p.add_argument(
        "--min-similarity",
        type=float,
        default=0.5,
        help="Minimum name-similarity to pair constants (0.0-1.0)",
    )
    ns = p.parse_args(argv)

    a_readable = os.path.isfile(ns.file_a) and os.access(ns.file_a, os.R_OK)
    b_readable = os.path.isfile(ns.file_b) and os.access(ns.file_b, os.R_OK)
    if not a_readable and not b_readable:
        print(
            f"ERROR: neither {ns.file_a} nor {ns.file_b} is readable",
            file=sys.stderr,
        )
        return 2

    # Decide which file is ADR vs python by extension.
    def is_py(path: str) -> bool:
        return path.endswith(".py")

    if is_py(ns.file_a) and not is_py(ns.file_b):
        py_file, adr_file = ns.file_a, ns.file_b
    elif is_py(ns.file_b) and not is_py(ns.file_a):
        py_file, adr_file = ns.file_b, ns.file_a
    elif is_py(ns.file_a) and is_py(ns.file_b):
        py_file, adr_file = ns.file_a, ns.file_b
    else:
        # Both non-python: treat file_b as "python-ish" (won't find Python
        # assignments, just ADR tokens in both)
        py_file, adr_file = ns.file_b, ns.file_a

    py_consts = extract_python(py_file) if is_py(py_file) else []
    adr_consts = extract_adr(adr_file)

    pairs = pair_constants(py_consts, adr_consts, ns.min_similarity)

    print(
        f"# invariant-check — proposed pytest invariants\n"
        f"# Py file:  {py_file}  ({len(py_consts)} constants)\n"
        f"# ADR file: {adr_file} ({len(adr_consts)} tokens)\n"
        f"# Pairs:    {len(pairs)} (min_similarity={ns.min_similarity})\n"
    )

    if not pairs:
        print(
            "# No invariant pairs proposed. Lower --min-similarity or rename "
            "constants to share a suffix.\n"
        )
        return 0

    for py_c, adr_c, sim in pairs:
        print(f"# --- pair (similarity={sim:.2f}) ---")
        print(f"# py:  {py_c.name}={py_c.value}  ({py_c.file}:{py_c.line})")
        print(f"# adr: {adr_c.name}={adr_c.value} ({adr_c.file}:{adr_c.line})")
        print(emit_test(py_c, adr_c, adr_file))

    return 0


if __name__ == "__main__":
    sys.exit(main())
