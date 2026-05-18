"""Tests for lib/reinvention_embeddings.py (ADR-039 Phase B-beta primitives).

Verifies:
1. embed() is deterministic (same text → same vector, always).
2. embed() returns unit-norm vectors (L2 ≈ 1.0).
3. cosine(embed(t), embed(t)) == 1.0 (self-similarity).
4. Rephrases of the same concept score HIGH (>= threshold).
5. Unrelated descriptions score LOW (< threshold).
6. cosine() raises ValueError on mismatched lengths.
7. embed("") returns zero vector (safe default).
8. IMPL_TYPE == "STUB" sentinel is present.
"""
from __future__ import annotations

import math
import sys
import os

import pytest

# Ensure project root is on path regardless of how pytest is invoked.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lib.reinvention_embeddings import (
    EMBED_DIM,
    DEFAULT_COSINE_THRESHOLD,
    IMPL_TYPE,
    cosine,
    embed,
)


# --------------------------------------------------------------------------- #
# Determinism                                                                  #
# --------------------------------------------------------------------------- #

def test_embed_is_deterministic():
    """Same text must produce identical vectors across calls."""
    text = "rate limiter token bucket flow control"
    v1 = embed(text)
    v2 = embed(text)
    assert v1 == v2, "embed() is not deterministic"


def test_embed_different_texts_differ():
    """Distinct texts must not produce identical vectors (collision)."""
    v1 = embed("rate limiter token bucket flow control")
    v2 = embed("agent heartbeat liveness pub sub bus")
    assert v1 != v2


# --------------------------------------------------------------------------- #
# Vector shape & norm                                                          #
# --------------------------------------------------------------------------- #

def test_embed_returns_correct_dimension():
    v = embed("some description")
    assert len(v) == EMBED_DIM


def test_embed_unit_norm():
    """embed() must return an L2-normalised vector (norm ≈ 1.0)."""
    v = embed("context compressor LLM summarization")
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-9, f"norm={norm} is not ~1.0"


def test_embed_empty_returns_zero_vector():
    """Empty string is a safe degenerate case — must not raise."""
    v = embed("")
    assert len(v) == EMBED_DIM
    assert all(x == 0.0 for x in v)


# --------------------------------------------------------------------------- #
# cosine() correctness                                                         #
# --------------------------------------------------------------------------- #

def test_cosine_self_similarity_is_one():
    """cosine(v, v) must be 1.0 for any non-zero vector."""
    v = embed("reinvention guard anti duplication check")
    score = cosine(v, v)
    assert abs(score - 1.0) < 1e-9, f"self-cosine={score}"


def test_cosine_symmetric():
    v1 = embed("session memory save recall")
    v2 = embed("cost governance budget per hour")
    assert abs(cosine(v1, v2) - cosine(v2, v1)) < 1e-12


def test_cosine_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="length mismatch"):
        cosine([1.0, 0.0], [1.0, 0.0, 0.0])


def test_cosine_zero_vector_returns_zero():
    """Zero vector → cosine 0.0 (no divide-by-zero crash)."""
    zero = [0.0] * EMBED_DIM
    v = embed("anything")
    assert cosine(zero, v) == 0.0
    assert cosine(v, zero) == 0.0


# --------------------------------------------------------------------------- #
# Semantic discrimination                                                      #
# --------------------------------------------------------------------------- #

# Pairs of (text_a, text_b) that are GENUINE semantic rewrites.
# The hashing-trick BOW stub scores these high because they share content tokens.
# Pairs are chosen to be robust to the BOW approximation (token overlap >= 50%).
_REPHRASE_PAIRS = [
    (
        "agent heartbeat liveness ping pub sub bus",
        "liveness heartbeat ping publish agent bus",
    ),
    (
        "session memory save recall engram storage",
        "engram storage save recall session memory",
    ),
    (
        "reinvention guard anti duplication check existing implementations",
        "check existing implementations reinvention anti duplication guard",
    ),
]

# Pairs of descriptions that are clearly DIFFERENT in meaning.
# The stub should score these well below DEFAULT_COSINE_THRESHOLD because
# they share few or no content tokens.
_UNRELATED_PAIRS = [
    (
        "rate limiter token bucket flow control agent",
        "machine learning gradient descent optimizer",
    ),
    (
        "agent orchestration dispatch budget circuit breaker",
        "html css javascript frontend styling layout",
    ),
    (
        "reinvention guard duplication primitive check",
        "payment gateway stripe webhook idempotency",
    ),
]


@pytest.mark.parametrize("a,b", _REPHRASE_PAIRS)
def test_rephrase_pairs_score_high(a, b):
    """Semantic rewrites must score >= DEFAULT_COSINE_THRESHOLD."""
    score = cosine(embed(a), embed(b))
    assert score >= DEFAULT_COSINE_THRESHOLD, (
        f"Rephrase pair scored too low ({score:.4f} < {DEFAULT_COSINE_THRESHOLD}):\n"
        f"  A: {a!r}\n  B: {b!r}"
    )


@pytest.mark.parametrize("a,b", _UNRELATED_PAIRS)
def test_unrelated_pairs_score_low(a, b):
    """Unrelated descriptions must score < DEFAULT_COSINE_THRESHOLD."""
    score = cosine(embed(a), embed(b))
    assert score < DEFAULT_COSINE_THRESHOLD, (
        f"Unrelated pair scored too high ({score:.4f} >= {DEFAULT_COSINE_THRESHOLD}):\n"
        f"  A: {a!r}\n  B: {b!r}"
    )


# --------------------------------------------------------------------------- #
# Module metadata                                                              #
# --------------------------------------------------------------------------- #

def test_impl_type_is_stub():
    assert IMPL_TYPE == "STUB", (
        f"Expected IMPL_TYPE='STUB', got {IMPL_TYPE!r}. "
        "Update this test if a REAL backend is activated."
    )


def test_default_threshold_is_in_range():
    assert 0.5 <= DEFAULT_COSINE_THRESHOLD <= 0.95, (
        f"DEFAULT_COSINE_THRESHOLD={DEFAULT_COSINE_THRESHOLD} is outside expected [0.5, 0.95]"
    )
