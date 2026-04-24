"""Tests for scripts/cos_test_quality_audit.py — classifier correctness.

Five tests, each verifying a different classification tier on a known snippet.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the auditor module without triggering its __main__ block
# ---------------------------------------------------------------------------

_AUDITOR_PATH = Path(__file__).parent.parent.parent / "scripts" / "cos_test_quality_audit.py"


def _load_auditor():
    """Import auditor as a module (avoids __main__ side-effects)."""
    spec = importlib.util.spec_from_file_location("cos_test_quality_audit", _AUDITOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Register under a stable name so dataclass __module__ resolves
    sys.modules["cos_test_quality_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_auditor()
classify_function = _mod.classify_function
TIER_BEHAVIORAL = _mod.TIER_BEHAVIORAL
TIER_STRUCTURAL = _mod.TIER_STRUCTURAL
TIER_TRIVIAL = _mod.TIER_TRIVIAL
TIER_MOCK_HEAVY = _mod.TIER_MOCK_HEAVY


def _parse_function(src: str) -> ast.FunctionDef:
    """Parse a single def and return the AST FunctionDef node."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            return node
    raise ValueError("No FunctionDef found in source")


# ---------------------------------------------------------------------------
# Test 1 — BEHAVIORAL: asserts subprocess exit code
# ---------------------------------------------------------------------------

def test_classifies_behavioral_subprocess_assert():
    """A test that asserts on a subprocess returncode is BEHAVIORAL."""
    src = """
def test_hook_exits_zero():
    import subprocess
    result = subprocess.run(["bash", "-n", "hooks/my-hook.sh"], capture_output=True)
    assert result.returncode == 0, "hook must be valid bash"
"""
    fn = _parse_function(src)
    record = classify_function(fn, "tests/unit/fake.py")
    assert record.tier == TIER_BEHAVIORAL, (
        f"Expected BEHAVIORAL for subprocess exit-code assertion, got {record.tier}"
    )
    assert record.assertions >= 1


# ---------------------------------------------------------------------------
# Test 2 — STRUCTURAL: only checks dict membership
# ---------------------------------------------------------------------------

def test_classifies_structural_membership_check():
    """A test that only checks 'key in dict' is STRUCTURAL."""
    src = """
def test_key_present():
    data = {"status": "ok", "count": 3}
    assert "status" in data
    assert "count" in data
"""
    fn = _parse_function(src)
    record = classify_function(fn, "tests/unit/fake.py")
    assert record.tier == TIER_STRUCTURAL, (
        f"Expected STRUCTURAL for membership-only checks, got {record.tier}"
    )


# ---------------------------------------------------------------------------
# Test 3 — TRIVIAL: assert True
# ---------------------------------------------------------------------------

def test_classifies_trivial_assert_true():
    """A test body with only 'assert True' is TRIVIAL."""
    src = """
def test_placeholder():
    result = some_function()
    assert True
"""
    fn = _parse_function(src)
    record = classify_function(fn, "tests/unit/fake.py")
    assert record.tier == TIER_TRIVIAL, (
        f"Expected TRIVIAL for 'assert True', got {record.tier}"
    )


# ---------------------------------------------------------------------------
# Test 4 — TRIVIAL: no assertions at all
# ---------------------------------------------------------------------------

def test_classifies_trivial_no_assertions():
    """A test with no assertions and no raise/skip is TRIVIAL."""
    src = """
def test_no_assertions():
    x = 1 + 1
    y = x * 2
"""
    fn = _parse_function(src)
    record = classify_function(fn, "tests/unit/fake.py")
    assert record.tier == TIER_TRIVIAL, (
        f"Expected TRIVIAL for a test with no assertions, got {record.tier}"
    )
    assert record.reason == "no assertions"


# ---------------------------------------------------------------------------
# Test 5 — BEHAVIORAL: pytest.raises as context manager
# ---------------------------------------------------------------------------

def test_classifies_behavioral_pytest_raises():
    """A test using pytest.raises(ValueError) is BEHAVIORAL — not TRIVIAL."""
    src = """
def test_raises_on_invalid_input():
    import pytest
    with pytest.raises(ValueError, match="invalid"):
        parse_value("not_a_number")
"""
    fn = _parse_function(src)
    record = classify_function(fn, "tests/unit/fake.py")
    assert record.tier == TIER_BEHAVIORAL, (
        f"Expected BEHAVIORAL for pytest.raises context manager, got {record.tier}. "
        f"Reason: {record.reason}"
    )
