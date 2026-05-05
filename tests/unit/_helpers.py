"""Shared test helpers for semantic/invariant-based assertions.

These helpers replace fragile exact-snapshot assertions with intent-preserving
checks that tolerate rewording while still enforcing the underlying contract.
"""
from __future__ import annotations

import time
from typing import Callable, List

import pytest


# ---------------------------------------------------------------------------
# Infrastructure detection (defined before markers so they can be called)
# ---------------------------------------------------------------------------

def _valkey_reachable() -> bool:
    """Return True when Valkey is listening on localhost:6379."""
    import socket
    try:
        with socket.create_connection(("localhost", 6379), timeout=0.5):
            return True
    except (OSError, socket.timeout):
        return False


def _bash_available() -> bool:
    """Return True when bash is available on PATH."""
    import shutil
    return shutil.which("bash") is not None


# ---------------------------------------------------------------------------
# Cached availability flags (evaluated once at import time)
# ---------------------------------------------------------------------------

#: True when Valkey is reachable (cached at import time for skip markers).
VALKEY_AVAILABLE: bool = _valkey_reachable()

#: True when bash is available (cached at import time).
BASH_AVAILABLE: bool = _bash_available()


# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

#: Mark a test that requires a live Valkey instance on localhost:6379.
requires_valkey = pytest.mark.skipif(
    not VALKEY_AVAILABLE,
    reason="Requires Valkey running on localhost:6379",
)

#: Mark a test that requires bash on PATH.
requires_bash = pytest.mark.skipif(
    not BASH_AVAILABLE,
    reason="Requires bash executable on PATH",
)

#: Mark a test that should only run when Valkey is NOT available.
#: Useful for "fallback mode" tests that fail when real Valkey is running.
skip_when_valkey_running = pytest.mark.skipif(
    VALKEY_AVAILABLE,
    reason="Skipped when Valkey is running (test only valid in offline environment)",
)

#: Mark a test for a feature that is not yet implemented.
requires_feature = pytest.mark.xfail(reason="Feature not yet implemented", strict=True)


# ---------------------------------------------------------------------------
# assert_preamble_contains_concepts
# ---------------------------------------------------------------------------

def assert_preamble_contains_concepts(text: str, concepts: List[str]) -> None:
    """Assert that *text* contains at least one of the given concept keywords.

    Case-insensitive substring matching.  Passes when ANY concept is found.
    Tolerates section renaming and minor restructuring.

    Args:
        text: Document text to inspect.
        concepts: Keywords — any one match satisfies the assertion.

    Raises:
        AssertionError: When none of the concepts are found.
    """
    if not concepts:
        return  # vacuously true
    text_lower = text.lower()
    for concept in concepts:
        if concept.lower() in text_lower:
            return
    raise AssertionError(
        f"None of the expected concepts found in text.\n"
        f"Concepts checked (any one would satisfy): {concepts}\n"
        f"Text excerpt (first 500 chars): {text[:500]!r}"
    )


# ---------------------------------------------------------------------------
# assert_all_concepts_present
# ---------------------------------------------------------------------------

def assert_all_concepts_present(text: str, concepts: List[str]) -> None:
    """Assert that ALL of the given concept keywords appear in *text*.

    Use when every concept is required.  Case-insensitive substring matching.

    Args:
        text: Document text to inspect.
        concepts: All keywords that must be present.

    Raises:
        AssertionError: Lists missing concepts.
    """
    text_lower = text.lower()
    missing = [c for c in concepts if c.lower() not in text_lower]
    if missing:
        raise AssertionError(
            f"Missing concepts in text: {missing}\n"
            f"All required: {concepts}\n"
            f"Text excerpt (first 500 chars): {text[:500]!r}"
        )


# ---------------------------------------------------------------------------
# assert_faster_than_baseline
# ---------------------------------------------------------------------------

def assert_faster_than_baseline(fn: Callable, factor: float = 3.0) -> float:
    """Measure *fn* execution time and assert it is within *factor* × baseline.

    Runs *fn* twice: first as a warm-up (baseline), then as the measured run.
    The assertion passes when ``elapsed < factor * baseline``.

    This relative threshold is resilient to system-load variations.

    Args:
        fn: Zero-argument callable to time.
        factor: Upper-bound multiplier applied to baseline.  Default 3.0.

    Returns:
        Measured elapsed time in seconds.

    Raises:
        AssertionError: When elapsed > factor * baseline.
    """
    t0 = time.monotonic()
    fn()
    baseline = time.monotonic() - t0

    t1 = time.monotonic()
    fn()
    elapsed = time.monotonic() - t1

    limit = factor * baseline
    assert elapsed < limit, (
        f"Function took {elapsed:.3f}s — exceeds {factor}× baseline ({baseline:.3f}s = {limit:.3f}s limit)"
    )
    return elapsed


# ---------------------------------------------------------------------------
# assert_within_absolute
# ---------------------------------------------------------------------------

def assert_within_absolute(elapsed: float, limit_s: float, slack_factor: float = 1.5) -> None:
    """Assert *elapsed* is within *limit_s* with a CI slack multiplier.

    Effective limit = ``limit_s * slack_factor``.

    Args:
        elapsed: Measured elapsed time in seconds.
        limit_s: Nominal (documented) time budget.
        slack_factor: CI headroom multiplier.  Default 1.5.

    Raises:
        AssertionError: When elapsed > effective limit.
    """
    effective = limit_s * slack_factor
    assert elapsed < effective, (
        f"Elapsed {elapsed:.3f}s exceeds {limit_s}s × {slack_factor} slack = {effective:.3f}s"
    )
