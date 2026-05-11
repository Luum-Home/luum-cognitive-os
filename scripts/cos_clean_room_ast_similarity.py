#!/usr/bin/env python3
"""
cos_clean_room_ast_similarity.py — ADR-271 Tier 2 clean-room detection.

Detects symbol-renamed clones by AST-normalizing both staged Python files and
every Python file in .cognitive-os/external-source-cache/, then comparing
SHA-256 hashes of normalized top-level function/class bodies.

What this tool DOES catch:
  - Identical function/class bodies where all identifiers have been renamed
    (the "s/foo/bar/g" attack).
  - Structural ports where formatting/whitespace differs but the algorithm
    (control flow, operators, literal values) is preserved.

What this tool does NOT catch (honest documentation):
  - Paraphrased adaptations with substantially different control flow.
  - Cross-language ports (Python-only in v1; TypeScript/Rust/Go: T5 only).
  - Pseudocode descriptions or prose explanations of upstream algorithms.
  - Concept-level design reuse (no code copy, same pattern).
  - Partial-function copies (sub-body splicing).
  See rules/clean-room-detection-limits.md for the full tier matrix.

Common false-positive classes (mitigated via baseline):
  - `__init__` stubs: `def __init__(self): pass` is identical for any class.
  - Empty / pass-only functions across many files.
  - `argparse`/`click` boilerplate: common option-parser patterns normalize
    to the same hash. Baseline seed captures these on first run.
  - `dataclass` field definitions with no logic.
  - Trivial getters/setters.
  The --baseline flag seeds these into manifests/ast-similarity-baseline.yaml
  so subsequent commits are clean.

Usage:
  python3 scripts/cos_clean_room_ast_similarity.py [options]

Options:
  --baseline         Write current matches to manifests/ast-similarity-baseline.yaml
  --quick            Staged files only (default behaviour; listed for hook compat)
  --format FORMAT    Output format: text (default) | json | markdown
  --allowlist PATH   Path to file with path-prefix excludes, one per line
  --ci               Exit 1 on any non-baseline match (same as default, explicit flag)

Performance:
  Index is cached at .cognitive-os/runtime/ast-similarity-index.json and
  rebuilt only when any .py file in external-source-cache is newer than the
  index. Warm run on typical commit (5-15 staged files): < 1s.
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT_DIR / ".cognitive-os" / "external-source-cache"
RUNTIME_DIR = ROOT_DIR / ".cognitive-os" / "runtime"
INDEX_FILE = RUNTIME_DIR / "ast-similarity-index.json"
BASELINE_FILE = ROOT_DIR / "manifests" / "ast-similarity-baseline.yaml"
DEFAULT_ALLOWLIST = [
    "docs/research/",
    "docs/adrs/",
]
MIN_BODY_LINES = 3  # skip trivial stubs shorter than this


# ── AST normalization ──────────────────────────────────────────────────────────


def _strip_docstring(node: ast.AST) -> None:
    """Remove docstring from function/class body in-place (modifies node)."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return
    body = node.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        node.body = body[1:]


def _strip_annotations(node: ast.AST) -> None:
    """Remove type annotations from function arguments and return types."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.returns = None
        for arg in (
            node.args.args
            + node.args.posonlyargs
            + node.args.kwonlyargs
            + ([node.args.vararg] if node.args.vararg else [])
            + ([node.args.kwarg] if node.args.kwarg else [])
        ):
            arg.annotation = None
    elif isinstance(node, ast.AnnAssign):
        # Convert annotated assignment to plain assignment or remove if no value
        pass  # handled via visitor below


class _NormVisitor(ast.NodeTransformer):
    """
    Replace every user-defined name with positional placeholders _v1, _v2, ...
    keyed by first-occurrence order within the subtree being normalized.

    Built-ins and dunder names are preserved so structural comparison remains
    meaningful (e.g. `isinstance`, `len`, `__init__`).
    """

    _BUILTINS = frozenset(
        dir(__builtins__) if isinstance(__builtins__, dict) else dir(__builtins__)
    )
    _PRESERVED = frozenset(
        [
            # common dunders worth preserving for structure
            "__init__",
            "__new__",
            "__del__",
            "__repr__",
            "__str__",
            "__eq__",
            "__hash__",
            "__len__",
            "__iter__",
            "__next__",
            "__enter__",
            "__exit__",
            "__call__",
            "__getitem__",
            "__setitem__",
            "__delitem__",
            "__contains__",
            "__bool__",
            "self",
            "cls",
        ]
    )

    def __init__(self) -> None:
        self._mapping: dict[str, str] = {}
        self._counter = 0

    def _placeholder(self, name: str) -> str:
        if name in self._PRESERVED or name in self._BUILTINS:
            return name
        if name not in self._mapping:
            self._counter += 1
            self._mapping[name] = f"_v{self._counter}"
        return self._mapping[name]

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = self._placeholder(node.id)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.name = self._placeholder(node.name)
        _strip_docstring(node)
        _strip_annotations(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        node.name = self._placeholder(node.name)
        _strip_docstring(node)
        _strip_annotations(node)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        node.name = self._placeholder(node.name)
        _strip_docstring(node)
        self.generic_visit(node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = self._placeholder(node.arg)
        node.annotation = None
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        """Drop type annotation, keep value assignment if present."""
        if node.value is not None:
            assign = ast.Assign(
                targets=[node.target],
                value=node.value,
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
            return self.generic_visit(assign)
        # Pure annotation with no value — drop entirely
        return None

    def visit_Import(self, node: ast.Import) -> ast.Import:
        # Normalize import names too
        for alias in node.names:
            alias.name = self._placeholder(alias.name)
            if alias.asname:
                alias.asname = self._placeholder(alias.asname)
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        if node.module:
            node.module = self._placeholder(node.module)
        for alias in node.names:
            alias.name = self._placeholder(alias.name)
            if alias.asname:
                alias.asname = self._placeholder(alias.asname)
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        node.attr = self._placeholder(node.attr)
        self.generic_visit(node)
        return node

    def visit_keyword(self, node: ast.keyword) -> ast.keyword:
        if node.arg:
            node.arg = self._placeholder(node.arg)
        self.generic_visit(node)
        return node


def _normalize_node(node: ast.AST) -> str:
    """
    Return a canonical normalized string for a function/class AST node.
    Each normalization gets a fresh visitor so placeholders are local.
    """
    visitor = _NormVisitor()
    normalized = visitor.visit(ast.fix_missing_locations(ast.copy_location(node, node)))
    return ast.dump(
        normalized, annotate_fields=False, include_attributes=False
    )


def _source_line_count(node: ast.AST) -> int:
    """Count approximate lines in the node."""
    try:
        end = getattr(node, "end_lineno", None)
        start = getattr(node, "lineno", None)
        if end and start:
            return end - start + 1
    except Exception:
        pass
    return 0


def _hash_node(node: ast.AST) -> str | None:
    """Hash the normalized canonical form. Returns None if body too trivial."""
    if _source_line_count(node) < MIN_BODY_LINES:
        return None
    try:
        canonical = _normalize_node(node)
        return hashlib.sha256(canonical.encode()).hexdigest()
    except Exception:
        return None


def _extract_top_level_units(
    source: str, filepath: str
) -> list[dict[str, Any]]:
    """
    Parse source and extract top-level functions + classes.
    Returns list of dicts: {name, kind, hash, lineno}.
    """
    try:
        # Strip type: ignore comments and encoding declarations before parse
        cleaned = re.sub(r"#.*$", "", source, flags=re.MULTILINE)
        tree = ast.parse(cleaned, filename=filepath)
    except SyntaxError:
        return []

    units = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            h = _hash_node(node)
            if h:
                units.append(
                    {
                        "name": node.name,
                        "kind": "function",
                        "hash": h,
                        "lineno": node.lineno,
                    }
                )
        elif isinstance(node, ast.ClassDef):
            h = _hash_node(node)
            if h:
                units.append(
                    {"name": node.name, "kind": "class", "hash": h, "lineno": node.lineno}
                )
            # Also hash each method independently (per-function granularity per ADR-271)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mh = _hash_node(child)
                    if mh:
                        units.append(
                            {
                                "name": f"{node.name}.{child.name}",
                                "kind": "method",
                                "hash": mh,
                                "lineno": child.lineno,
                            }
                        )
    return units


# ── External-source-cache index ───────────────────────────────────────────────


def _cache_mtime(cache_dir: Path) -> float:
    """Return max mtime of any .py file in cache_dir."""
    max_mtime = 0.0
    for py_file in cache_dir.rglob("*.py"):
        try:
            mtime = py_file.stat().st_mtime
            if mtime > max_mtime:
                max_mtime = mtime
        except OSError:
            pass
    return max_mtime


def _build_index(cache_dir: Path) -> dict[str, Any]:
    """Build AST hash index from all .py files in cache_dir."""
    index: dict[str, list[dict[str, Any]]] = {}
    for py_file in cache_dir.rglob("*.py"):
        rel = str(py_file.relative_to(cache_dir))
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        units = _extract_top_level_units(source, str(py_file))
        if units:
            index[rel] = units
    return {
        "built_at": datetime.datetime.utcnow().isoformat(),
        "cache_mtime": _cache_mtime(cache_dir),
        "files": index,
    }


def _load_or_build_index(cache_dir: Path) -> dict[str, Any]:
    """Load cached index if fresh, otherwise rebuild."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    current_mtime = _cache_mtime(cache_dir)

    if INDEX_FILE.exists():
        try:
            stored = json.loads(INDEX_FILE.read_text())
            if stored.get("cache_mtime", 0) >= current_mtime:
                return stored
        except (json.JSONDecodeError, KeyError):
            pass

    index = _build_index(cache_dir)
    try:
        INDEX_FILE.write_text(json.dumps(index, indent=2))
    except OSError:
        pass
    return index


def _flat_hash_map(index: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """
    Return {hash -> [{file, name, kind}]} from the index for O(1) lookup.
    """
    result: dict[str, list[dict[str, str]]] = {}
    for rel_file, units in index.get("files", {}).items():
        for unit in units:
            h = unit["hash"]
            if h not in result:
                result[h] = []
            result[h].append(
                {"file": rel_file, "name": unit["name"], "kind": unit["kind"]}
            )
    return result


# ── Staged files ───────────────────────────────────────────────────────────────


def _get_staged_python_files(repo_root: Path) -> list[Path]:
    """Return list of staged .py files (absolute paths)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        files = []
        for line in result.stdout.splitlines():
            if line.endswith(".py"):
                p = repo_root / line
                if p.exists():
                    files.append(p)
        return files
    except Exception:
        return []


# ── Baseline ───────────────────────────────────────────────────────────────────


def _load_baseline(baseline_path: Path) -> set[str]:
    """Return set of accepted hashes from baseline YAML (simple line parser)."""
    accepted: set[str] = set()
    if not baseline_path.exists():
        return accepted
    for line in baseline_path.read_text().splitlines():
        m = re.match(r"\s+ast_hash:\s+([0-9a-f]{64})", line)
        if m:
            accepted.add(m.group(1))
    return accepted


def _load_baseline_pairs(baseline_path: Path) -> set[tuple[str, str]]:
    """Return set of (cos_file_rel, ast_hash) pairs from baseline.

    YAML list entries start with '  - cos_file:' so we match both
    '    cos_file:' and '  - cos_file:' patterns.
    """
    pairs: set[tuple[str, str]] = set()
    if not baseline_path.exists():
        return pairs
    current_cos_file = ""
    for line in baseline_path.read_text().splitlines():
        # Match both '  - cos_file: ...' and '    cos_file: ...' (first/other fields)
        m_file = re.match(r"[\s\-]+cos_file:\s+(.+)", line)
        if m_file:
            current_cos_file = m_file.group(1).strip()
        m_hash = re.match(r"\s+ast_hash:\s+([0-9a-f]{64})", line)
        if m_hash and current_cos_file:
            pairs.add((current_cos_file, m_hash.group(1)))
    return pairs


def _write_baseline(matches: list[dict[str, Any]], repo_root: Path) -> None:
    """Write matches to manifests/ast-similarity-baseline.yaml."""
    now = datetime.date.today().isoformat()
    lines = [
        "schema_version: ast-similarity-baseline/v1",
        f"generated: {now}",
        "note: |",
        "  ACCEPTED AST similarity hits — symbol-renamed or structurally-identical",
        "  units from external-source-cache that have been reviewed and are permitted",
        "  (e.g. common Python idioms, boilerplate). New hits NOT in this file block",
        "  commits. See rules/clean-room-detection-limits.md for tier matrix.",
        "accepted:",
    ]
    for m in matches:
        lines += [
            f"  - cos_file: {m['cos_file']}",
            f"    cos_unit: {m['cos_unit']}",
            f"    cache_file: {m['cache_file']}",
            f"    cache_unit: {m['cache_unit']}",
            f"    ast_hash: {m['ast_hash']}",
            f"    classification: {m['classification']}",
            f"    note: seeded by --baseline run on {now}",
        ]
    BASELINE_FILE.write_text("\n".join(lines) + "\n")
    print(f"Baseline written: {BASELINE_FILE} ({len(matches)} entries)")


# ── Allowlist ──────────────────────────────────────────────────────────────────


def _load_allowlist(allowlist_path: str | None) -> list[str]:
    prefixes = list(DEFAULT_ALLOWLIST)
    if allowlist_path:
        p = Path(allowlist_path)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    prefixes.append(line)
    return prefixes


def _is_allowlisted(rel_path: str, prefixes: list[str]) -> bool:
    for prefix in prefixes:
        if rel_path.startswith(prefix):
            return True
    return False


# ── Core scan ──────────────────────────────────────────────────────────────────


def scan(
    staged_files: list[Path],
    hash_map: dict[str, list[dict[str, str]]],
    baseline_pairs: set[tuple[str, str]],
    allowlist_prefixes: list[str],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """
    Compare staged files against the hash_map built from external-source-cache.
    Returns list of match dicts.
    """
    matches = []
    for filepath in staged_files:
        try:
            rel = str(filepath.relative_to(repo_root))
        except ValueError:
            rel = str(filepath)

        if _is_allowlisted(rel, allowlist_prefixes):
            continue

        # Skip symlinks pointing into packages/ (lib-symlink identity rule)
        if filepath.is_symlink():
            target = filepath.resolve()
            packages_dir = repo_root / "packages"
            if packages_dir.exists() and str(target).startswith(str(packages_dir)):
                continue

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        units = _extract_top_level_units(source, str(filepath))
        for unit in units:
            h = unit["hash"]
            if h not in hash_map:
                continue
            upstream_hits = hash_map[h]
            classification = "exact-AST"
            for upstream in upstream_hits:
                pair = (rel, h)
                if pair in baseline_pairs:
                    classification = "exact-AST (baselined)"
                matches.append(
                    {
                        "cos_file": rel,
                        "cos_unit": unit["name"],
                        "cos_lineno": unit["lineno"],
                        "cache_file": upstream["file"],
                        "cache_unit": upstream["name"],
                        "ast_hash": h,
                        "classification": classification,
                    }
                )
    return matches


# ── Output formatters ──────────────────────────────────────────────────────────


def _format_text(matches: list[dict[str, Any]], new_count: int) -> str:
    if not matches:
        return "ast-similarity: no matches found."
    lines = [f"ast-similarity: {len(matches)} match(es) ({new_count} new):"]
    for m in matches:
        tag = " [BASELINED]" if "baselined" in m["classification"] else " [NEW]"
        lines.append(
            f"  {m['cos_file']}:{m['cos_lineno']} {m['cos_unit']}"
            f" <- {m['cache_file']} {m['cache_unit']}"
            f" [{m['classification']}]{tag}"
        )
    return "\n".join(lines)


def _format_json(matches: list[dict[str, Any]], new_count: int) -> str:
    return json.dumps(
        {"matches": matches, "total": len(matches), "new_hits": new_count}, indent=2
    )


def _format_markdown(matches: list[dict[str, Any]], new_count: int) -> str:
    lines = [
        f"## AST Similarity Scan — {len(matches)} match(es) ({new_count} new)\n",
        "| COS File | Unit | Cache File | Cache Unit | Hash | Classification |",
        "|---|---|---|---|---|---|",
    ]
    for m in matches:
        lines.append(
            f"| {m['cos_file']} | {m['cos_unit']} | {m['cache_file']}"
            f" | {m['cache_unit']} | `{m['ast_hash'][:12]}…` | {m['classification']} |"
        )
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ADR-271 Tier 2 AST similarity detector"
    )
    parser.add_argument(
        "--baseline", action="store_true", help="Write matches to baseline manifest"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        default=True,
        help="Staged files only (default; flag kept for hook compatibility)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    parser.add_argument("--allowlist", default=None, help="Path to allowlist file")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Exit 1 on any non-baseline match (same as default behaviour)",
    )
    args = parser.parse_args(argv)

    repo_root = ROOT_DIR

    # Check cache dir
    if not CACHE_DIR.exists() or not any(CACHE_DIR.rglob("*.py")):
        if args.format == "json":
            print(
                json.dumps(
                    {"matches": [], "total": 0, "new_hits": 0, "skipped": "no cache"}
                )
            )
        else:
            print("ast-similarity: external-source-cache is empty — nothing to compare.")
        return 0

    # Load / build index
    index = _load_or_build_index(CACHE_DIR)
    hash_map = _flat_hash_map(index)

    # Load baseline
    baseline_pairs = _load_baseline_pairs(BASELINE_FILE)

    # Load allowlist
    allowlist_prefixes = _load_allowlist(args.allowlist)

    # Get staged files
    staged_files = _get_staged_python_files(repo_root)

    if not staged_files:
        if args.format == "json":
            print(json.dumps({"matches": [], "total": 0, "new_hits": 0}))
        else:
            print("ast-similarity: no staged Python files.")
        return 0

    # Scan
    matches = scan(staged_files, hash_map, baseline_pairs, allowlist_prefixes, repo_root)

    # Partition new vs baselined
    new_matches = [m for m in matches if "baselined" not in m["classification"]]
    new_count = len(new_matches)

    # Output
    if args.format == "json":
        print(_format_json(matches, new_count))
    elif args.format == "markdown":
        print(_format_markdown(matches, new_count))
    else:
        print(_format_text(matches, new_count))

    # Baseline mode
    if args.baseline:
        _write_baseline(matches, repo_root)
        return 0

    # Block on new matches
    if new_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
