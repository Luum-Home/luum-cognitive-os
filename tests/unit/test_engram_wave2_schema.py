"""Unit tests for additive Engram Wave 2 schema migration."""
from __future__ import annotations

import sqlite3

from lib.engram_wave2_schema import ensure_wave2_schema, observation_columns


def _create_db(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_id TEXT UNIQUE,
            title TEXT,
            content TEXT,
            type TEXT,
            topic_key TEXT,
            project TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE memory_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_id TEXT NOT NULL UNIQUE,
            source_id TEXT,
            target_id TEXT,
            relation TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            evidence TEXT,
            confidence REAL,
            judgment_status TEXT NOT NULL DEFAULT 'pending',
            superseded_at TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def test_wave2_schema_migration_adds_columns_indexes_and_backfills(tmp_path):
    db = tmp_path / "engram.db"
    conn = _create_db(db)
    conn.execute(
        "INSERT INTO observations (sync_id, title, content, type, topic_key, project, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("obs-old", "old", "content", "decision", "t", "p", "2026-01-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO observations (sync_id, title, content, type, topic_key, project, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("obs-new", "new", "content", "decision", "t", "p", "2026-02-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO memory_relations (sync_id, source_id, target_id, relation, judgment_status, superseded_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("rel-1", "obs-new", "obs-old", "supersedes", "approved", "2026-02-01T00:00:00Z", "2026-02-01T00:00:00Z"),
    )
    conn.commit()
    conn.close()

    result = ensure_wave2_schema(db)

    assert result.status == "pass"
    assert set(result.added_columns) == {"valid_from", "valid_to", "memory_class", "source_episode"}
    assert result.backfilled_valid_from == 2
    assert result.backfilled_valid_to == 1
    assert result.backfilled_memory_class == 2

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    assert {"valid_from", "valid_to", "memory_class", "source_episode"}.issubset(observation_columns(conn))
    old = conn.execute("SELECT valid_from, valid_to, memory_class, source_episode FROM observations WHERE sync_id = 'obs-old'").fetchone()
    assert old["valid_from"] == "2026-01-01T00:00:00Z"
    assert old["valid_to"] == "2026-02-01T00:00:00Z"
    assert old["memory_class"] == "unknown"
    assert old["source_episode"] is None
    conn.close()


def test_wave2_schema_migration_is_idempotent(tmp_path):
    db = tmp_path / "engram.db"
    conn = _create_db(db)
    conn.close()

    first = ensure_wave2_schema(db)
    second = ensure_wave2_schema(db)

    assert first.added_columns
    assert second.added_columns == []
    assert second.created_indexes == []
    assert second.backfilled_valid_from == 0
    assert second.backfilled_valid_to == 0
    assert second.backfilled_memory_class == 0


def test_wave2_schema_check_is_non_mutating(tmp_path):
    db = tmp_path / "engram.db"
    conn = _create_db(db)
    conn.close()

    result = ensure_wave2_schema(db, dry_run=True)

    assert result.status == "would-change"
    assert set(result.added_columns) == {"valid_from", "valid_to", "memory_class", "source_episode"}
    conn = sqlite3.connect(db)
    assert "valid_from" not in observation_columns(conn)
    conn.close()
