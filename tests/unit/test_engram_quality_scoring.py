"""Unit tests for ADR-290 Engram quality scoring."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from lib.engram_fts5_search import search_bm25
from lib.engram_wave3_schema import (
    Claim,
    DEFAULT_QUALITY_WEIGHTS,
    compute_quality_score,
    ensure_wave3_schema,
)


@pytest.fixture
def quality_fts_db(tmp_path: Path) -> Path:
    db = tmp_path / "quality-fts.db"
    conn = sqlite3.connect(db)
    try:
        conn.executescript(
            """
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_name TEXT,
                type TEXT NOT NULL,
                project TEXT,
                topic_key TEXT,
                quality_completeness REAL,
                quality_relevance REAL,
                quality_clarity REAL,
                quality_accuracy REAL
            );
            CREATE VIRTUAL TABLE observations_fts USING fts5(
                title, content, tool_name, type, project, topic_key,
                content='observations', content_rowid='id'
            );
            CREATE TRIGGER obs_fts_insert AFTER INSERT ON observations BEGIN
                INSERT INTO observations_fts(rowid, title, content, tool_name, type, project, topic_key)
                VALUES (new.id, new.title, new.content, new.tool_name, new.type, new.project, new.topic_key);
            END;
            """
        )
        conn.executemany(
            """
            INSERT INTO observations (
                title, content, tool_name, type, project, topic_key,
                quality_completeness, quality_relevance, quality_clarity, quality_accuracy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("high quality fox", "fox evidence", None, "fact", "p", "k/high", 0.9, 0.9, 0.9, 0.9),
                ("low quality fox", "fox evidence", None, "fact", "p", "k/low", 0.1, 0.1, 0.1, 0.1),
                ("unscored fox", "fox evidence", None, "fact", "p", "k/none", None, None, None, None),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return db


def test_compute_quality_score_clamps_and_weights() -> None:
    score = compute_quality_score(
        completeness=2.0,
        relevance=0.5,
        clarity=-1.0,
        accuracy=1.0,
        weights={"completeness": 2, "relevance": 1, "clarity": 1, "accuracy": 0},
    )

    assert score == pytest.approx((1.0 * 2 + 0.5 * 1 + 0.0 * 1 + 1.0 * 0) / 4)


def test_min_quality_none_preserves_unfiltered_hits(quality_fts_db: Path) -> None:
    hits = search_bm25("fox", db_path=quality_fts_db, limit=10, min_quality=None)

    assert {hit.title for hit in hits} == {"high quality fox", "low quality fox", "unscored fox"}


def test_min_quality_filters_low_and_unscored_hits(quality_fts_db: Path) -> None:
    hits = search_bm25("fox", db_path=quality_fts_db, limit=10, min_quality=0.5)

    assert [hit.title for hit in hits] == ["high quality fox"]


# ---------------------------------------------------------------------------
# Additional coverage — scoring determinism, claim dataclass, schema migration.
# ---------------------------------------------------------------------------


def test_compute_quality_score_uniform_default_weights() -> None:
    assert compute_quality_score(1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)
    assert compute_quality_score(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0)
    assert compute_quality_score(0.5, 0.5, 0.5, 0.5) == pytest.approx(0.5)


def test_compute_quality_score_custom_weights_deterministic() -> None:
    weights = {
        "completeness": 0.1,
        "relevance": 0.1,
        "clarity": 0.1,
        "accuracy": 0.7,
    }
    assert compute_quality_score(0.0, 0.0, 0.0, 1.0, weights=weights) == pytest.approx(0.7)
    assert compute_quality_score(1.0, 1.0, 1.0, 0.0, weights=weights) == pytest.approx(0.3)


def test_compute_quality_score_missing_weight_key_raises() -> None:
    with pytest.raises(ValueError, match="missing required key"):
        compute_quality_score(0.5, 0.5, 0.5, 0.5, weights={"completeness": 1.0})


def test_default_weights_sum_to_one() -> None:
    assert sum(DEFAULT_QUALITY_WEIGHTS.values()) == pytest.approx(1.0)


def test_claim_quality_fields_default_to_none() -> None:
    c = Claim(title="t", content="c", type="discovery")
    assert c.quality_completeness is None
    assert c.quality_relevance is None
    assert c.quality_clarity is None
    assert c.quality_accuracy is None


def test_claim_accepts_quality_fields() -> None:
    c = Claim(
        title="t",
        content="c",
        type="fact",
        quality_completeness=0.9,
        quality_relevance=0.8,
        quality_clarity=0.7,
        quality_accuracy=0.6,
    )
    assert c.quality_completeness == 0.9
    assert c.quality_accuracy == 0.6


def _make_min_engram_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                project TEXT,
                topic_key TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_wave3_migration_adds_quality_columns(tmp_path: Path) -> None:
    db = tmp_path / "engram.db"
    _make_min_engram_db(db)
    result = ensure_wave3_schema(db)
    assert "quality_completeness" in result.added_columns
    assert "quality_relevance" in result.added_columns
    assert "quality_clarity" in result.added_columns
    assert "quality_accuracy" in result.added_columns

    conn = sqlite3.connect(db)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(observations)")}
    finally:
        conn.close()
    assert {
        "quality_completeness",
        "quality_relevance",
        "quality_clarity",
        "quality_accuracy",
    }.issubset(cols)


def test_search_bm25_default_call_unaffected_by_pattern4(quality_fts_db: Path) -> None:
    """Regression — default invocation behaves identically to explicit None."""
    default_hits = search_bm25("fox", db_path=quality_fts_db, limit=10)
    explicit = search_bm25("fox", db_path=quality_fts_db, limit=10, min_quality=None)
    assert {h.title for h in default_hits} == {h.title for h in explicit}
