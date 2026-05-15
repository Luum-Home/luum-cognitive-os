#!/usr/bin/env python3
# SCOPE: both
"""Test Quality Auditor — classifies every test function in tests/**/*.py.

Classification tiers
--------------------
BEHAVIORAL  — asserts side-effects: subprocess exit codes, JSONL rows written,
               state changes, return values of real functions.
STRUCTURAL  — asserts attribute values / dict membership / type checks / path
               existence only.  No side-effect verification.
TRIVIAL     — `assert True`, `assert x == x`, or has NO assertions at all.
MOCK-HEAVY  — > 50% of function-level calls are Mock/MagicMock/patch
               constructions and the only assertions are on mock objects.

Tier hierarchy (first match wins):
  TRIVIAL > MOCK-HEAVY > BEHAVIORAL > STRUCTURAL

Output
------
.cognitive-os/metrics/test-quality-audit.jsonl  — one JSON row per test function
stdout --summary                                 — tier count table

Usage
-----
    python3 scripts/cos_test_quality_audit.py              # scan + write JSONL
    python3 scripts/cos_test_quality_audit.py --summary    # scan + print table
    python3 scripts/cos_test_quality_audit.py --file tests/unit/foo.py
    python3 scripts/cos_test_quality_audit.py --help
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
TESTS_DIR = ROOT / "tests"
METRICS_DIR = ROOT / ".cognitive-os" / "metrics"
OUTPUT_FILE = METRICS_DIR / "test-quality-audit.jsonl"
REPORTS_DIR = ROOT / ".cognitive-os" / "reports" / "test-quality"

# Calls that indicate structural-only checks (no behaviour)
_STRUCTURAL_CALL_ATTRS = frozenset({
    "exists", "is_file", "is_dir", "is_symlink",
    "isfile", "isdir", "islink", "isabs",
})

# Assertion helper method names that are unambiguously behavioural
_BEHAVIOURAL_ASSERT_METHODS = frozenset({
    "assertEqual", "assertNotEqual",
    "assertRaises", "assertRaisesRegex",
    "assertWarns",
    "assertLogs",
    "assertAlmostEqual", "assertNotAlmostEqual",
    "assertGreater", "assertGreaterEqual",
    "assertLess", "assertLessEqual",
    "assertRegex", "assertNotRegex",
    "assertIn", "assertNotIn",
    "assertIsInstance", "assertNotIsInstance",
    "assertIsNone", "assertIsNotNone",
    "assert_called_with", "assert_called_once_with",
    "assert_any_call", "assert_called", "assert_not_called",
    "assert_called_once",
})

# Calls whose presence is a strong signal of side-effect verification
_BEHAVIOURAL_SIGNAL_CALLS = frozenset({
    "subprocess", "run", "check_output", "check_call", "Popen",
    "open",           # file I/O
    "write", "read",
    "json", "loads", "dumps",
    "Path",           # path construction followed by asserts
    "raises",         # pytest.raises(...)
})

# Names that indicate trivial / no-op assertions
_TRIVIAL_CONST_ASSERT: tuple[type, ...] = (ast.Constant,)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

TIER_BEHAVIORAL = "BEHAVIORAL"
TIER_STRUCTURAL = "STRUCTURAL"
TIER_TRIVIAL = "TRIVIAL"
TIER_MOCK_HEAVY = "MOCK-HEAVY"


@dataclass
class TestRecord:
    file: str
    function: str
    line: int
    tier: str
    assertions: int
    mock_calls: int
    total_calls: int
    reason: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _iter_func_nodes(func: ast.FunctionDef) -> list[ast.AST]:
    """Walk all nodes inside a function (but NOT nested function definitions)."""
    result: list[ast.AST] = []
    for node in ast.walk(func):
        if node is not func and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # skip nested functions
        result.append(node)
    return result


def _count_mock_constructions(nodes: list[ast.AST]) -> int:
    """Count Mock/MagicMock/patch calls + @patch decorators in a function's body."""
    count = 0
    for node in nodes:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr in ("Mock", "MagicMock", "patch", "create_autospec"):
                    count += 1
            elif isinstance(func, ast.Name):
                if func.id in ("Mock", "MagicMock", "patch", "create_autospec"):
                    count += 1
    return count


def _count_total_calls(nodes: list[ast.AST]) -> int:
    return sum(1 for n in nodes if isinstance(n, ast.Call))


def _get_assertions(nodes: list[ast.AST]) -> list[ast.AST]:
    """Return all assert statements, assertX() call nodes, and pytest.raises uses."""
    result: list[ast.AST] = []
    for node in nodes:
        if isinstance(node, ast.Assert):
            result.append(node)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr in _BEHAVIOURAL_ASSERT_METHODS:
                    result.append(node)
                elif func.attr == "raises":
                    # pytest.raises(...) used as context manager — counts as a behavioural check
                    result.append(node)
    return result


# ---------------------------------------------------------------------------
# Assertion analysis
# ---------------------------------------------------------------------------

def _is_trivially_true(assert_node: ast.Assert) -> bool:
    """True for `assert True`, `assert 1`, `assert "x"`, etc."""
    test = assert_node.test
    if isinstance(test, ast.Constant):
        return bool(test.value)  # assert True / assert 1
    # assert x == x  (same name on both sides)
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
        if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name):
            return test.left.id == test.comparators[0].id
    return False


def _assert_is_structural(node: ast.Assert) -> bool:
    """Return True when an assert only checks existence / membership / type."""
    return _expr_is_structural(node.test)


def _expr_is_structural(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _STRUCTURAL_CALL_ATTRS:
            return True
        if isinstance(func, ast.Name) and func.id in ("isinstance", "issubclass"):
            return True  # type-check only
        return False

    if isinstance(node, ast.Compare):
        # `x in container` — membership check
        for op in node.ops:
            if isinstance(op, ast.In):
                return True
        # comparisons like `x == "value"` or `len(x) == 3` are structural
        # unless the left side is something interesting
        if isinstance(node.left, ast.Call):
            # len(x) == N  → structural length check
            func = node.left.func
            if isinstance(func, ast.Name) and func.id == "len":
                return True
        return False

    if isinstance(node, ast.BoolOp):
        return all(_expr_is_structural(v) for v in node.values)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _expr_is_structural(node.operand)

    if isinstance(node, ast.Attribute) and node.attr in _STRUCTURAL_CALL_ATTRS:
        return True

    return False


def _has_behavioural_assertion(nodes: list[ast.AST]) -> bool:
    """Return True if the test body has at least one clearly behavioural assertion."""
    for node in nodes:
        # pytest.raises(...)  context manager usage
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "raises":
                return True
            if isinstance(func, ast.Attribute) and func.attr in _BEHAVIOURAL_ASSERT_METHODS:
                return True

        if isinstance(node, ast.Assert):
            if not _assert_is_structural(node) and not _is_trivially_true(node):
                return True

    return False


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_function(func: ast.FunctionDef, file_path: str) -> TestRecord:
    """Classify a single test function and return a TestRecord."""
    nodes = _iter_func_nodes(func)
    assertions = _get_assertions(nodes)
    mock_count = _count_mock_constructions(nodes)
    call_count = _count_total_calls(nodes)

    n_assertions = len(assertions)

    # --- TRIVIAL: no assertions OR only `assert True` / `assert x == x` ----
    if n_assertions == 0:
        # Exception: "no crash" / "does not raise" tests are behavioural by intent.
        # Names like test_*_no_crash, test_*_does_not_raise, test_*_survives_*,
        # test_*_silently_*, test_*_no_raise, test_*_does_not_crash are OK.
        _no_crash_suffixes = (
            "_no_crash", "_does_not_raise", "_no_raise",
            "_silently", "_survives_", "_no_exception",
            "_does_not_crash",
        )
        is_no_crash = any(
            s in func.name for s in _no_crash_suffixes
        )
        # Also: body contains try/except block that calls pytest.fail() on exception
        has_try_fail = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in ("fail", "skip")
            for n in nodes
        )
        # Also: function body uses `raise` to signal failure (smoke-test pattern)
        has_conditional_raise = any(
            isinstance(n, ast.Raise) and n.exc is not None
            for n in nodes
        )
        if is_no_crash or has_try_fail or has_conditional_raise:
            return TestRecord(
                file=file_path,
                function=func.name,
                line=func.lineno,
                tier=TIER_BEHAVIORAL,
                assertions=0,
                mock_calls=mock_count,
                total_calls=call_count,
                reason="no-crash/exception-safety or raise-on-failure test (behavioural by pattern)",
            )

        return TestRecord(
            file=file_path,
            function=func.name,
            line=func.lineno,
            tier=TIER_TRIVIAL,
            assertions=0,
            mock_calls=mock_count,
            total_calls=call_count,
            reason="no assertions",
        )

    all_trivial = all(
        isinstance(a, ast.Assert) and _is_trivially_true(a)
        for a in assertions
        if isinstance(a, ast.Assert)
    )
    # pytest.raises counts as behavioural — never trivial
    has_raises = any(
        isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and a.func.attr == "raises"
        for a in assertions
    )
    if all_trivial and all(isinstance(a, ast.Assert) for a in assertions) and not has_raises:
        return TestRecord(
            file=file_path,
            function=func.name,
            line=func.lineno,
            tier=TIER_TRIVIAL,
            assertions=n_assertions,
            mock_calls=mock_count,
            total_calls=call_count,
            reason="only trivial assertions (assert True / assert x==x)",
        )

    # --- MOCK-HEAVY: >50% calls are mock constructions ----------------------
    if call_count > 0 and mock_count / call_count > 0.5 and n_assertions > 0:
        # Check if every assertion is on a Mock attribute
        only_mock_asserts = all(
            (
                isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
                and a.func.attr in {"assert_called_with", "assert_called_once_with",
                                    "assert_called", "assert_not_called", "assert_called_once",
                                    "assert_any_call"}
            ) or (
                isinstance(a, ast.Assert) and _assert_is_structural(a)
            )
            for a in assertions
        )
        if only_mock_asserts:
            return TestRecord(
                file=file_path,
                function=func.name,
                line=func.lineno,
                tier=TIER_MOCK_HEAVY,
                assertions=n_assertions,
                mock_calls=mock_count,
                total_calls=call_count,
                reason=f"{mock_count}/{call_count} calls are mock constructions, assertions only on mocks",
            )

    # --- BEHAVIORAL: has at least one real side-effect assertion ------------
    if _has_behavioural_assertion(nodes):
        return TestRecord(
            file=file_path,
            function=func.name,
            line=func.lineno,
            tier=TIER_BEHAVIORAL,
            assertions=n_assertions,
            mock_calls=mock_count,
            total_calls=call_count,
            reason="asserts real side-effects or return values",
        )

    # --- STRUCTURAL: only checks existence/membership/types -----------------
    return TestRecord(
        file=file_path,
        function=func.name,
        line=func.lineno,
        tier=TIER_STRUCTURAL,
        assertions=n_assertions,
        mock_calls=mock_count,
        total_calls=call_count,
        reason="only structural assertions (existence, membership, type checks)",
    )


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------

def _has_fixture_decorator(func: ast.FunctionDef) -> bool:
    """Return True if the function is decorated with @pytest.fixture."""
    for dec in func.decorator_list:
        # @pytest.fixture or @pytest.fixture(...)
        if isinstance(dec, ast.Attribute) and dec.attr == "fixture":
            return True
        if isinstance(dec, ast.Call):
            inner = dec.func
            if isinstance(inner, ast.Attribute) and inner.attr == "fixture":
                return True
    return False


def _has_skip_decorator(func: ast.FunctionDef) -> bool:
    """Return True if the function is fully skipped via @pytest.mark.skip."""
    for dec in func.decorator_list:
        if isinstance(dec, ast.Call):
            inner = dec.func
            # pytest.mark.skip(...)
            if (isinstance(inner, ast.Attribute) and inner.attr == "skip"):
                return True
    return False


def scan_file(path: Path, root: Path) -> list[TestRecord]:
    """Parse one file and classify all test_* functions."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    rel = str(path.relative_to(root))
    records: list[TestRecord] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("test_"):
                continue
            # Skip fixtures named test_* (unusual but happens)
            if _has_fixture_decorator(node):  # type: ignore[arg-type]
                continue
            # Skip-decorated stubs are placeholders, not real tests — mark as TRIVIAL
            # but with a clear label so they can be tracked separately
            if _has_skip_decorator(node):  # type: ignore[arg-type]
                is_empty_body = all(isinstance(s, (ast.Pass, ast.Expr)) for s in node.body)
                if is_empty_body:
                    rec = TestRecord(
                        file=rel,
                        function=node.name,
                        line=node.lineno,
                        tier=TIER_TRIVIAL,
                        assertions=0,
                        mock_calls=0,
                        total_calls=0,
                        reason="skipped placeholder test (empty body + @pytest.mark.skip)",
                    )
                    records.append(rec)
                    continue
            rec = classify_function(node, rel)  # type: ignore[arg-type]
            records.append(rec)

    return records


def scan_all(test_root: Path, root: Path) -> list[TestRecord]:
    """Recursively scan all test files."""
    records: list[TestRecord] = []
    for path in sorted(test_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.name.startswith("conftest"):
            continue
        records.extend(scan_file(path, root))
    return records


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_jsonl(records: list[TestRecord], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(asdict(rec)) + "\n")


def quality_summary(records: list[TestRecord]) -> dict[str, object]:
    from collections import Counter

    tier_counts: Counter[str] = Counter(r.tier for r in records)
    total = len(records)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "tiers": {tier: tier_counts.get(tier, 0) for tier in (TIER_BEHAVIORAL, TIER_STRUCTURAL, TIER_TRIVIAL, TIER_MOCK_HEAVY)},
        "blocking_count": tier_counts.get(TIER_TRIVIAL, 0) + tier_counts.get(TIER_MOCK_HEAVY, 0),
    }


def render_summary(records: list[TestRecord]) -> str:
    summary = quality_summary(records)
    tier_counts = summary["tiers"]
    total_value = summary["total"]
    total = int(total_value) if isinstance(total_value, int | float | str | bytes | bytearray) else 0
    lines: list[str] = []

    tiers = [TIER_BEHAVIORAL, TIER_STRUCTURAL, TIER_TRIVIAL, TIER_MOCK_HEAVY]
    lines.append("")
    lines.append(f"Test Quality Audit — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    lines.append(f"{'='*55}")
    lines.append(f"{'Tier':<14} {'Count':>7}  {'%':>6}  {'Meaning'}")
    lines.append(f"{'-'*55}")
    for tier in tiers:
        cnt = tier_counts.get(tier, 0)  # type: ignore[union-attr]
        pct = cnt / total * 100 if total else 0
        meaning = {
            TIER_BEHAVIORAL: "A — keep (verifies side-effects)",
            TIER_STRUCTURAL: "B — acceptable (metadata/config)",
            TIER_MOCK_HEAVY: "C — rewrite (mocked business logic)",
            TIER_TRIVIAL:    "D — delete or rewrite (no real check)",
        }[tier]
        lines.append(f"{tier:<14} {cnt:>7}  {pct:>5.1f}%  {meaning}")
    lines.append(f"{'-'*55}")
    lines.append(f"{'TOTAL':<14} {total:>7}")

    # Top worst offenders
    bad = [r for r in records if r.tier in (TIER_TRIVIAL, TIER_MOCK_HEAVY)]
    if bad:
        lines.append(f"\nTop 20 Tier C/D offenders:")
        lines.append(f"{'File':<60} {'Line':>5}  {'Function':<40}  {'Reason'}")
        lines.append("-" * 120)
        for r in sorted(bad, key=lambda r: (r.tier, r.file, r.line))[:20]:
            lines.append(f"{r.file:<60} {r.line:>5}  {r.function:<40}  {r.reason}")
    return "\n".join(lines) + "\n"


def print_summary(records: list[TestRecord]) -> None:
    print(render_summary(records), end="")


def write_report_artifacts(records: list[TestRecord], reports_dir: Path = REPORTS_DIR) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = reports_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.txt").write_text(render_summary(records), encoding="utf-8")
    (run_dir / "quality.json").write_text(
        json.dumps(quality_summary(records), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    latest = reports_dir / "latest"
    if latest.exists() or latest.is_symlink():
        if latest.is_dir() and not latest.is_symlink():
            return run_dir
        latest.unlink()
    try:
        latest.symlink_to(run_dir, target_is_directory=True)
    except OSError:
        pass
    return run_dir


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--summary", action="store_true", help="Print tier counts to stdout")
    parser.add_argument("--file", metavar="PATH", help="Scan a single file instead of all tests")
    parser.add_argument("--no-write", action="store_true", help="Skip writing JSONL output")
    parser.add_argument("--no-artifact", action="store_true", help="Skip writing persisted report artifacts")
    parser.add_argument("--artifact-dir", metavar="PATH", help="Override persisted report artifact directory")
    args = parser.parse_args()

    root = ROOT

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = Path.cwd() / path
        records = scan_file(path, root)
    else:
        records = scan_all(TESTS_DIR, root)

    if not args.no_write:
        write_jsonl(records, OUTPUT_FILE)
        print(f"Wrote {len(records)} records to {OUTPUT_FILE}", file=sys.stderr)

    if not args.no_artifact:
        reports_dir = Path(args.artifact_dir) if args.artifact_dir else REPORTS_DIR
        run_dir = write_report_artifacts(records, reports_dir)
        print(f"Wrote test quality artifacts to {run_dir}", file=sys.stderr)

    if args.summary:
        print_summary(records)

    return 0


if __name__ == "__main__":
    sys.exit(main())
