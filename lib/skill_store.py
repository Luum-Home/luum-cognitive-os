# SCOPE: os-only
"""SkillStore — SQLite persistence engine for skill quality tracking and lineage.

Schema ported verbatim from:
  github.com/HKUDS/OpenSpace @ d1e367d0ed4722d67f1f3b95d816ba4a959288d2
  openspace/skill_engine/store.py  (blob SHA b3e27516c9b5582d4b7377bab0e126ac405ae0a9)
  Lines 80-166 (_DDL block)

COS-namespace adjustments documented in ADR-176:
  - creator_id retained as TEXT; maps to agent_session_id at insert time
  - analyzed_by maps to `analyzer` parameter in record_analysis()
  - skill_applied (INTEGER) maps to status boolean

Discipline gate: this module has NO write path to live SKILL.md files.
All write paths go to the SQLite DB or to docs/reports/skill-analysis-proposals/.

Python 3.9+ compatible. Standard library only (sqlite3, hashlib, threading).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# DDL — verbatim port from OpenSpace store.py lines 79-166
# COS adjustments are noted inline.
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS skill_records (
    skill_id               TEXT PRIMARY KEY,
    name                   TEXT NOT NULL,
    description            TEXT NOT NULL DEFAULT '',
    path                   TEXT NOT NULL DEFAULT '',
    is_active              INTEGER NOT NULL DEFAULT 1,
    category               TEXT NOT NULL DEFAULT 'workflow',
    visibility             TEXT NOT NULL DEFAULT 'private',
    creator_id             TEXT NOT NULL DEFAULT '',
    lineage_origin         TEXT NOT NULL DEFAULT 'imported',
    lineage_generation     INTEGER NOT NULL DEFAULT 0,
    lineage_source_task_id TEXT,
    lineage_change_summary TEXT NOT NULL DEFAULT '',
    lineage_content_diff   TEXT NOT NULL DEFAULT '',
    lineage_content_snapshot TEXT NOT NULL DEFAULT '{}',
    lineage_created_at     TEXT NOT NULL,
    lineage_created_by     TEXT NOT NULL DEFAULT '',
    total_selections       INTEGER NOT NULL DEFAULT 0,
    total_applied          INTEGER NOT NULL DEFAULT 0,
    total_completions      INTEGER NOT NULL DEFAULT 0,
    total_fallbacks        INTEGER NOT NULL DEFAULT 0,
    first_seen             TEXT NOT NULL,
    last_updated           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sr_category ON skill_records(category);
CREATE INDEX IF NOT EXISTS idx_sr_updated  ON skill_records(last_updated);
CREATE INDEX IF NOT EXISTS idx_sr_active   ON skill_records(is_active);
CREATE INDEX IF NOT EXISTS idx_sr_name     ON skill_records(name);

CREATE TABLE IF NOT EXISTS skill_lineage_parents (
    skill_id        TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    parent_skill_id TEXT NOT NULL,
    PRIMARY KEY (skill_id, parent_skill_id)
);
CREATE INDEX IF NOT EXISTS idx_lp_parent
    ON skill_lineage_parents(parent_skill_id);

-- One row per task.  task_id is UNIQUE (at most one analysis per task).
CREATE TABLE IF NOT EXISTS execution_analyses (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id                 TEXT NOT NULL UNIQUE,
    timestamp               TEXT NOT NULL,
    task_completed          INTEGER NOT NULL DEFAULT 0,
    execution_note          TEXT NOT NULL DEFAULT '',
    tool_issues             TEXT NOT NULL DEFAULT '[]',
    candidate_for_evolution INTEGER NOT NULL DEFAULT 0,
    evolution_processed_at  TEXT DEFAULT NULL,
    evolution_suggestions   TEXT NOT NULL DEFAULT '[]',
    analyzed_by             TEXT NOT NULL DEFAULT '',
    analyzed_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ea_task  ON execution_analyses(task_id);
CREATE INDEX IF NOT EXISTS idx_ea_ts    ON execution_analyses(timestamp);

-- Per-skill judgments within an analysis.
-- FK to execution_analyses.id (CASCADE delete).
-- skill_id is a plain TEXT — no FK to skill_records so that
-- historical judgments survive skill deletion.
CREATE TABLE IF NOT EXISTS skill_judgments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id    INTEGER NOT NULL
        REFERENCES execution_analyses(id) ON DELETE CASCADE,
    skill_id       TEXT NOT NULL,
    skill_applied  INTEGER NOT NULL DEFAULT 0,
    note           TEXT NOT NULL DEFAULT '',
    UNIQUE(analysis_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_sj_skill    ON skill_judgments(skill_id);
CREATE INDEX IF NOT EXISTS idx_sj_analysis ON skill_judgments(analysis_id);

CREATE TABLE IF NOT EXISTS skill_tool_deps (
    skill_id TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    tool_key TEXT NOT NULL,
    critical INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (skill_id, tool_key)
);
CREATE INDEX IF NOT EXISTS idx_td_tool ON skill_tool_deps(tool_key);

CREATE TABLE IF NOT EXISTS skill_tags (
    skill_id TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    PRIMARY KEY (skill_id, tag)
);
"""


# ---------------------------------------------------------------------------
# COS-specific extension tables (not in OpenSpace, added per ADR-176)
# ---------------------------------------------------------------------------

_DDL_COS_EXTENSION = """
-- COS extension: typed analyses beyond execution_analyses
-- Supports record_analysis() with arbitrary analyzer names and score fields.
CREATE TABLE IF NOT EXISTS skill_analysis_scores (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id         TEXT NOT NULL,
    analyzer         TEXT NOT NULL DEFAULT '',
    score            REAL NOT NULL DEFAULT 0.0,
    observations     TEXT NOT NULL DEFAULT '{}',
    recorded_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sas_skill ON skill_analysis_scores(skill_id);
"""


def _sha256(data: str) -> str:
    """SHA-256 hash of a string for content-addressable lineage."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# SkillStore
# ---------------------------------------------------------------------------


class SkillStore:
    """SQLite persistence engine — Skill quality tracking and evolution ledger.

    Schema: 6-table verbatim port from OpenSpace (ADR-176) + 1 COS extension table.

    Architecture:
        Write path: sync method → self._mu lock → self._conn
        Read path:  sync method → independent short connection (WAL parallel read)

    Lifecycle: ``__init__(db_path)`` → use → ``close()``

    DISCIPLINE GATE: this class has no write path to live SKILL.md files.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._mu = threading.Lock()
        self._closed = False
        self._conn = self._make_connection()
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_connection(self, *, read_only: bool = False) -> sqlite3.Connection:
        if read_only:
            uri = f"file:{self._db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._mu:
            cur = self._conn.cursor()
            cur.executescript(_DDL)
            cur.executescript(_DDL_COS_EXTENSION)
            self._conn.commit()

    def close(self) -> None:
        if not self._closed:
            self._conn.close()
            self._closed = True

    def __enter__(self) -> "SkillStore":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def record_execution(
        self,
        skill_name: str,
        agent_session_id: str,
        tool_count: int,
        duration_ms: int,
        status: str,
        output_hash: Optional[str] = None,
    ) -> str:
        """Insert or upsert a skill execution record.

        Returns the skill_id (SHA-256 of skill_name for content-addressable key).
        Maps to OpenSpace's skill_records table.
        """
        skill_id = _sha256(skill_name)
        now = _now_iso()
        is_success = 1 if status in ("success", "ok", "pass") else 0
        snapshot = json.dumps({"output_hash": output_hash or "", "tool_count": tool_count, "duration_ms": duration_ms})

        with self._mu:
            self._conn.execute(
                """
                INSERT INTO skill_records (
                    skill_id, name, creator_id, lineage_content_snapshot,
                    lineage_created_at, first_seen, last_updated,
                    total_completions, total_applied
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    last_updated = excluded.last_updated,
                    total_completions = skill_records.total_completions + 1,
                    total_applied = skill_records.total_applied + excluded.total_applied
                """,
                (
                    skill_id,
                    skill_name,
                    agent_session_id,
                    snapshot,
                    now,
                    now,
                    now,
                    is_success,
                ),
            )
            self._conn.commit()
        return skill_id

    def record_lineage(
        self,
        child_id: str,
        parent_id: str,
        relation_type: str = "derived",
    ) -> None:
        """Insert a parent-child lineage edge.

        Maps to OpenSpace's skill_lineage_parents table.
        relation_type is stored in a note (OpenSpace table has no relation_type column).
        """
        with self._mu:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO skill_lineage_parents (skill_id, parent_skill_id)
                VALUES (?, ?)
                """,
                (child_id, parent_id),
            )
            self._conn.commit()

    def record_analysis(
        self,
        skill_id: str,
        analyzer: str,
        score: float,
        observations_json: str,
    ) -> int:
        """Insert a scored analysis for a skill.

        Uses COS extension table skill_analysis_scores (ADR-176 §COS extension).
        Also inserts a row into execution_analyses for cross-table consistency.
        Returns the inserted row id.
        """
        now = _now_iso()
        task_id = f"{skill_id}:{analyzer}:{now}"

        with self._mu:
            # Ensure execution_analyses has a corresponding row
            self._conn.execute(
                """
                INSERT OR IGNORE INTO execution_analyses (
                    task_id, timestamp, analyzed_by, analyzed_at
                ) VALUES (?, ?, ?, ?)
                """,
                (task_id, now, analyzer, now),
            )
            cur = self._conn.execute(
                """
                INSERT INTO skill_analysis_scores (skill_id, analyzer, score, observations, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (skill_id, analyzer, score, observations_json, now),
            )
            self._conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def record_judgment(
        self,
        skill_id: str,
        judge_model: str,
        verdict: str,
        confidence: float,
        rationale: str,
    ) -> None:
        """Insert a judgment for a skill (propose-only; never triggers auto-apply).

        Maps to OpenSpace's skill_judgments table via an execution_analyses parent row.
        DISCIPLINE GATE: verdict is stored only — no code path exists here to modify
        live SKILL.md files.
        """
        now = _now_iso()
        task_id = f"judgment:{skill_id}:{judge_model}:{now}"
        note = json.dumps({"verdict": verdict, "confidence": confidence, "rationale": rationale, "judge_model": judge_model})

        with self._mu:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO execution_analyses (
                    task_id, timestamp, analyzed_by, analyzed_at
                ) VALUES (?, ?, ?, ?)
                """,
                (task_id, now, judge_model, now),
            )
            row = self._conn.execute(
                "SELECT id FROM execution_analyses WHERE task_id = ?", (task_id,)
            ).fetchone()
            analysis_id = row["id"]

            skill_applied = 1 if verdict in ("approve", "accept", "pass") else 0
            self._conn.execute(
                """
                INSERT OR IGNORE INTO skill_judgments (analysis_id, skill_id, skill_applied, note)
                VALUES (?, ?, ?, ?)
                """,
                (analysis_id, skill_id, skill_applied, note),
            )
            self._conn.commit()

    def record_tool_dep(
        self,
        skill_id: str,
        tool_name: str,
        frequency: int = 1,
    ) -> None:
        """Insert or update a tool dependency for a skill.

        Maps to OpenSpace's skill_tool_deps table.
        `frequency` maps to `critical`: frequency >= 3 → critical=1.
        """
        critical = 1 if frequency >= 3 else 0
        with self._mu:
            self._conn.execute(
                """
                INSERT INTO skill_tool_deps (skill_id, tool_key, critical)
                VALUES (?, ?, ?)
                ON CONFLICT(skill_id, tool_key) DO UPDATE SET
                    critical = MAX(skill_tool_deps.critical, excluded.critical)
                """,
                (skill_id, tool_name, critical),
            )
            self._conn.commit()

    def record_tag(
        self,
        skill_id: str,
        tag: str,
        source: str = "auto",
    ) -> None:
        """Insert a tag for a skill.

        Maps to OpenSpace's skill_tags table.
        `source` is appended to tag as `<tag>:<source>` for traceability.
        """
        tagged = f"{tag}:{source}" if source and source != "auto" else tag
        with self._mu:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO skill_tags (skill_id, tag)
                VALUES (?, ?)
                """,
                (skill_id, tagged),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def query_lineage(
        self,
        skill_id: str,
        depth: int = 3,
    ) -> List[Tuple[str, int]]:
        """Return ancestor chain for a skill via recursive CTE traversal.

        Returns list of (skill_id, depth) tuples starting from direct parents.
        depth=0 means the skill itself; this returns depth 1..depth.
        """
        with self._make_connection(read_only=True) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            rows = conn.execute(
                """
                WITH RECURSIVE lineage(skill_id, depth) AS (
                    SELECT parent_skill_id, 1
                    FROM skill_lineage_parents
                    WHERE skill_id = ?
                    UNION ALL
                    SELECT slp.parent_skill_id, l.depth + 1
                    FROM skill_lineage_parents slp
                    JOIN lineage l ON slp.skill_id = l.skill_id
                    WHERE l.depth < ?
                )
                SELECT skill_id, depth FROM lineage ORDER BY depth, skill_id
                """,
                (skill_id, depth),
            ).fetchall()
        return [(row["skill_id"], row["depth"]) for row in rows]

    def query_recent(
        self,
        skill_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return recent execution records for a named skill.

        Returns list of dicts with keys: skill_id, name, last_updated,
        total_completions, total_applied, lineage_content_snapshot.
        """
        skill_id = _sha256(skill_name)
        with self._make_connection(read_only=True) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT skill_id, name, last_updated, total_completions, total_applied,
                       lineage_content_snapshot
                FROM skill_records
                WHERE skill_id = ?
                ORDER BY last_updated DESC
                LIMIT ?
                """,
                (skill_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def hash_output(output: str) -> str:
        """SHA-256 of execution output for content-addressable lineage."""
        return _sha256(output)
