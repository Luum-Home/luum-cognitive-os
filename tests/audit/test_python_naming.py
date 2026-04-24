"""Enforce rule: Python scripts use snake_case filenames.

See rules/python-naming.md.

Hyphens in Python filenames break pytest collection and require importlib hacks.
All Python scripts in scripts/, lib/, and packages/*/lib/ must use underscores.
"""
from pathlib import Path
import pytest

REPO = Path(__file__).parent.parent.parent


@pytest.mark.audit
def test_scripts_are_snake_case():
    hits = list((REPO / "scripts").glob("*-*.py"))
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
