"""Unit tests for lib.engram_fts5_search (ADR-287 capability 3).

These tests build a self-contained SQLite DB with the same FTS5 mirror shape
used by the live engram store (observations + observations_fts contentless
FTS5 with triggers). The wrapper is then exercised against it.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from lib.engram_fts5_search import BM25Hit, fts5_available, search_bm25


@pytest.fixture
def fts_db(tmp_path: Path) -> Path:
    db = tmp_path / "engram-fts.db"
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
                topic_key TEXT
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
        rows = [
            ("alpha note", "the quick brown fox jumps over the lazy dog",
             None, "note", "p1", "k/alpha"),
            ("beta decision", "fox related decision about quick browsing",
             None, "decision", "p1", "k/beta"),
            ("gamma irrelevant", "completely unrelated text about cats",
             None, "note", "p2", "k/gamma"),
            ("delta heavy fox",
             "fox fox fox fox fox fox fox repeated for ranking",
             None, "note", "p1", "k/delta"),
        ]
        conn.executemany(
            "INSERT INTO observations (title, content, tool_name, type, project, topic_key) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return db


def test_fts5_available_true_when_table_present(fts_db):
    assert fts5_available(fts_db) is True


def test_fts5_available_false_when_missing(tmp_path):
    empty = tmp_path / "empty.db"
    conn = sqlite3.connect(empty)
    conn.execute("CREATE TABLE foo (id INTEGER)")
    conn.close()
    assert fts5_available(empty) is False


def test_search_bm25_returns_hits_ordered_by_score(fts_db):
    hits = search_bm25("fox", db_path=fts_db, limit=10)
    assert hits, "expected at least one hit"
    assert all(isinstance(h, BM25Hit) for h in hits)
    # Scores must be non-decreasing (FTS5 BM25: lower = more relevant).
    scores = [h.score for h in hits]
    assert scores == sorted(scores)
    # The "delta heavy fox" row repeats 'fox' many times -> should rank top.
    assert hits[0].title == "delta heavy fox"


def test_search_bm25_snippet_contains_match(fts_db):
    hits = search_bm25("quick", db_path=fts_db, limit=5)
    assert hits
    assert any("[quick]" in h.snippet or "quick" in h.snippet for h in hits)


def test_search_bm25_filters_by_project(fts_db):
    hits = search_bm25("fox", db_path=fts_db, limit=10, project="p2")
    # No p2 row contains 'fox'.
    assert hits == []


def test_search_bm25_filters_by_type(fts_db):
    hits = search_bm25("fox", db_path=fts_db, limit=10, type_filter="decision")
    assert hits
    assert all(h.type == "decision" for h in hits)


def test_search_bm25_empty_query_returns_empty(fts_db):
    assert search_bm25("", db_path=fts_db) == []
    assert search_bm25("   ", db_path=fts_db) == []
