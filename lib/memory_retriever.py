"""
Hybrid Memory Retriever — FTS5 + Jaccard reranking for Engram queries.

Improves recall quality over raw FTS5 by adding:
- Jaccard word-set similarity for reranking
- Optional trust-score weighting
- Configurable score weights

Adopted pattern: Hermes holographic/retrieval.py (MIT license)
Simplified: FTS5 + Jaccard only (no HRR vectors)
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Stop words — English + Spanish
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    # English
    "the", "a", "an", "is", "are", "was", "were", "in", "on",
    "at", "to", "for", "of", "with", "and", "or", "not", "it",
    "this", "that", "from", "by", "as", "be", "has", "had",
    "have", "will", "would", "could", "should", "do", "did",
    "its", "if", "so", "but", "we", "he", "she", "they", "you",
    # Spanish
    "el", "la", "los", "las", "de", "en", "un", "una", "y", "o",
    "es", "son", "ser", "estar", "con", "por", "para", "al", "del",
    "lo", "le", "se", "su", "sus", "que", "no", "si", "me", "te",
})


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """A single result from hybrid retrieval."""

    id: int
    title: str
    content: str
    topic_key: str
    project: str
    fts5_score: float     # normalized FTS5 rank in [0, 1]
    jaccard_score: float  # word-set similarity in [0, 1]
    combined_score: float  # weighted combination


# ---------------------------------------------------------------------------
# MemoryRetriever
# ---------------------------------------------------------------------------


class MemoryRetriever:
    """Hybrid FTS5 + Jaccard retriever over Engram's SQLite database.

    Retrieval pipeline:
    1. FTS5 search: pull ``limit * 3`` candidates from the observations_fts
       virtual table (wider net for reranking headroom).
    2. Jaccard reranking: compute word-set overlap between the query and each
       candidate's (title + content).
    3. Combine: ``combined = fts5_weight * fts5 + jaccard_weight * jaccard``.
    4. Sort descending by combined score, return top ``limit`` results.

    Weights:
        fts5_weight=0.6, jaccard_weight=0.4 — favour FTS5 because it uses
        BM25 internally and understands term frequency; Jaccard adds recall
        for paraphrased queries that share vocabulary but not exact phrases.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        fts5_weight: float = 0.6,
        jaccard_weight: float = 0.4,
    ) -> None:
        self.db_path = db_path or os.path.expanduser("~/.engram/engram.db")
        self.fts5_weight = fts5_weight
        self.jaccard_weight = jaccard_weight

        # Normalise weights so they always sum to 1.0
        total = self.fts5_weight + self.jaccard_weight
        if total > 0:
            self.fts5_weight /= total
            self.jaccard_weight /= total

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 10,
        project: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """Hybrid search: FTS5 candidates → Jaccard reranking.

        Args:
            query:   Free-text search query.
            limit:   Maximum number of results to return.
            project: Optional project name to restrict results.

        Returns:
            List of :class:`RetrievalResult` sorted by ``combined_score``
            descending, capped at ``limit`` entries.
        """
        if not query or not query.strip():
            return []

        # Step 1: FTS5 candidates (3× limit for reranking headroom)
        candidates = self._fts5_search(query, limit * 3, project)

        if not candidates:
            return []

        # Step 2: Jaccard reranking
        query_tokens = self._tokenize(query)
        for candidate in candidates:
            content_tokens = self._tokenize(
                f"{candidate.title} {candidate.content}"
            )
            candidate.jaccard_score = self._jaccard_similarity(
                query_tokens, content_tokens
            )
            candidate.combined_score = (
                self.fts5_weight * candidate.fts5_score
                + self.jaccard_weight * candidate.jaccard_score
            )

        # Step 3: sort and truncate
        candidates.sort(key=lambda r: -r.combined_score)
        return candidates[:limit]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fts5_search(
        self,
        query: str,
        limit: int,
        project: Optional[str],
    ) -> List[RetrievalResult]:
        """Query Engram's FTS5 index directly via SQLite.

        FTS5 rank values are negative (lower = better match).  We normalise
        them to [0, 1] using ``score = |rank| / max(|rank|)`` across the
        candidate set so that the best match gets score 1.0.
        """
        if not os.path.exists(self.db_path):
            return []

        # Escape FTS5 special characters to avoid syntax errors on raw input
        safe_query = self._escape_fts5_query(query)
        if not safe_query:
            return []

        conn = sqlite3.connect(self.db_path)
        try:
            sql = """
                SELECT o.id,
                       o.title,
                       o.content,
                       COALESCE(o.topic_key, '') AS topic_key,
                       COALESCE(o.project,   '') AS project,
                       fts.rank                  AS fts_rank_raw
                FROM observations_fts fts
                JOIN observations o ON o.id = fts.rowid
                WHERE observations_fts MATCH ?
                  AND o.deleted_at IS NULL
            """
            params: list = [safe_query]

            if project:
                sql += " AND o.project = ?"
                params.append(project)

            sql += " ORDER BY fts.rank LIMIT ?"
            params.append(limit)

            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                # Malformed FTS5 query — return empty rather than crash
                return []

            if not rows:
                return []

            # Normalise FTS5 rank to [0, 1]: rank is negative, abs closer to
            # 0 = better match.  Use max-normalisation so the top hit is 1.0.
            raw_ranks = [abs(row[5]) if row[5] else 1.0 for row in rows]
            max_rank = max(raw_ranks) if raw_ranks else 1.0
            max_rank = max(max_rank, 1e-9)  # guard against zero

            results: List[RetrievalResult] = []
            for row, raw_rank in zip(rows, raw_ranks):
                normalized = raw_rank / max_rank  # [0, 1] — higher = better match
                results.append(
                    RetrievalResult(
                        id=row[0],
                        title=row[1] or "",
                        content=row[2] or "",
                        topic_key=row[3],
                        project=row[4],
                        fts5_score=normalized,
                        jaccard_score=0.0,
                        combined_score=0.0,
                    )
                )
            return results
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Static utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> set:
        """Tokenise *text* into a lowercase word set with stop words removed.

        Uses a simple regex word-character split — no stemming.  Spanish stop
        words are included alongside English ones.
        """
        if not text:
            return set()
        words = set(re.findall(r"\w+", text.lower()))
        return words - _STOP_WORDS

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """Jaccard similarity between two word sets: |A ∩ B| / |A ∪ B|."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _escape_fts5_query(query: str) -> str:
        """Strip FTS5 syntax characters that would cause parse errors.

        Removes double-quotes, asterisks, carets, and parentheses so raw
        user-supplied text can be passed to MATCH without crashing.  The
        result may be empty if the query consisted entirely of special chars.
        """
        # Remove characters with special meaning in FTS5 MATCH syntax
        cleaned = re.sub(r'["\^\*\(\)\:\-]', " ", query)
        # Collapse whitespace and strip
        cleaned = " ".join(cleaned.split())
        return cleaned
