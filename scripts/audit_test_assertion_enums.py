#!/usr/bin/env python3
# SCOPE: os-only
"""Find tests that ASSERT a value outside a closed enum declared in a manifest.

The failure mode this catches is not a missing test — it is a test that
certifies a defect.  While the product emits the bogus value the test is green;
the day someone repairs the product the test turns red, and the red accuses the
FIX rather than the test.  That is why the class survives normal review: a test
defending a bug is indistinguishable from a correct one for as long as the bug
lives.

The one signal that is decidable without running anything: the test states, as
the expected answer, a value that the closed enum does not contain.  On
2026-08-19 two suites asserted ``permissionDecision == "block"`` — a value no
harness accepts — and the branch under them failed open on all 11.493 runs.

WHAT COUNTS AS AN ASSERTION (and what does not)
    flagged      assert hso["permissionDecision"] == "block"
    flagged      assert hso.get("permissionDecision") in ("block", "allow")
    flagged      self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "block")
    flagged      d = hso["permissionDecision"]; assert d == "block"     (local alias)
    NOT flagged  a bash/JSON fixture string that contains permissionDecision:"block"
    NOT flagged  '"permissionDecision": "block"' in hook_source          (a detector)
    NOT flagged  a docstring or comment describing the historical bug
The distinction is the reason this is an AST pass and not a grep: a test that
FEEDS an invalid value to something is honest work, and greps cannot tell it
apart from a test that CLAIMS the invalid value is right.

Read-only.  Deterministic.  Changes nothing, so it restores nothing.

Exit codes: 0 = no findings, 1 = findings, 2 = error.

Usage:
    scripts/audit_test_assertion_enums.py
    scripts/audit_test_assertion_enums.py --json
    scripts/audit_test_assertion_enums.py --root /path/to/tree
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import warnings
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on a broken env
    print("audit_test_assertion_enums: PyYAML is required", file=sys.stderr)
    raise SystemExit(2)

REGISTRY_RELPATH = "manifests/test-assertion-enums.yaml"

_EQ_OPS = (ast.Eq, ast.NotEq)
_IN_OPS = (ast.In, ast.NotIn)
_UNITTEST_EQ = {"assertEqual", "assertNotEqual", "assertEquals"}
_UNITTEST_IN = {"assertIn", "assertNotIn"}


class RegistryError(RuntimeError):
    """The registry or the manifest it points at cannot be read as declared."""


def _resolve_pointer(doc: Any, pointer: str, where: str) -> list[str]:
    node: Any = doc
    for part in pointer.split("."):
        if not isinstance(node, dict) or part not in node:
            raise RegistryError(f"{where}: pointer {pointer!r} does not resolve at {part!r}")
        node = node[part]
    if not isinstance(node, list) or not node or not all(isinstance(v, str) for v in node):
        raise RegistryError(f"{where}: pointer {pointer!r} is not a non-empty list of strings")
    return list(node)


def load_enums(root: Path, registry_path: Path | None = None) -> list[dict[str, Any]]:
    """Read the registry and pull each enum's values FROM ITS SOURCE manifest.

    Values are never stored in the registry, so the registry cannot drift away
    from the contract it points at.
    """
    reg_path = registry_path or (root / REGISTRY_RELPATH)
    if not reg_path.is_file():
        raise RegistryError(f"registry not found: {reg_path}")
    registry = yaml.safe_load(reg_path.read_text(encoding="utf-8")) or {}
    entries = registry.get("enums") or []
    if not isinstance(entries, list) or not entries:
        raise RegistryError(f"{reg_path}: `enums` must be a non-empty list")

    resolved: list[dict[str, Any]] = []
    for entry in entries:
        for key in ("id", "field", "source", "pointer", "scan_globs", "rationale"):
            if not entry.get(key):
                raise RegistryError(f"{reg_path}: enum {entry.get('id', '?')!r} is missing {key!r}")
        if "values" in entry:
            raise RegistryError(
                f"{reg_path}: enum {entry['id']!r} inlines `values`; the registry must "
                "read them from `source`/`pointer` so it cannot drift from the contract"
            )
        source = root / entry["source"]
        if not source.is_file():
            raise RegistryError(f"{reg_path}: enum {entry['id']!r} source not found: {source}")
        doc = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        values = _resolve_pointer(doc, entry["pointer"], f"{entry['source']}")
        resolved.append({**entry, "values": values})
    return resolved


class _AssertionScanner(ast.NodeVisitor):
    """Collect (line, field, asserted_value) for every enum-field assertion."""

    def __init__(self, fields: set[str]) -> None:
        self.fields = fields
        self.hits: list[tuple[int, str, str]] = []
        self._alias_stack: list[dict[str, str]] = [{}]

    # -- scope handling: aliases are local to the function that created them ---
    def _enter_scope(self, node: ast.AST) -> None:
        self._alias_stack.append({})
        self.generic_visit(node)
        self._alias_stack.pop()

    visit_FunctionDef = _enter_scope
    visit_AsyncFunctionDef = _enter_scope
    visit_Lambda = _enter_scope

    # -- field resolution ------------------------------------------------------
    def _field_of(self, node: ast.AST) -> str | None:
        """Return the enum field this expression READS, or None.

        Only real key accesses count.  A string literal that merely contains the
        field name is a payload being built or searched, never an assertion.
        """
        if isinstance(node, ast.Subscript):
            key = node.slice
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                if key.value in self.fields:
                    return key.value
            return None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "get" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    if first.value in self.fields:
                        return first.value
            return None
        if isinstance(node, ast.Name):
            for scope in reversed(self._alias_stack):
                if node.id in scope:
                    return scope[node.id]
        return None

    @staticmethod
    def _str_of(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    @staticmethod
    def _str_seq_of(node: ast.AST) -> list[str] | None:
        if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return None
        out = []
        for elt in node.elts:
            if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                return None  # not a literal set of strings; unknowable statically
            out.append(elt.value)
        return out or None

    # -- alias capture ---------------------------------------------------------
    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            field = self._field_of(node.value)
            if field and isinstance(node.value, (ast.Subscript, ast.Call)):
                self._alias_stack[-1][node.targets[0].id] = field
        self.generic_visit(node)

    # -- the two assertion shapes ---------------------------------------------
    def visit_Compare(self, node: ast.Compare) -> None:
        if len(node.ops) == 1:
            op, right = node.ops[0], node.comparators[0]
            if isinstance(op, _EQ_OPS):
                for a, b in ((node.left, right), (right, node.left)):
                    field = self._field_of(a)
                    literal = self._str_of(b)
                    if field and literal is not None:
                        self.hits.append((node.lineno, field, literal))
                        break
            elif isinstance(op, _IN_OPS):
                field = self._field_of(node.left)
                seq = self._str_seq_of(right)
                if field and seq:
                    for literal in seq:
                        self.hits.append((node.lineno, field, literal))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if name in _UNITTEST_EQ and len(node.args) >= 2:
            for a, b in ((node.args[0], node.args[1]), (node.args[1], node.args[0])):
                field = self._field_of(a)
                literal = self._str_of(b)
                if field and literal is not None:
                    self.hits.append((node.lineno, field, literal))
                    break
        elif name in _UNITTEST_IN and len(node.args) >= 2:
            field = self._field_of(node.args[0])
            seq = self._str_seq_of(node.args[1])
            if field and seq:
                for literal in seq:
                    self.hits.append((node.lineno, field, literal))
        self.generic_visit(node)


def scan(root: Path, enums: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return (findings, files_scanned)."""
    by_field = {e["field"]: e for e in enums}
    files: dict[Path, set[str]] = {}
    for entry in enums:
        for pattern in entry["scan_globs"]:
            for path in sorted(root.glob(pattern)):
                if path.is_file():
                    files.setdefault(path, set()).add(entry["field"])

    findings: list[dict[str, Any]] = []
    for path, fields in sorted(files.items()):
        try:
            with warnings.catch_warnings():
                # A test file with a stray escape sequence is not this gate's business.
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise RegistryError(f"cannot parse {path}: {exc}") from exc
        scanner = _AssertionScanner(fields)
        scanner.visit(tree)
        for lineno, field, literal in scanner.hits:
            entry = by_field[field]
            if literal in entry["values"]:
                continue
            findings.append(
                {
                    "file": str(path.relative_to(root)),
                    "line": lineno,
                    "field": field,
                    "asserted": literal,
                    "allowed": entry["values"],
                    "enum_id": entry["id"],
                    "source": f"{entry['source']}:{entry['pointer']}",
                }
            )
    return findings, len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="tree to scan (default: cwd)")
    parser.add_argument("--registry", default=None, help="override registry path")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    registry = Path(args.registry).resolve() if args.registry else None
    try:
        enums = load_enums(root, registry)
        findings, scanned = scan(root, enums)
    except RegistryError as exc:
        print(f"audit_test_assertion_enums: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "files_scanned": scanned,
                    "enums": [{"id": e["id"], "field": e["field"], "values": e["values"]} for e in enums],
                    "findings": findings,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if findings else 0

    header = ", ".join(f"{e['field']}={'|'.join(e['values'])}" for e in enums)
    print(f"scanned {scanned} test file(s) for closed-enum assertions [{header}]")
    if not findings:
        print("no test asserts a value outside a registered closed enum")
        return 0
    print(f"\n{len(findings)} assertion(s) state a value the enum does not contain:\n")
    for f in findings:
        print(f"  {f['file']}:{f['line']}")
        print(f"    asserts {f['field']} == {f['asserted']!r}; allowed: {'|'.join(f['allowed'])}")
        print(f"    contract: {f['source']}")
    print(
        "\nA test asserting a value outside the enum does not fail — it CERTIFIES the\n"
        "defect. Fix the assertion against the contract, do not widen the enum."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
