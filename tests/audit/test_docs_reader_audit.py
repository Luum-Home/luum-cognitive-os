"""Hold ``scripts/docs_reader_audit.py`` at its measured zero-unread state.

The audit answers "who reads this doc?" for every file under ``docs/``. As of
2026-08-15 it reports 0 unread of 1348 audited, so the contract it enforces is
a genuine zero, not accepted debt — no baseline manifest is needed, and adding
one would only create room to drift.

This test executes the census and asserts its verdict. It does not import the
module and check it loads: ``scripts/aspirational_audit.py`` would count that
as coverage, which is exactly the cheap green this audit exists to prevent.
The ``total_audited`` guard is the important half — an audit that walks zero
docs also reports zero unread, and would otherwise pass forever.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "docs_reader_audit.py"


@pytest.fixture(scope="module")
def report() -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic path
        pytest.fail(f"docs_reader_audit emitted non-JSON: {exc}\nstderr:\n{proc.stderr}")


def test_census_actually_walks_the_docs_tree(report) -> None:
    """Guard against a zero-unread verdict produced by auditing nothing."""
    _, payload = report
    assert payload["schema"] == "docs-reader-audit/v1"
    assert payload["total_audited"] > 500, (
        f"docs census audited only {payload['total_audited']} docs -- the scope "
        f"collapsed, so its zero-unread verdict is meaningless"
    )
    assert len(payload["results"]) == payload["total_audited"]


def test_no_unreachable_docs(report) -> None:
    """Every doc under docs/ must be reachable from some surface."""
    code, payload = report
    unread = [r["doc"] for r in payload["results"] if r["verdict"] == "unread"]
    assert payload["unread"] == 0, (
        f"{payload['unread']} doc(s) are reachable from nowhere: {unread[:10]}. "
        f"Either link them from an index/consumer or delete them."
    )
    assert unread == []
    assert code == 0, "audit exits non-zero with zero unread docs"
