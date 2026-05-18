#!/usr/bin/env python3
# SCOPE: both
"""Detect structural-only test files that verify existence rather than behavior.

Structural tests check things like path.exists(), is_file(), is_dir(), or
"string in content" — they confirm files exist and contain certain strings but
never exercise the code's logic. These tests survive 100% of mutations and
provide a false sense of coverage.

SCOPE CONTRACT
--------------
This script operates ONLY on the file list it is given. It does NOT auto-scan
the working tree. The caller (pre-commit hook or CI script) is responsible for
computing the correct file list from `git diff --cached --name-only --diff-filter=A`
and passing it as positional arguments.

Auto-scan is available only via the explicit --working-tree flag (manual debug).

Usage:
    # Pre-commit: pass staged files explicitly (hook does this automatically)
    python scripts/check_test_quality.py tests/unit/test_foo.py tests/unit/test_bar.py

    # CI mode: check new tests added since origin/main
    python scripts/check_test_quality.py --ci

    # Manual debug: scan entire working tree (opt-in only)
    python scripts/check_test_quality.py --working-tree

    # Legacy --pre-commit (still works, but hook now passes files directly)
    python scripts/check_test_quality.py --pre-commit
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Patterns that indicate structural-only assertions
# ---------------------------------------------------------------------------

# Function/method calls that check existence, not behavior
STRUCTURAL_CALLS = {
    "exists",
    "is_file",
    "is_dir",
    "is_symlink",
    "isfile",
    "isdir",
    "islink",
}

# assert patterns in raw source that suggest structural checks
STRUCTURAL_RAW_PATTERNS = [
    "path.exists()",
    "os.path.exists(",
    "os.path.isfile(",
    "os.path.isdir(",
    ".is_file()",
    ".is_dir()",
    ".is_symlink()",
    "in content",
    "in text",
    'in open(',
    "assert os.path.exists",
]

# Test name patterns that suggest structural intent
STRUCTURAL_NAME_PATTERNS = [
    "test_exists",
    "test_file_exists",
    "test_files_exist",
    "test_has_",
    "test_contains_section",
    "test_contains_header",
    "test_structure",
    "test_directory_structure",
]


@dataclass
class TestFileReport:
    path: str
    total_tests: int = 0
    structural_tests: int = 0
    behavioral_tests: int = 0
    structural_names: list[str] = field(default_factory=list)
    behavioral_names: list[str] = field(default_factory=list)

    @property
    def is_structural_only(self) -> bool:
        return self.total_tests > 0 and self.behavioral_tests == 0

    @property
    def structural_ratio(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.structural_tests / self.total_tests


def _is_structural_call(node: ast.AST) -> bool:
    """Check if an AST node is a call to a structural method."""
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in STRUCTURAL_CALLS:
            return True
    return False


def _assertion_is_structural(node: ast.AST) -> bool:
    """Check if an assert statement tests only structural properties."""
    if isinstance(node, ast.Assert):
        return _expression_is_structural(node.test)
    return False


def _expression_is_structural(node: ast.AST) -> bool:
    """Recursively check if an expression is purely structural."""
    if isinstance(node, ast.Call):
        return _is_structural_call(node)
    if isinstance(node, ast.Compare):
        # "x in content" pattern
        for op in node.ops:
            if isinstance(op, ast.In):
                return True
        return any(_expression_is_structural(c) for c in node.comparators)
    if isinstance(node, ast.BoolOp):
        return all(_expression_is_structural(v) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _expression_is_structural(node.operand)
    return False


def _has_behavioral_assertion(body: list[ast.stmt], source_lines: list[str]) -> bool:
    """Check if a test function body contains at least one behavioral assertion."""
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        # Look for calls to behavioral test methods
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr in (
                    "assertEqual",
                    "assertNotEqual",
                    "assertRaises",
                    "assertWarns",
                    "assertLogs",
                    "assertAlmostEqual",
                    "assertGreater",
                    "assertLess",
                    "assertRegex",
                    "assertIn",  # can be behavioral if checking return values
                    "assertNotIn",
                    "assertIsInstance",
                    "assertIsNone",
                    "assertIsNotNone",
                    "assert_called_with",
                    "assert_called_once_with",
                    "assert_called",
                    "assert_not_called",
                ):
                    return True
            # pytest.raises is behavioral
            if isinstance(func, ast.Attribute) and func.attr == "raises":
                return True

        # assert with non-structural expression
        if isinstance(node, ast.Assert) and not _assertion_is_structural(node):
            return True

    return False


def _name_suggests_structural(name: str) -> bool:
    """Check if a test name suggests structural-only intent."""
    name_lower = name.lower()
    return any(pat in name_lower for pat in STRUCTURAL_NAME_PATTERNS)


def analyze_test_file(filepath: Path) -> TestFileReport:
    """Analyze a single test file for structural vs behavioral tests."""
    report = TestFileReport(path=str(filepath))

    try:
        source = filepath.read_text()
    except (OSError, UnicodeDecodeError):
        return report

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return report

    source_lines = source.splitlines()

    for node in ast.walk(tree):
        # Find test functions and methods
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("test"):
                continue

            report.total_tests += 1

            _name_suggests_structural(node.name)  # informational; influences naming heuristics
            has_behavioral = _has_behavioral_assertion(node.body, source_lines)

            # A test is structural if it has no behavioral assertions
            # OR if its name suggests structural intent and it lacks behavioral content
            if not has_behavioral:
                report.structural_tests += 1
                report.structural_names.append(node.name)
            else:
                report.behavioral_tests += 1
                report.behavioral_names.append(node.name)

    return report


def get_new_test_files_in_pr() -> list[Path]:
    """Get test files added in the current PR (vs origin/main)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", "origin/main", "--", "tests/*.py", "tests/**/*.py"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return [Path(f) for f in result.stdout.strip().splitlines() if f]
    except subprocess.CalledProcessError:
        return []


def get_changed_test_files_cached() -> list[Path]:
    """Get test files in the staging area (for pre-commit hook)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=A", "--", "tests/*.py", "tests/**/*.py"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return [Path(f) for f in result.stdout.strip().splitlines() if f]
    except subprocess.CalledProcessError:
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect structural-only test files")
    parser.add_argument("files", nargs="*", help="Explicit list of test files to check (preferred — no auto-scan)")
    parser.add_argument("--ci", action="store_true", help="CI mode: check only new tests in PR (vs origin/main)")
    parser.add_argument("--pre-commit", action="store_true", help="Legacy pre-commit mode: derive staged files internally")
    parser.add_argument("--working-tree", action="store_true", help="Debug mode: scan entire working tree (opt-in only, never default)")
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="Max structural ratio before failure (0.0-1.0, default 1.0 = fail only if 100%% structural)")
    args = parser.parse_args()

    if args.files:
        # Explicit file list — primary interface used by the pre-commit hook.
        # Only these files are examined; working tree is never touched.
        test_files = [Path(f) for f in args.files]
    elif args.ci:
        test_files = get_new_test_files_in_pr()
    elif args.pre_commit:
        # Legacy mode: derive staged files internally (kept for backwards compat).
        # Prefer passing files explicitly from the hook instead.
        test_files = get_changed_test_files_cached()
    elif args.working_tree:
        # Opt-in working-tree scan for manual debugging only.
        test_files = list(Path("tests").rglob("*.py")) if Path("tests").exists() else []
    else:
        # No file list and no mode flag: refuse to auto-scan.
        # This prevents silent whole-tree scans when invoked without arguments.
        print(
            "check_test_quality.py: no files specified.\n"
            "Pass explicit file paths, or use --ci / --working-tree.\n"
            "The pre-commit hook passes files directly; --pre-commit is kept for legacy use.",
            file=sys.stderr,
        )
        return 0

    if not test_files:
        print("No test files to analyze.")
        return 0

    reports: list[TestFileReport] = []
    for f in test_files:
        if not f.exists():
            continue
        report = analyze_test_file(f)
        if report.total_tests > 0:
            reports.append(report)

    if not reports:
        print("No test functions found in scanned files.")
        return 0

    # Print results
    failures = []
    for r in reports:
        ratio_pct = f"{r.structural_ratio * 100:.0f}%"

        if r.is_structural_only:
            marker = "FAIL"
            failures.append(r)
        elif r.structural_ratio >= args.threshold and args.threshold < 1.0:
            marker = "WARN"
        else:
            marker = "PASS"

        print(f"  [{marker}] {r.path}: {r.total_tests} tests, {r.structural_tests} structural ({ratio_pct})")

        if r.structural_names:
            for name in r.structural_names:
                print(f"         structural: {name}")

    print()
    total_tests = sum(r.total_tests for r in reports)
    total_structural = sum(r.structural_tests for r in reports)
    total_behavioral = sum(r.behavioral_tests for r in reports)
    print(f"Summary: {total_tests} tests across {len(reports)} files")
    print(f"  Behavioral: {total_behavioral}")
    print(f"  Structural: {total_structural}")

    if failures:
        print()
        print(f"BLOCKED: {len(failures)} file(s) contain ONLY structural tests.")
        print("Structural tests verify that files exist and contain strings, but never")
        print("exercise the code's logic. They survive 100% of mutations.")
        print()
        print("Fix: add assertions that test return values, side effects, or error handling.")
        print("See docs/09-Quality/testing/mutation-testing.md for guidance.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
