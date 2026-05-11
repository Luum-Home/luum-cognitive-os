"""
ADR-263 — Tool-Replay Budget Ledger
Per-session SQLite ledger with FRESH/PREVIEW/REFERENCE_ONLY modes.

Source-pattern: .private/external-pattern-research/annex-b-cost-budget.md §B1 (clean-room rewrite)
License: Apache-2.0 modified. No source code copied from reference pattern.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Caps (derived from luum usage distribution, see ADR-263 §3)
# ---------------------------------------------------------------------------
CHAR_CAP_PER_SESSION: int = 20_000
ITEM_CAP_PER_SESSION: int = 10
TTL_HOURS: float = 4.0
TTL_SECONDS: float = TTL_HOURS * 3600

# Pointer string length estimate (for chars_saved calculation)
_POINTER_CHARS: int = 120


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class Mode(Enum):
    FRESH = "fresh"
    PREVIEW = "compact"
    REFERENCE_ONLY = "pointer_only"


@dataclass
class LedgerDecision:
    mode: Mode
    trimmed: bool
    trim_reason: Optional[str]          # "char_cap" | "item_cap" | None
    replay_chars: int
    total_session_chars: int
    max_session_chars: int
    total_session_items: int
    max_session_items: int
    spillover_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name     TEXT    NOT NULL,
    target_hash   TEXT    NOT NULL,
    first_seen_ts REAL    NOT NULL,
    touched_at_ts REAL    NOT NULL,
    visit_count   INTEGER NOT NULL DEFAULT 1,
    cumul_chars   INTEGER NOT NULL DEFAULT 0,
    UNIQUE(tool_name, target_hash)
);

CREATE TABLE IF NOT EXISTS session_budget (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    total_chars     INTEGER NOT NULL DEFAULT 0,
    total_items     INTEGER NOT NULL DEFAULT 0,
    chars_saved     INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO session_budget (id, total_chars, total_items, chars_saved)
VALUES (1, 0, 0, 0);
"""


# ---------------------------------------------------------------------------
# ToolReplayLedger
# ---------------------------------------------------------------------------

class ToolReplayLedger:
    """
    Per-session SQLite ledger that tracks (tool_name, target_hash) replay
    frequency and enforces char/item caps.

    Args:
        session_id: Identifier of the current session.  Defaults to
            $CLAUDE_SESSION_ID, then PID+timestamp fallback.
        base_dir: Root directory for all sessions.  Defaults to
            .cognitive-os/sessions relative to the working directory.
        char_cap: Maximum cumulative chars across the session.
        item_cap: Maximum distinct (tool, target) tuples tracked.
        ttl_hours: Hours before an entry is considered expired.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        base_dir: Optional[str] = None,
        char_cap: int = CHAR_CAP_PER_SESSION,
        item_cap: int = ITEM_CAP_PER_SESSION,
        ttl_hours: float = TTL_HOURS,
    ) -> None:
        self._session_id = session_id or self._resolve_session_id()
        self._char_cap = char_cap
        self._item_cap = item_cap
        self._ttl_seconds = ttl_hours * 3600

        # Resolve paths
        if base_dir:
            session_dir = Path(base_dir) / self._session_id
        else:
            project_dir = Path(os.environ.get("PROJECT_DIR", os.getcwd()))
            session_dir = project_dir / ".cognitive-os" / "sessions" / self._session_id

        self._session_dir = session_dir
        self._db_path = session_dir / "replay-ledger.sqlite"
        self._spillover_dir = session_dir / "spillover"
        self._metrics_path = self._resolve_metrics_path()

        session_dir.mkdir(parents=True, exist_ok=True)
        self._conn = self._open_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, tool_name: str, target_hash: str, result_chars: int) -> LedgerDecision:
        """
        Record a tool result and return the mode decision for this call.

        Side-effects:
        - Updates the SQLite ledger.
        - Appends to metrics JSONL.
        - Prunes expired entries (lazily, only when count > 2×item_cap).
        """
        now = time.time()
        budget = self._load_budget()

        # Lazy prune
        entry_count = self._entry_count()
        if entry_count > self._item_cap * 2:
            self.prune_expired()

        existing = self._get_entry(tool_name, target_hash)
        is_expired = existing is not None and (now - existing["touched_at_ts"]) > self._ttl_seconds

        # Treat expired entries as non-existent
        if is_expired:
            self._delete_entry(tool_name, target_hash)
            existing = None

        trim_reason: Optional[str] = None
        mode: Mode

        if existing is None:
            # First time seeing this (tool, target) — check item cap
            current_items = budget["total_items"]
            if current_items >= self._item_cap:
                # Item cap reached: new targets are immediately REFERENCE_ONLY
                mode = Mode.REFERENCE_ONLY
                trim_reason = "item_cap"
            else:
                mode = Mode.FRESH
                self._insert_entry(tool_name, target_hash, result_chars, now)
                self._update_budget(result_chars, delta_items=1)
        else:
            # Seen before — determine PREVIEW or REFERENCE_ONLY
            current_chars = budget["total_chars"]
            if current_chars + result_chars > self._char_cap:
                mode = Mode.REFERENCE_ONLY
                trim_reason = "char_cap"
            else:
                mode = Mode.PREVIEW

            self._touch_entry(tool_name, target_hash, result_chars, now)
            self._update_budget(result_chars, delta_items=0)

        # Reload budget after update
        budget = self._load_budget()

        spillover_path: Optional[str] = None
        chars_saved = 0
        if mode == Mode.REFERENCE_ONLY:
            chars_saved = result_chars - _POINTER_CHARS
        elif mode == Mode.PREVIEW:
            # Approximate: saved = chars beyond the preview threshold
            from lib.tool_budget_catalog import get_thresholds
            preview_max, _ = get_thresholds(tool_name)
            chars_saved = max(0, result_chars - preview_max)

        self._update_chars_saved(chars_saved)

        decision = LedgerDecision(
            mode=mode,
            trimmed=(mode != Mode.FRESH),
            trim_reason=trim_reason,
            replay_chars=result_chars,
            total_session_chars=budget["total_chars"],
            max_session_chars=self._char_cap,
            total_session_items=budget["total_items"],
            max_session_items=self._item_cap,
        )

        self._append_metric(tool_name, target_hash, mode, result_chars, budget, spillover_path)
        return decision

    def get_mode(self, tool_name: str, target_hash: str) -> Mode:
        """Query mode without modifying accumulators."""
        now = time.time()
        existing = self._get_entry(tool_name, target_hash)

        if existing is None:
            return Mode.FRESH

        if (now - existing["touched_at_ts"]) > self._ttl_seconds:
            return Mode.FRESH  # Expired → treat as new

        budget = self._load_budget()
        if budget["total_chars"] >= self._char_cap:
            return Mode.REFERENCE_ONLY

        return Mode.PREVIEW

    def write_spillover(self, tool_name: str, target_hash: str, content: str) -> str:
        """
        Write full content to spillover directory and return the pointer string.
        """
        self._spillover_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        hash_short = target_hash[:8]
        filename = f"{tool_name}-{hash_short}-{ts}.txt"
        path = self._spillover_dir / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    def make_pointer(self, tool_name: str, target_hash: str, spillover_path: str) -> str:
        """Return the [REF:...] pointer string for REFERENCE_ONLY mode."""
        hash_short = target_hash[:8]
        return f"[REF:tool={tool_name} target={hash_short} path={spillover_path}]"

    def stats(self) -> dict:
        """Return session metrics: chars_saved, items_tracked, etc."""
        budget = self._load_budget()
        entry_count = self._entry_count()
        return {
            "session_id": self._session_id,
            "total_chars": budget["total_chars"],
            "char_cap": self._char_cap,
            "total_items": budget["total_items"],
            "item_cap": self._item_cap,
            "chars_saved": budget["chars_saved"],
            "entries_tracked": entry_count,
            "db_path": str(self._db_path),
            "spillover_dir": str(self._spillover_dir),
        }

    def prune_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        cutoff = time.time() - self._ttl_seconds
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM entries WHERE touched_at_ts < ?", (cutoff,)
            )
            return cursor.rowcount

    def cleanup(self) -> None:
        """Delete SQLite and spillover directory for this session."""
        try:
            self._conn.close()
        except Exception:
            pass

        if self._db_path.exists():
            self._db_path.unlink()

        if self._spillover_dir.exists():
            import shutil
            shutil.rmtree(self._spillover_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_session_id() -> str:
        sid = os.environ.get("CLAUDE_SESSION_ID", "")
        if sid:
            return sid
        # Fallback: PID + coarse timestamp
        return f"default-{os.getpid()}-{int(time.time() // 3600)}"

    def _resolve_metrics_path(self) -> Path:
        project_dir = Path(os.environ.get("PROJECT_DIR", os.getcwd()))
        metrics_dir = project_dir / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        return metrics_dir / "tool-replay-ledger.jsonl"

    def _open_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL mode for concurrent subshell access (ADR-263 §Consequences)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_DDL)
        conn.commit()
        return conn

    def _get_entry(self, tool_name: str, target_hash: str) -> Optional[sqlite3.Row]:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE tool_name=? AND target_hash=?",
            (tool_name, target_hash),
        ).fetchone()
        return row

    def _insert_entry(self, tool_name: str, target_hash: str, chars: int, ts: float) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT OR IGNORE INTO entries
                   (tool_name, target_hash, first_seen_ts, touched_at_ts, visit_count, cumul_chars)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (tool_name, target_hash, ts, ts, chars),
            )

    def _touch_entry(self, tool_name: str, target_hash: str, chars: int, ts: float) -> None:
        with self._conn:
            self._conn.execute(
                """UPDATE entries
                   SET touched_at_ts=?, visit_count=visit_count+1, cumul_chars=cumul_chars+?
                   WHERE tool_name=? AND target_hash=?""",
                (ts, chars, tool_name, target_hash),
            )

    def _delete_entry(self, tool_name: str, target_hash: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM entries WHERE tool_name=? AND target_hash=?",
                (tool_name, target_hash),
            )

    def _entry_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        return row[0] if row else 0

    def _load_budget(self) -> dict:
        row = self._conn.execute("SELECT * FROM session_budget WHERE id=1").fetchone()
        if row:
            return dict(row)
        return {"total_chars": 0, "total_items": 0, "chars_saved": 0}

    def _update_budget(self, chars: int, delta_items: int) -> None:
        with self._conn:
            self._conn.execute(
                """UPDATE session_budget
                   SET total_chars=total_chars+?, total_items=total_items+?
                   WHERE id=1""",
                (chars, delta_items),
            )

    def _update_chars_saved(self, chars_saved: int) -> None:
        if chars_saved <= 0:
            return
        with self._conn:
            self._conn.execute(
                "UPDATE session_budget SET chars_saved=chars_saved+? WHERE id=1",
                (chars_saved,),
            )

    def _append_metric(
        self,
        tool_name: str,
        target_hash: str,
        mode: Mode,
        result_chars: int,
        budget: dict,
        spillover_path: Optional[str],
    ) -> None:
        try:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            chars_saved = budget.get("chars_saved", 0)
            entry = {
                "ts": ts,
                "session_id": self._session_id,
                "tool_name": tool_name,
                "target_hash": target_hash[:8],
                "mode": mode.value,
                "result_chars": result_chars,
                "total_session_chars": budget.get("total_chars", 0),
                "chars_saved": chars_saved,
                "spilled": spillover_path is not None,
                "spillover_path": spillover_path,
            }
            with open(self._metrics_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.debug("Failed to append metric: %s", exc)


# ---------------------------------------------------------------------------
# Convenience: compute target_hash from tool arguments
# ---------------------------------------------------------------------------

def compute_target_hash(tool_args: str) -> str:
    """
    SHA-256 of normalized tool args, first 16 hex chars.
    Normalization strips timestamps, PIDs and other non-deterministic tokens
    so the same logical operation maps to the same hash even if minor
    details vary (ADR-263 §Open Questions #1).
    """
    import re
    # Strip common non-deterministic tokens
    normalized = re.sub(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\s]*', '', tool_args)
    normalized = re.sub(r'\bPID[= ]\d+', '', normalized)
    normalized = re.sub(r'\b\d{5,}\b', '', normalized)  # large numeric IDs
    normalized = normalized.strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
