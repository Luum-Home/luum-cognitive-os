# SCOPE: both
"""Engram FTS5 + BM25 retrieval wrapper (ADR-287, capability 3).

The ``observations_fts`` virtual table already exists on the live engram DB
with `INSERT`/`UPDATE`/`DELETE` triggers keeping it synchronised. This module
is a thin, read-only Python wrapper that surfaces BM25 score + snippet to
callers without requiring them to know SQL.

The DB is opened read-only via the ``mode=ro`` URI form to guarantee no
mutation can leak from this path.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = os.environ.get(
    "ENGRAM_DB", str(Path.home() / ".engram" / "engram.db")
)

# Default FTS5 column to apply snippet() to. observations_fts columns:
#   0=title, 1=content, 2=tool_name, 3=type, 4=project, 5=topic_key
_SNIPPET_COLUMN = 1


@dataclass(frozen=True)
class BM25Hit:
    observation_id: int
    title: str
    snippet: str
    score: float
    project: str | None
    type: str | None
    topic_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _open_readonly(db_path: str | Path) -> sqlite3.Connection:
    p = Path(db_path).expanduser()
    uri = f"file:{p}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fts5_available(db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    """Return True if ``observations_fts`` exists and is queryable."""
    try:
        conn = _open_readonly(db_path)
    except sqlite3.OperationalError:
        return False
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='observations_fts'"
        ).fetchone()
        return row is not None
    except sqlite3.DatabaseError:
        return False
    finally:
        conn.close()


def search_bm25(
    query: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    limit: int = 10,
    project: str | None = None,
    type_filter: str | None = None,
    snippet_chars: int = 24,
    min_quality: float | None = None,
) -> list[BM25Hit]:
    """Search ``observations_fts`` for ``query`` ranked by BM25.

    Args:
      query: An FTS5 MATCH expression. Caller is responsible for quoting
             phrases. We do NOT pre-tokenize.
      db_path: SQLite DB file. Opened read-only.
      limit: Max rows.
      project: Optional project filter (applied via FTS5 column match for
               exact equality).
      type_filter: Optional type filter.
      snippet_chars: Max tokens in the snippet (FTS5 ``snippet()`` arg 5).
      min_quality: ADR-290 Pattern 4 filter on the weighted quality score.
                   ``None`` (default) disables filtering — backwards-compatible.
                   A positive float (e.g. ``0.5``) excludes any observation
                   whose ``quality_completeness``, ``quality_relevance``,
                   ``quality_clarity``, or ``quality_accuracy`` is NULL
                   (missing == 0), or whose weighted score is below
                   ``min_quality``.

    Returns: list of :class:`BM25Hit`, ordered by ascending BM25 score
    (lower is more relevant per FTS5 convention).
    """
    if not query or not query.strip():
        return []

    # Build the MATCH expression. observations_fts is a regular (non-column)
    # FTS5 index; we apply project/type filters with explicit column syntax.
    parts: list[str] = [f"({query})"]
    if project:
        parts.append(f'project:"{project}"')
    if type_filter:
        parts.append(f'type:"{type_filter}"')
    match_expr = " AND ".join(parts)

    snippet_call = (
        f"snippet(observations_fts, {_SNIPPET_COLUMN}, '[', ']', '...', ?)"
    )

    sql = f"""
        SELECT rowid,
               title,
               {snippet_call} AS snippet,
               bm25(observations_fts) AS score,
               project,
               type,
               topic_key
        FROM observations_fts
        WHERE observations_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """

    # When min_quality is requested we may need to fetch more rows than
    # ``limit`` because some will be filtered out. We over-fetch a small
    # constant factor and trim after filtering.
    effective_limit = limit if min_quality is None else max(limit * 4, limit)

    conn = _open_readonly(db_path)
    try:
        cur = conn.execute(sql, (snippet_chars, match_expr, effective_limit))
        rows = cur.fetchall()

        if min_quality is None:
            hits_rows = rows
        else:
            hits_rows = _apply_min_quality_filter(
                conn, rows, min_quality=float(min_quality)
            )[:limit]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

    return [
        BM25Hit(
            observation_id=int(r[0]),
            title=str(r[1] or ""),
            snippet=str(r[2] or ""),
            score=float(r[3]),
            project=r[4],
            type=r[5],
            topic_key=r[6],
        )
        for r in hits_rows
    ]


def _apply_min_quality_filter(
    conn: sqlite3.Connection,
    rows: list[tuple[Any, ...]],
    *,
    min_quality: float,
) -> list[tuple[Any, ...]]:
    """Filter FTS rows by the weighted quality score on ``observations``.

    Missing scores (any of the four columns NULL) are treated as 0 and the
    row is excluded whenever ``min_quality > 0``. Weights are uniform 0.25
    (kept inline here to avoid a circular import with the schema module).
    """
    if not rows:
        return []
    ids = [int(r[0]) for r in rows]
    placeholders = ",".join("?" for _ in ids)
    quality_sql = (
        "SELECT id, quality_completeness, quality_relevance, "
        "quality_clarity, quality_accuracy "
        f"FROM observations WHERE id IN ({placeholders})"
    )
    try:
        cur = conn.execute(quality_sql, ids)
        score_by_id: dict[int, float | None] = {}
        for obs_id, c, r, cl, a in cur.fetchall():
            if c is None or r is None or cl is None or a is None:
                score_by_id[int(obs_id)] = None
                continue
            score_by_id[int(obs_id)] = (
                float(c) + float(r) + float(cl) + float(a)
            ) / 4.0
    except sqlite3.OperationalError:
        # Observations table missing the quality columns yet — treat as missing.
        return [] if min_quality > 0 else list(rows)

    kept: list[tuple[Any, ...]] = []
    for row in rows:
        obs_id = int(row[0])
        score = score_by_id.get(obs_id)
        if score is None:
            # Missing == 0; excluded whenever the caller asks for > 0.
            if min_quality > 0:
                continue
            kept.append(row)
            continue
        if score >= min_quality:
            kept.append(row)
    return kept
