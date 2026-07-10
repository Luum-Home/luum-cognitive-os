# SCOPE: both
"""Additive Engram Wave 2 memory schema migration helpers.

The migration is intentionally SQLite-local and idempotent. It only adds nullable
observation fields required by M1/M2/M4 experiments and backfills deterministic
values; it does not change the default Engram retrieval strategy.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

WAVE2_SCHEMA_VERSION = "engram-wave2-memory-schema.v1"

OBSERVATION_COLUMNS: dict[str, str] = {
    "valid_from": "TEXT",
    "valid_to": "TEXT",
    "memory_class": "TEXT",
    "source_episode": "TEXT",
}

INDEXES: tuple[tuple[str, str], ...] = (
    ("idx_observations_validity", "observations(valid_from, valid_to)"),
    ("idx_observations_memory_class", "observations(memory_class)"),
    ("idx_observations_source_episode", "observations(source_episode)"),
)


@dataclass(frozen=True)
class EngramWave2SchemaResult:
    schema_version: str
    status: str
    db_path: str
    dry_run: bool
    added_columns: list[str]
    existing_columns: list[str]
    created_indexes: list[str]
    backfilled_valid_from: int
    backfilled_valid_to: int
    backfilled_memory_class: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def observation_columns(conn: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(observations)").fetchall()}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA index_list(observations)").fetchall()}


def ensure_wave2_schema(db_path: str | Path, *, dry_run: bool = False) -> EngramWave2SchemaResult:
    """Ensure additive Wave 2 columns/indexes exist in an Engram SQLite DB.

    Backfill policy follows the Wave 2 plan:
    - valid_from = created_at only when created_at exists and is non-empty.
    - valid_to = memory_relations.superseded_at for approved supersedes edges.
    - memory_class = unknown when missing; deterministic inference is deferred.
    - source_episode stays null until episode/event IDs are available.
    """
    path = Path(db_path).expanduser()
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "observations" not in tables:
            raise ValueError("Engram DB does not contain observations table")

        before = observation_columns(conn)
        added: list[str] = []
        for column, ddl_type in OBSERVATION_COLUMNS.items():
            if column in before:
                continue
            added.append(column)
            if not dry_run:
                conn.execute(f"ALTER TABLE observations ADD COLUMN {column} {ddl_type}")

        after = before | set(added)
        existing = sorted(after)

        present_indexes = _index_names(conn)
        created_indexes: list[str] = []
        for name, spec in INDEXES:
            if name in present_indexes:
                continue
            created_indexes.append(name)
            if not dry_run:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {spec}")

        backfilled_valid_from = 0
        backfilled_valid_to = 0
        backfilled_memory_class = 0

        if not dry_run:
            if "created_at" in after:
                cur = conn.execute(
                    """
                    UPDATE observations
                    SET valid_from = created_at
                    WHERE (valid_from IS NULL OR valid_from = '')
                      AND created_at IS NOT NULL
                      AND created_at != ''
                    """
                )
                backfilled_valid_from = cur.rowcount if cur.rowcount is not None else 0

            cur = conn.execute(
                """
                UPDATE observations
                SET memory_class = 'unknown'
                WHERE memory_class IS NULL OR memory_class = ''
                """
            )
            backfilled_memory_class = cur.rowcount if cur.rowcount is not None else 0

            if "memory_relations" in tables:
                rel_cols = {str(row[1]) for row in conn.execute("PRAGMA table_info(memory_relations)").fetchall()}
                if {"target_id", "relation", "judgment_status", "superseded_at"}.issubset(rel_cols):
                    cur = conn.execute(
                        """
                        UPDATE observations
                        SET valid_to = (
                            SELECT mr.superseded_at
                            FROM memory_relations mr
                            WHERE mr.target_id = observations.sync_id
                              AND mr.relation = 'supersedes'
                              AND mr.judgment_status != 'rejected'
                              AND mr.superseded_at IS NOT NULL
                              AND mr.superseded_at != ''
                            ORDER BY mr.superseded_at DESC
                            LIMIT 1
                        )
                        WHERE (valid_to IS NULL OR valid_to = '')
                          AND sync_id IN (
                            SELECT target_id
                            FROM memory_relations
                            WHERE relation = 'supersedes'
                              AND judgment_status != 'rejected'
                              AND superseded_at IS NOT NULL
                              AND superseded_at != ''
                          )
                        """
                    )
                    backfilled_valid_to = cur.rowcount if cur.rowcount is not None else 0

            conn.commit()

        status = "would-change" if dry_run and (added or created_indexes) else "pass"
        return EngramWave2SchemaResult(
            schema_version=WAVE2_SCHEMA_VERSION,
            status=status,
            db_path=str(path),
            dry_run=dry_run,
            added_columns=added,
            existing_columns=existing,
            created_indexes=created_indexes,
            backfilled_valid_from=backfilled_valid_from,
            backfilled_valid_to=backfilled_valid_to,
            backfilled_memory_class=backfilled_memory_class,
        )
    finally:
        conn.close()
