"""Enforce rule: Python scripts use snake_case filenames.

See rules/python-naming.md.

Hyphens in Python filenames break pytest collection and require importlib hacks.
All Python scripts in scripts/, lib/, and packages/*/lib/ must use underscores.
"""
from pathlib import Path
import pytest

REPO = Path(__file__).parent.parent.parent

# Historical executable audit/benchmark entrypoints kept hyphenated because
# manifests, ADR receipts, and operator docs refer to those CLI paths. New Python
# modules must still use snake_case filenames.
HYphenated_SCRIPT_ALLOWLIST = {
    "agent-orchestration-benchmark.py",
    "agent-orchestration-boundary-audit.py",
    "primitive-behavior-audit.py",
    "primitive-coherence-audit.py",
    "skill-router-benchmark.py",
    "skill-router-retrieval-audit.py",
}


@pytest.mark.audit
def test_scripts_are_snake_case():
    hits = [path for path in (REPO / "scripts").glob("*-*.py") if path.name not in HYphenated_SCRIPT_ALLOWLIST]
    assert not hits, (
        f"Python scripts MUST use snake_case filenames (see rules/python-naming.md). "
        f"Hyphenated files found: {[h.name for h in hits]}"
    )


@pytest.mark.audit
def test_lib_is_snake_case():
    hits = list((REPO / "lib").glob("*-*.py"))
    assert not hits, (
        f"lib/*.py MUST use snake_case filenames (see rules/python-naming.md). "
        f"Hyphenated files found: {[h.name for h in hits]}"
    )


@pytest.mark.audit
def test_packages_lib_is_snake_case():
    """Check packages/*/lib/*.py — any package lib Python files must use snake_case."""
    hits = []
    for lib_dir in (REPO / "packages").glob("*/lib"):
        if lib_dir.is_dir():
            hits.extend(lib_dir.glob("*-*.py"))
    assert not hits, (
        f"packages/*/lib/*.py MUST use snake_case filenames (see rules/python-naming.md). "
        f"Hyphenated files found: {[str(h.relative_to(REPO)) for h in hits]}"
    )
