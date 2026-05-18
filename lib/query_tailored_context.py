# SCOPE: os-only
"""ADR-040 — Public select_context API for query-tailored context injection.

Thin wrapper around lib.context_injector that exposes a structured list API
instead of a pre-formatted string.  Designed for callers that want to post-
process or re-rank the matches before formatting.

Usage::

    from lib.query_tailored_context import select_context

    chunks = select_context("refactor rate limiter", max_chunks=5)
    for chunk in chunks:
        print(chunk["file"], chunk["score"])

Each returned chunk is a dict with keys:
    file           str   — relative path to the source file (e.g. "lib/rate_limiter.py")
    lineno         int   — 0 (line-level granularity not available in the current index)
    content_snippet str  — short excerpt or docstring from the indexed item
    score          float — similarity score in [0.0, 1.0]

Implementation notes:
- Uses self_knowledge.query() for keyword candidates when embeddings unavailable.
- Uses reinvention_embeddings.cosine() for ranking when both sources supply vectors.
- Falls back to Jaccard score from context_injector when only code-index is available.
- Returns [] for empty queries (no error raised).
- max_chunks is always respected.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path bootstrap (so this module works regardless of sys.path state)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def select_context(
    query: str,
    max_chunks: int = 5,
    project_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return the top-*max_chunks* semantically relevant chunks for *query*.

    Parameters
    ----------
    query:
        Free-text description of the current task or question.
    max_chunks:
        Maximum number of chunks to return.  Must be >= 1.
    project_root:
        Path to the repository root.  Auto-detected when None.

    Returns
    -------
    list[dict]
        Each item has keys: file, lineno, content_snippet, score.
        Empty list when *query* is blank or no matches are found.

    Raises
    ------
    ValueError
        If *max_chunks* < 1.
    """
    if not query or not query.strip():
        return []

    if max_chunks < 1:
        raise ValueError(f"max_chunks must be >= 1, got {max_chunks!r}")

    root = _resolve_root(project_root)

    # Delegate heavy lifting to context_injector internals.
    from lib.context_injector import (
        _tokenise,
        _search_code_embeddings,
        _search_code_index,
        _search_adrs,
        _search_debt,
    )

    query_tokens = _tokenise(query.strip())
    all_matches: list[dict] = []

    # 1. Prefer embedding-based search for code corpus.
    embed_results = _search_code_embeddings(query.strip(), root, top_k=max_chunks)
    if embed_results is not None:
        all_matches.extend(embed_results)
    else:
        # Jaccard fallback.
        all_matches.extend(_search_code_index(query_tokens, root, top_k=max_chunks))

    # 2. ADR semantic search (Jaccard — ADRs not in embeddings corpus).
    all_matches.extend(_search_adrs(query_tokens, root, top_k=max_chunks))

    # 3. Debt register.
    all_matches.extend(_search_debt(query_tokens, root, top_k=max_chunks))

    # De-duplicate by path, keep highest score per path.
    seen: dict[str, dict] = {}
    for m in all_matches:
        key = m["path"]
        if key not in seen or m["score"] > seen[key]["score"]:
            seen[key] = m

    ranked = sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:max_chunks]

    # Normalise to the public chunk schema.
    return [
        {
            "file": item["path"],
            "lineno": 0,
            "content_snippet": item.get("excerpt", ""),
            "score": item["score"],
        }
        for item in ranked
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_root(project_root: str | Path | None) -> Path:
    """Resolve project root from argument or auto-detect."""
    if project_root is not None:
        return Path(project_root).resolve()

    # Walk up from this file to find the project root.
    candidate = _REPO_ROOT
    for _ in range(4):
        if (candidate / "cognitive-os.yaml").exists() or (candidate / ".claude").exists():
            return candidate
        candidate = candidate.parent

    return _REPO_ROOT
