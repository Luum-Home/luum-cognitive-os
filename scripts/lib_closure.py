#!/usr/bin/env python3
"""Dependency-closure computation for hook `cos_lib.*` imports.

Implements the closure algorithm from
`docs/02-Decisions/designs/hook-lib-projection-contract.md` §2.2:

1. Seed set = hooks passed in by the caller (already filtered by profile).
2. Extract `cos_lib.<mod>` references from each seed hook across the three
   embedding forms hooks use: heredocs, inline `-c` strings, and
   `python3 -m cos_lib.<mod>`. A regex seeds the candidate set; heredoc bodies
   are additionally parsed with `ast` to drop false positives that a pure
   regex would pick up from comments/strings.
3. Transitive resolution over `lib/` itself: for every `cos_lib.<mod>` found,
   resolve `lib/<mod>.py` through its symlink (if any), `ast.parse` the real
   target, and add any further `cos_lib.<other>` imports to the worklist until
   a fixpoint is reached.
4. Return a `{module_name: ClosureEntry}` mapping the caller can use to
   project the closure and emit a provenance manifest.

Standalone-testable via the `main()` CLI:

    python3 scripts/lib_closure.py --hooks hook1.sh hook2.sh --repo-root .
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Set

# Matches `from cos_lib.<mod>`, `import cos_lib.<mod>`, `-m cos_lib.<mod>`, and
# `python3 -m cos_lib.<mod>` — the three embedding forms named in §2.2 step 2.
_LIB_IMPORT_RE = re.compile(
    r"(?:from lib\.|import lib\.|-m lib\.|python3 -m lib\.)([A-Za-z0-9_]+)"
)

# Heredoc block: `<<[-]?'MARKER'` or `<<[-]?MARKER` ... body ... `MARKER`
# (unindented terminator, matching common hook authoring style).
_HEREDOC_RE = re.compile(
    r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\n(.*?)\n\1\b",
    re.DOTALL,
)


@dataclass
class ClosureEntry:
    """One resolved member of the cos_lib.* dependency closure."""

    source_real_path: str
    was_symlink: bool
    sha256_hex: str

    def to_manifest_dict(self) -> dict:
        """§2.2 step 5 manifest shape: {sha256, source_rel_path, was_symlink}."""
        return {
            "sha256": self.sha256_hex,
            "source_rel_path": self.source_real_path,
            "was_symlink": self.was_symlink,
        }


def _extract_lib_modules_from_text(text: str) -> Set[str]:
    """Regex-only extraction (covers -c / -m forms and any residual text)."""
    return set(_LIB_IMPORT_RE.findall(text))


def _extract_lib_modules_ast(source: str) -> Set[str]:
    """AST-based extraction for a Python source blob (heredoc body).

    Walks Import/ImportFrom nodes and collects module names whose root is
    `lib`. Returns an empty set (never raises) if the blob does not parse —
    callers fall back to regex extraction in that case.
    """
    modules: Set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return modules

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "lib" and len(parts) > 1:
                    modules.add(parts[1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split(".")
                if parts[0] == "lib" and len(parts) > 1:
                    modules.add(parts[1])
    return modules


def extract_lib_modules_from_hook(hook_path: Path) -> Set[str]:
    """Extract the `cos_lib.<mod>` reference set from one hook file.

    Regex-seeds the whole file (covers `-c` / `-m cos_lib.<mod>` forms), then
    upgrades heredoc bodies to AST-based extraction to drop false positives
    (comments, strings) that the regex alone would include.
    """
    try:
        text = hook_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()

    modules = _extract_lib_modules_from_text(text)

    for match in _HEREDOC_RE.finditer(text):
        body = match.group(2)
        ast_modules = _extract_lib_modules_ast(body)
        if ast_modules:
            # AST successfully parsed this heredoc: trust it as the
            # authoritative set for this block. The regex pass above still
            # contributes any modules found outside heredocs (e.g. `-c`,
            # `-m`), so we only ever add here, never replace globally.
            modules |= ast_modules

    return modules


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def compute_closure(
    hook_paths: Iterable[Path], repo_root: Path
) -> Dict[str, ClosureEntry]:
    """Compute the transitive cos_lib.* dependency closure for a set of hooks.

    Args:
        hook_paths: seed set — hooks actually projected for the active
            profile (caller filters by `scope_allows` / default vs full).
        repo_root: SOURCE repo root; `repo_root/lib/<mod>.py` is resolved
            for each module, following symlinks to their real target.

    Returns:
        Mapping of module name -> ClosureEntry (real path, symlink flag,
        sha256 of the dereferenced content).
    """
    lib_dir = repo_root / "lib"

    worklist: List[str] = []
    seen: Set[str] = set()

    for hook_path in hook_paths:
        hook_path = Path(hook_path)
        if not hook_path.is_file():
            continue
        for mod in extract_lib_modules_from_hook(hook_path):
            if mod not in seen:
                seen.add(mod)
                worklist.append(mod)

    closure: Dict[str, ClosureEntry] = {}

    while worklist:
        mod = worklist.pop()
        candidate = lib_dir / f"{mod}.py"
        if not candidate.exists():
            # Static-closure miss (§2.3): module referenced but not present
            # on disk. Skip — the fail-open backstop covers this at runtime.
            continue

        was_symlink = candidate.is_symlink()
        real_path = candidate.resolve()

        try:
            source = real_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            source = ""

        try:
            source_rel_path = str(real_path.relative_to(repo_root.resolve()))
        except ValueError:
            source_rel_path = str(real_path)

        closure[mod] = ClosureEntry(
            source_real_path=source_rel_path,
            was_symlink=was_symlink,
            sha256_hex=_sha256_of_file(real_path),
        )

        # Transitive step: parse the real target for further cos_lib.* imports.
        for other in _extract_lib_modules_ast(source) | _extract_lib_modules_from_text(source):
            if other not in seen:
                seen.add(other)
                worklist.append(other)

    return closure


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute the transitive cos_lib.* dependency closure for a set of hooks."
    )
    parser.add_argument(
        "--hooks", nargs="+", required=True, help="Hook file paths (seed set)."
    )
    parser.add_argument(
        "--repo-root", required=True, help="SOURCE repo root containing lib/."
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    hook_paths = [Path(h) for h in args.hooks]

    closure = compute_closure(hook_paths, repo_root)
    output = {mod: entry.to_manifest_dict() for mod, entry in sorted(closure.items())}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
