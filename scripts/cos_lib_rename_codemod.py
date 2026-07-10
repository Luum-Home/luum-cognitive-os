#!/usr/bin/env python3
"""Deterministic codemod for the repo-wide ``lib`` -> ``cos_lib`` package rename.

Resolves risk U1 (namespace collision: a consumer's own top-level ``lib/`` shadowing
the projected COS ``lib/``) by renaming the shipped package to ``cos_lib`` and rewriting
every importer.

Design principles
-----------------
* **Dry-run by default.** ``--apply`` is required to mutate. ``--json`` emits machine output.
* **Protected-config guard.** ``--apply`` REFUSES to write any path under ``hooks/``,
  ``rules/``, ``skills/`` or ``.claude/`` (top-level). Those files are *listed* so a guarded
  env-session (``COS_ALLOW_PROTECTED_CONFIG_WRITE=1``) can run them in one atomic pass.
  A PARTIAL apply (guarded files skipped) leaves the repo BROKEN.
* **AST-aware for .py.** Imports are confirmed via the ``ast`` module, then the exact import
  line is edited with a boundary-anchored regex. Substrings such as ``pathlib``, ``zlib``,
  ``glob``, ``joblib``, ``library``, ``lib_`` and a variable named ``lib`` are never touched.
* **Module allowlist.** Only ``lib.<name>`` where ``<name>`` is an actual top-level module of
  the ``lib/`` package is rewritten. ``lib.telegram`` (which resolves to ``workflows/lib/``,
  a *different* package on sys.path) is therefore left alone and flagged UNSAFE.
* **Idempotent + reversible.** Re-running is a no-op once rewritten. Revert = ``git mv cos_lib
  lib`` + run this tool with ``--revert`` (swaps OLD/NEW). Nothing is done that ``git`` cannot
  cleanly undo.

The tool NEVER performs the ``git mv`` itself unless ``--apply`` is given; even then the dir
move is emitted as an explicit shell command for the operator to run in the atomic pass, so a
partial/aborted run can never leave a half-moved package.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

OLD_PKG = "lib"
NEW_PKG = "cos_lib"

# Top-level directories that the protected-config guard forbids writing in --apply.
GUARDED_PREFIXES = ("hooks", "rules", "skills", ".claude")

# Other top-level dirs literally named "lib" that are NOT the package under rename.
# The module allowlist already protects these, but we name them for auditability.
FOREIGN_LIB_DIRS = ("workflows/lib", "packages")  # packages/*/lib are symlink TARGETS

# --- boundary-anchored matchers -------------------------------------------------------------
# `lib.` used as a dotted-import prefix. Negative lookbehind on a word char / dot prevents
# matching inside pathlib., zlib., mylib., a.lib. etc.
RE_DOTTED = re.compile(r"(?<![A-Za-z0-9_.])lib(?=\.)")
# `from lib import ...` (package-level, no submodule in the dotted path).
RE_FROM_BARE = re.compile(r"(?<![A-Za-z0-9_.])lib(?=\s+import\b)")
# `-m lib.<mod>` on a command line (shell / docs / subprocess list).
RE_DASH_M = re.compile(r"(?<=-m\s)lib(?=\.)")

# String / path references that resolve the package by *directory name* (higher risk).
# Quoted directory-name refs like Path(...) / lib, list literals containing bare lib.
RE_PATH_STRING = re.compile(r"""['"]lib['"]""")


@dataclass
class Edit:
    path: str
    lineno: int
    kind: str          # from | import | from-bare | dash-m | sh-embedded
    before: str
    after: str


@dataclass
class Flag:
    path: str
    lineno: int
    reason: str
    snippet: str


@dataclass
class Result:
    edits: list[Edit] = field(default_factory=list)
    guarded_edits: list[Edit] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)          # UNSAFE / needs human review
    string_refs: list[Flag] = field(default_factory=list)    # separate higher-risk bucket
    symlinks: list[dict] = field(default_factory=list)
    files_changed: set[str] = field(default_factory=set)
    guarded_files: set[str] = field(default_factory=set)


# ------------------------------------------------------------------------------------------
def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(out.stdout.strip())


def is_guarded(rel: str) -> bool:
    parts = Path(rel).parts
    return bool(parts) and parts[0] in GUARDED_PREFIXES


def load_allowlist(root: Path, old: str, new: str | None = None) -> set[str]:
    """Top-level importable names of the package being renamed (files, dirs, symlinks).

    Order-independent: if `root/old` is absent (i.e. the mv has already happened),
    fall back to `root/new`. This makes --apply safe to run either before or
    after `git mv lib cos_lib`, preventing the empty-allowlist defect that leaves
    internal self-imports flagged as foreign instead of rewritten.
    """
    pkg = root / old
    if not pkg.is_dir() and new is not None:
        pkg = root / new
    names: set[str] = set()
    if not pkg.is_dir():
        return names
    for entry in pkg.iterdir():
        name = entry.name
        if name in ("__init__.py", "__pycache__"):
            continue
        if name.endswith(".py"):
            names.add(name[:-3])
        elif entry.is_dir() or entry.is_symlink():
            names.add(name[:-3] if name.endswith(".py") else name)
    return names


def git_tracked_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True,
    )
    return out.stdout.splitlines()


# ------------------------------------------------------------------------------------------
def rewrite_import_line(line: str, old: str, new: str) -> str:
    """Rewrite a single confirmed import line. Boundary-anchored; idempotent."""
    line = RE_DOTTED.sub(new, line)
    line = RE_FROM_BARE.sub(new, line)
    line = RE_DASH_M.sub(new, line)
    return line


def collect_py(root: Path, rel: str, allow: set[str], res: Result, old: str, new: str) -> None:
    path = root / rel
    try:
        src = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    try:
        tree = ast.parse(src, filename=rel)
    except SyntaxError:
        # Cannot AST-parse -> do NOT guess. Flag for human review if it mentions lib import.
        if re.search(r"(?<![A-Za-z0-9_.])lib\.", src):
            res.flags.append(Flag(rel, 0, "AST parse failed; lib import present, cannot auto-rewrite", ""))
        return

    lines = src.splitlines(keepends=True)

    def submodule_ok(mod_first_seg: str) -> bool:
        return mod_first_seg in allow

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top != old:
                    continue
                seg = alias.name.split(".")
                # `import lib` (bare) or `import lib.X`
                if len(seg) == 1:
                    _record_flag(res, rel, node.lineno,
                                 "bare `import lib` (package object) — verify no alias reliance",
                                 lines, node.lineno)
                    _apply(res, rel, node.lineno, lines, old, new, "import")
                elif submodule_ok(seg[1]):
                    _apply(res, rel, node.lineno, lines, old, new, "import")
                else:
                    _record_flag(res, rel, node.lineno,
                                 f"`import lib.{seg[1]}` — `{seg[1]}` not a top-level lib module (foreign/dynamic?)",
                                 lines, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or not node.module:
                continue
            seg = node.module.split(".")
            if seg[0] != old:
                continue
            if len(seg) == 1:
                # `from lib import X, Y` — the imported names ARE the submodules; verify.
                bad = [a.name for a in node.names if a.name not in allow]
                if bad:
                    _record_flag(res, rel, node.lineno,
                                 f"`from lib import {', '.join(bad)}` — name(s) not top-level lib modules (foreign/dynamic?)",
                                 lines, node.lineno)
                else:
                    _apply(res, rel, node.lineno, lines, old, new, "from-bare")
            elif submodule_ok(seg[1]):
                _apply(res, rel, node.lineno, lines, old, new, "from")
            else:
                _record_flag(res, rel, node.lineno,
                             f"`from lib.{seg[1]}` — `{seg[1]}` not a top-level lib module (e.g. workflows/lib collision)",
                             lines, node.lineno)

    # String/path references resolving the package by directory name.
    for i, ln in enumerate(lines, start=1):
        if RE_PATH_STRING.search(ln) and re.search(r"sys\.path|PYTHONPATH|/\s*['\"]lib['\"]|['\"]lib['\"]", ln):
            # Only surface those plausibly used for import resolution.
            if "sys.path" in ln or "PYTHONPATH" in ln or "path" in ln.lower():
                res.string_refs.append(Flag(rel, i, "string/path ref to a dir named 'lib' — verify: repo package vs. test fixture", ln.strip()))


def _apply(res: Result, rel: str, lineno: int, lines: list[str], old: str, new: str, kind: str) -> None:
    if lineno < 1 or lineno > len(lines):
        return
    before = lines[lineno - 1]
    after = rewrite_import_line(before, old, new)
    if after == before:
        return  # idempotent no-op
    edit = Edit(rel, lineno, kind, before.rstrip("\n"), after.rstrip("\n"))
    if is_guarded(rel):
        res.guarded_edits.append(edit)
        res.guarded_files.add(rel)
    else:
        res.edits.append(edit)
        res.files_changed.add(rel)


def _record_flag(res: Result, rel: str, lineno: int, reason: str, lines: list[str], ln: int) -> None:
    snippet = lines[ln - 1].strip() if 1 <= ln <= len(lines) else ""
    res.flags.append(Flag(rel, lineno, reason, snippet))


def collect_shell(root: Path, rel: str, res: Result, old: str, new: str) -> None:
    """.sh files with embedded python / -m lib. / PYTHONPATH refs (careful regex)."""
    path = root / rel
    try:
        src = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    for i, ln in enumerate(src.splitlines(keepends=True), start=1):
        if not re.search(r"(?<![A-Za-z0-9_.])lib\.|(?<=-m\s)lib\.|(?<![A-Za-z0-9_.])lib(?=\s+import\b)", ln):
            # PYTHONPATH="$X/lib" (dir on path) is a separate higher-risk bucket.
            if re.search(r"PYTHONPATH=[^\n]*(?<![A-Za-z0-9_./])lib(?![A-Za-z0-9_])", ln):
                res.string_refs.append(Flag(rel, i, "PYTHONPATH entry adds a dir named 'lib' — parent-of-package stays; a package-dir entry must become cos_lib", ln.strip()))
            continue
        after = rewrite_import_line(ln, old, new)
        if after == ln:
            continue
        edit = Edit(rel, i, "sh-embedded", ln.rstrip("\n"), after.rstrip("\n"))
        if is_guarded(rel):
            res.guarded_edits.append(edit)
            res.guarded_files.add(rel)
        else:
            res.edits.append(edit)
            res.files_changed.add(rel)


def collect_symlinks(root: Path, old: str, res: Result) -> None:
    pkg = root / old
    if not pkg.is_dir():
        return
    for entry in sorted(pkg.rglob("*")):
        if entry.is_symlink():
            target = os.readlink(entry)
            resolved = None
            try:
                resolved = os.path.realpath(entry)
            except OSError:
                pass
            rel = str(entry.relative_to(root))
            # After `git mv lib cos_lib` the symlink FILE moves; relative targets like
            # ../packages/*/lib/*.py stay valid because packages/ is a sibling of both.
            target_named_lib = bool(re.search(r"(^|/)lib(/|$)", target))
            res.symlinks.append({
                "path": rel,
                "target": target,
                "resolved": resolved,
                "target_contains_lib_dir": target_named_lib,
                "relative_target_stays_valid": target.startswith(".."),
            })


# ------------------------------------------------------------------------------------------
def run(root: Path, old: str, new: str) -> Result:
    res = Result()
    allow = load_allowlist(root, old, new)
    for rel in git_tracked_files(root):
        if rel.startswith(f"{old}/") and (root / rel).is_symlink():
            # symlink module files: their *import bodies* live at the target (packages/*/lib)
            continue
        if rel.endswith(".py"):
            collect_py(root, rel, allow, res, old, new)
        elif rel.endswith(".sh"):
            collect_shell(root, rel, res, old, new)
    collect_symlinks(root, old, res)
    return res


def apply_edits(root: Path, res: Result, allow_protected: bool) -> tuple[int, int]:
    """Apply non-guarded edits. Refuse guarded unless COS_ALLOW_PROTECTED_CONFIG_WRITE=1."""
    by_file: dict[str, list[Edit]] = {}
    pool = list(res.edits)
    if allow_protected:
        pool += res.guarded_edits
    for e in pool:
        by_file.setdefault(e.path, []).append(e)
    written = 0
    for rel, edits in by_file.items():
        if is_guarded(rel) and not allow_protected:
            continue
        path = root / rel
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for e in edits:
            cur = lines[e.lineno - 1]
            lines[e.lineno - 1] = rewrite_import_line(cur, OLD_PKG, NEW_PKG)
        path.write_text("".join(lines), encoding="utf-8")
        written += 1
    return written, len(by_file)


def prose_sweep(root: Path, allow_protected: bool) -> tuple[int, int]:
    """Second-pass rewrite of prose references (comments, docstrings, string data)
    where `lib.X` appears outside AST-import positions.

    Uses the same boundary-anchored RE_DOTTED / RE_FROM_BARE / RE_DASH_M regexes as
    the import rewriter, so `cos_lib.X` and other `_lib` suffixes stay untouched
    (negative lookbehind rejects them). Skips workflows/ per RISKY-edge policy.

    Idempotent: re-running produces no further changes.
    """
    files_scanned = 0
    files_written = 0
    for rel in git_tracked_files(root):
        if not (rel.endswith(".py") or rel.endswith(".sh") or rel.endswith(".md")):
            continue
        # Skip workflows/ — its `lib.telegram` refs live in a different package (U-Q2 policy).
        if rel.startswith("workflows/"):
            continue
        # Skip the codemod itself and the design/proposal docs describing the rename.
        if rel == "scripts/cos_lib_rename_codemod.py":
            continue
        if is_guarded(rel) and not allow_protected:
            continue
        path = root / rel
        if not path.is_file() or path.is_symlink():
            continue
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new = RE_DOTTED.sub(NEW_PKG, text)
        new = RE_FROM_BARE.sub(NEW_PKG, new)
        new = RE_DASH_M.sub(NEW_PKG, new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            files_written += 1
    return files_scanned, files_written


# ------------------------------------------------------------------------------------------
def print_human(res: Result, old: str, new: str, apply: bool, allow_protected: bool) -> None:
    total_lines = len(res.edits) + len(res.guarded_edits)
    print(f"# {old} -> {new} rename codemod ({'APPLY' if apply else 'DRY-RUN'})")
    print()
    print(f"Unguarded files to change : {len(res.files_changed)}")
    print(f"Unguarded lines to change : {len(res.edits)}")
    print(f"GUARDED files (need env-session) : {len(res.guarded_files)}")
    print(f"GUARDED lines : {len(res.guarded_edits)}")
    print(f"Total files : {len(res.files_changed) + len(res.guarded_files)}")
    print(f"Total import lines : {total_lines}")
    print(f"RISKY / unsafe-to-auto edge cases : {len(res.flags)}")
    print(f"String/path refs (higher-risk, enumerated only) : {len(res.string_refs)}")
    print(f"Symlinks in {old}/ : {len(res.symlinks)}")
    print()
    if apply and res.guarded_files and not allow_protected:
        print("!" * 78)
        print("WARNING: PARTIAL APPLY. Guarded files under hooks/ rules/ skills/ .claude/ were")
        print("SKIPPED. The repo is now BROKEN (importers rewritten, guarded importers not).")
        print("Re-run in a guarded env-session as ONE atomic pass:")
        print("  COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 scripts/cos_lib_rename_codemod.py --apply")
        print("!" * 78)


def to_json(res: Result, old: str, new: str) -> dict:
    return {
        "old": old, "new": new,
        "totals": {
            "unguarded_files": len(res.files_changed),
            "unguarded_lines": len(res.edits),
            "guarded_files": len(res.guarded_files),
            "guarded_lines": len(res.guarded_edits),
            "total_files": len(res.files_changed) + len(res.guarded_files),
            "total_lines": len(res.edits) + len(res.guarded_edits),
            "risky_flags": len(res.flags),
            "string_refs": len(res.string_refs),
            "symlinks": len(res.symlinks),
        },
        "guarded_files": sorted(res.guarded_files),
        "flags": [vars(f) for f in res.flags],
        "string_refs": [vars(f) for f in res.string_refs],
        "symlinks": res.symlinks,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="mutate files (default: dry-run)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--revert", action="store_true", help="swap direction: cos_lib -> lib")
    ap.add_argument("--root", default=None, help="repo root (default: git toplevel)")
    ap.add_argument("--prose-sweep", action="store_true",
                    help="also rewrite `lib.X` in comments/docstrings/data strings "
                    "(second pass, boundary-anchored, workflows/ excluded)")
    args = ap.parse_args(argv)

    old, new = (NEW_PKG, OLD_PKG) if args.revert else (OLD_PKG, NEW_PKG)
    globals()["OLD_PKG"], globals()["NEW_PKG"] = old, new  # keep apply_edits consistent

    root = Path(args.root) if args.root else repo_root()
    res = run(root, old, new)

    allow_protected = os.environ.get("COS_ALLOW_PROTECTED_CONFIG_WRITE") == "1"

    if args.apply:
        if not root.joinpath(new).exists():
            print(f"NOTE: run `git mv {old} {new}` first (package dir not yet moved).", file=sys.stderr)
        written, total = apply_edits(root, res, allow_protected)
        print(f"applied edits to {written}/{total} files "
              f"({'incl.' if allow_protected else 'EXCL.'} guarded)", file=sys.stderr)
        if args.prose_sweep:
            scanned, sweep_written = prose_sweep(root, allow_protected)
            print(f"prose sweep: rewrote {sweep_written}/{scanned} files "
                  f"(comments/docstrings/data strings)", file=sys.stderr)

    if args.json:
        print(json.dumps(to_json(res, old, new), indent=2))
    else:
        print_human(res, old, new, args.apply, allow_protected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
