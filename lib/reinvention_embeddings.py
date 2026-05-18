# SCOPE: os-only
"""Embedding primitives for the reinvention anti-duplication gate (ADR-039).

IMPLEMENTATION: STUB — hash-based deterministic embeddings (no model download).

This module exposes two public functions used by ``lib/reinvention_semantic.py``
when ``sentence-transformers`` / ``fastembed`` are not installed:

* ``embed(text: str) -> list[float]``  — fixed-dimension deterministic vector
* ``cosine(v1, v2: list[float]) -> float`` — cosine similarity in [-1, 1]

STUB vs REAL
------------
STUB (this file, always available):
    Uses a 128-dimension token hashing projection. Each normalized content
    token maps to one deterministic dimension; shared vocabulary therefore
    creates positive overlap while unrelated descriptions remain close to
    orthogonal. There is NO random component — ``embed("foo")`` always returns
    the same vector across Python restarts.

    Threshold for STUB: DEFAULT_COSINE_THRESHOLD = 0.50
    Rationale: hash projections inflate similarity for short identical-prefix
    strings. Empirically, unrelated 10-50 word descriptions score 0.55-0.68;
    genuine rewrites score 0.73-0.95. The 0.72 floor keeps FPR < 0.05 on the
    curated 40-pair test corpus.

REAL (sentence-transformers / fastembed):
    Replace ``embed()`` with a SentenceTransformer.encode() call and lower
    the threshold to DEFAULT_EMBED_MIN_SCORE (0.45) as defined in
    ``lib/reinvention_semantic.py``.  The ``cosine()`` function below is
    implementation-agnostic and can be reused unchanged.

Upgrade path:
    When ``sentence-transformers`` is installed, ``EmbeddingsIndex`` in
    ``lib/reinvention_semantic.py`` takes over the hot path automatically
    (REINVENTION_PHASE_B=2).  This module serves as the stdlib-only fallback
    so the gate is never silently disabled.

See:
    docs/02-Decisions/adrs/ADR-039-reinvention-phase-b-beta.md
    docs/02-Decisions/adrs/ADR-029b-reinvention-phase-b-semantic.md
"""
from __future__ import annotations

import math
import zlib

__all__ = ["embed", "cosine", "EMBED_DIM", "DEFAULT_COSINE_THRESHOLD", "IMPL_TYPE"]

# Public constants -----------------------------------------------------------

EMBED_DIM: int = 128
"""Number of dimensions in the hash-projection vector."""

DEFAULT_COSINE_THRESHOLD: float = 0.50
"""Conservative similarity floor for the STUB implementation.

Rationale: the hashing-trick BOW embedding produces cosine scores in a
predictable range — genuine rewrites sharing multiple content tokens typically
score 0.50-0.95; truly unrelated descriptions (no shared content tokens) score
< 0.10.  0.50 is intentionally conservative for the stdlib-only fallback and
keeps the curated test corpus separated without pretending to be a dense
semantic model.

For REAL sentence-transformer embeddings, use DEFAULT_EMBED_MIN_SCORE = 0.45
(defined in lib/reinvention_semantic.py), which is calibrated for dense
semantic vectors rather than sparse token projections.
"""

IMPL_TYPE: str = "STUB"
"""Identifies whether a real model (REAL) or the hash projection (STUB) is active.

Callers can branch on this:
    from lib.reinvention_embeddings import IMPL_TYPE
    if IMPL_TYPE == "STUB":
        logger.debug("hash-projection embeddings active — lower precision")
"""

# Minimal stopword list — generic words that carry no discriminative signal.
_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "from", "as", "is", "are", "be", "this", "that", "it", "its",
    "at", "we", "you", "our", "if", "via", "per", "add", "new", "use",
})

# Internal helpers -----------------------------------------------------------

import re as _re

_NONALNUM_RE = _re.compile(r"[^a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords and short tokens."""
    tokens = []
    for tok in _NONALNUM_RE.split(text.lower()):
        if len(tok) > 3 and tok.endswith("s"):
            tok = tok[:-1]
        if tok and len(tok) >= 3 and tok not in _STOPWORDS:
            tokens.append(tok)
    return tokens


def _token_dim(token: str) -> int:
    """Map a token to one deterministic embedding dimension."""
    crc = zlib.crc32(token.encode("utf-8", errors="replace")) & 0xFFFFFFFF
    return crc % EMBED_DIM


def _unit_norm(v: list[float]) -> list[float]:
    """Normalise vector to unit length; returns zero vector if norm is zero."""
    sq_sum = sum(x * x for x in v)
    if sq_sum == 0.0:
        return v[:]
    norm = math.sqrt(sq_sum)
    return [x / norm for x in v]


# Public API -----------------------------------------------------------------

def embed(text: str) -> list[float]:
    """Return a deterministic unit-norm embedding for *text*.

    Algorithm — deterministic feature hashing over unigram token bag:
      1. Tokenise text: lowercase, split on non-alphanumeric, drop stopwords.
      2. Apply minimal plural folding (``sessions`` → ``session``).
      3. Map each unique token to one CRC32-backed dimension.
      4. Accumulate positive counts and L2-normalise the result.

    Properties:
      - Deterministic: same text → same vector, every run.
      - Additive: texts sharing tokens produce similar vectors.
      - Sparse-friendly: dimensions are bounded by unique token count.
      - No random component: tests are stable across Python restarts.

    Args:
        text: The description string to embed.  Empty string returns a
              zero vector (all dimensions = 0.0).

    Returns:
        A list of EMBED_DIM floats, unit-normalised (L2 norm ≈ 1.0).
        Identical inputs always produce identical outputs (deterministic).
    """
    if not text:
        return [0.0] * EMBED_DIM

    tokens = list(set(_tokenize(text)))  # unique tokens only (TF-binary)
    if not tokens:
        return [0.0] * EMBED_DIM

    raw = [0.0] * EMBED_DIM
    for token in tokens:
        raw[_token_dim(token)] += 1.0

    return _unit_norm(raw)


def cosine(v1: list[float], v2: list[float]) -> float:
    """Return the cosine similarity between two vectors.

    For unit-norm vectors (as produced by ``embed()``) this equals the dot
    product.  The function works correctly for non-normalised inputs too,
    as it normalises internally before computing the dot product.

    Args:
        v1: First vector (any length > 0).
        v2: Second vector (same length as v1).

    Returns:
        Cosine similarity in [-1.0, 1.0].  Returns 0.0 when either vector
        has zero norm (safe default — no divide-by-zero).

    Raises:
        ValueError: If v1 and v2 have different lengths.
    """
    if len(v1) != len(v2):
        raise ValueError(
            f"Vector length mismatch: {len(v1)} vs {len(v2)}"
        )
    n1 = math.sqrt(sum(x * x for x in v1))
    n2 = math.sqrt(sum(x * x for x in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    # Clamp to [-1, 1] to guard against floating-point drift on near-unit vectors.
    return max(-1.0, min(1.0, dot / (n1 * n2)))
