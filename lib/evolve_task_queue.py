#!/usr/bin/env python3
# SCOPE: os-only
"""evolve_task_queue — SQLite-backed proposal queue for the evolve loop spike.

ADR-262 §Decision 2: persistent queue at .cognitive-os/state/evolve-proposals.db.
Supports enqueue, list_pending, approve, reject, mark_promoted operations.

Clean-room implementation per ADR-259. No holaOS source material used.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / ".cognitive-os" / "state" / "evolve-proposals.db"
ERROR_LEARNING_PATH = REPO_ROOT / ".cognitive-os" / "error-learning.jsonl"

QUEUE_CAP = 50  # Hard cap on pending proposals

VALID_KINDS = {"skill_new", "skill_patch"}
VALID_STATUSES = {"pending", "approved", "rejected", "promoted"}

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS evolve_proposals (
    proposal_id   TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,
    title         TEXT NOT NULL,
    rationale     TEXT NOT NULL,
    draft         TEXT NOT NULL,
    confidence    REAL NOT NULL,
    fingerprint   TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL,
    reviewed_at   TEXT,
    reviewer      TEXT,
    reject_reason TEXT
);
"""


@dataclass
class EvolveProposal:
    """A candidate skill proposal extracted by the evolve review job.

    Fields mirror the evolve_proposals table schema (ADR-262 §Decision 2).
    """

    kind: str  # 'skill_new' | 'skill_patch'
    title: str
    rationale: str
    draft: str
    confidence: float
    # Computed on enqueue if not provided
    fingerprint: str = ""
    # Set by the queue on insertion
    proposal_id: str = ""
    status: str = "pending"
    created_at: str = ""
    reviewed_at: Optional[str] = None
    reviewer: Optional[str] = None
    reject_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"Invalid kind '{self.kind}'. Must be one of {VALID_KINDS}")
        if not self.fingerprint:
            self.fingerprint = compute_fingerprint(self.kind, self.title, self.draft)

    def to_dict(self) -> dict:
        return asdict(self)


def compute_fingerprint(kind: str, title: str, draft: str) -> str:
    """Compute a sha256 fingerprint over normalized (kind, title, draft).

    Normalization: strip leading/trailing whitespace, collapse internal runs of
    whitespace to a single space. This makes minor formatting differences
    (extra newlines, indentation) not generate duplicate proposals.
    """
    import re

    def _normalize(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip())

    raw = "\n".join([_normalize(kind), _normalize(title), _normalize(draft)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _log_error_learning(message: str, context: dict | None = None) -> None:
    """Append a warning record to error-learning.jsonl."""
    try:
        ERROR_LEARNING_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "evolve_task_queue",
            "message": message,
            "context": context or {},
        }
        with ERROR_LEARNING_PATH.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to write error-learning.jsonl: %s", exc)


class EvolveTaskQueue:
    """SQLite-backed queue for evolve loop skill proposals.

    Usage::

        queue = EvolveTaskQueue()
        proposal_id = queue.enqueue(proposal)
        pending = queue.list_pending()
        queue.approve(proposal_id, reviewer="operator")
        queue.reject(proposal_id, reason="Not reusable", reviewer="operator")
        queue.mark_promoted(proposal_id)
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, proposal: EvolveProposal) -> str | None:
        """Insert a proposal if its fingerprint is not already present.

        Returns the proposal_id on success, or None if:
        - The fingerprint already exists (duplicate, silent no-op).
        - The pending queue is at or above QUEUE_CAP (warning logged).
        """
        with self._connect() as conn:
            # Dedup check
            existing = conn.execute(
                "SELECT proposal_id FROM evolve_proposals WHERE fingerprint = ?",
                (proposal.fingerprint,),
            ).fetchone()
            if existing:
                logger.debug("Duplicate fingerprint %s — skipping enqueue", proposal.fingerprint[:12])
                return None

            # Cap check
            pending_count = conn.execute(
                "SELECT COUNT(*) FROM evolve_proposals WHERE status = 'pending'"
            ).fetchone()[0]
            if pending_count >= QUEUE_CAP:
                msg = (
                    f"Evolve queue at capacity ({QUEUE_CAP} pending). "
                    f"Proposal '{proposal.title[:60]}' not enqueued."
                )
                logger.warning(msg)
                _log_error_learning(msg, {"title": proposal.title, "kind": proposal.kind})
                return None

            # Assign IDs
            if not proposal.proposal_id:
                proposal.proposal_id = str(uuid.uuid4())
            if not proposal.created_at:
                proposal.created_at = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO evolve_proposals
                  (proposal_id, kind, title, rationale, draft, confidence,
                   fingerprint, status, created_at, reviewed_at, reviewer, reject_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, NULL, NULL, NULL)
                """,
                (
                    proposal.proposal_id,
                    proposal.kind,
                    proposal.title,
                    proposal.rationale,
                    proposal.draft,
                    proposal.confidence,
                    proposal.fingerprint,
                    proposal.created_at,
                ),
            )
            conn.commit()

        logger.info("Enqueued proposal %s '%s'", proposal.proposal_id[:8], proposal.title[:60])
        return proposal.proposal_id

    def list_pending(self, limit: int = 50) -> list[EvolveProposal]:
        """Return pending proposals ordered by confidence DESC."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM evolve_proposals
                WHERE status = 'pending'
                ORDER BY confidence DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_proposal(r) for r in rows]

    def approve(self, proposal_id: str, reviewer: str = "operator") -> bool:
        """Mark a proposal as approved. Returns True if row was updated."""
        return self._set_reviewed_status(proposal_id, "approved", reviewer, None)

    def reject(self, proposal_id: str, reason: str, reviewer: str = "operator") -> bool:
        """Mark a proposal as rejected, storing the reason. Returns True if updated."""
        return self._set_reviewed_status(proposal_id, "rejected", reviewer, reason)

    def mark_promoted(self, proposal_id: str) -> bool:
        """Mark an approved proposal as promoted. Returns True if row was updated."""
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE evolve_proposals
                SET status = 'promoted'
                WHERE proposal_id = ? AND status = 'approved'
                """,
                (proposal_id,),
            )
            conn.commit()
            return result.rowcount > 0

    def get(self, proposal_id: str) -> EvolveProposal | None:
        """Fetch a single proposal by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM evolve_proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        return _row_to_proposal(row) if row else None

    def pending_count(self) -> int:
        """Return current count of pending proposals."""
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM evolve_proposals WHERE status = 'pending'"
            ).fetchone()[0]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_reviewed_status(
        self,
        proposal_id: str,
        status: str,
        reviewer: str,
        reason: str | None,
    ) -> bool:
        reviewed_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE evolve_proposals
                SET status = ?,
                    reviewed_at = ?,
                    reviewer = ?,
                    reject_reason = ?
                WHERE proposal_id = ? AND status = 'pending'
                """,
                (status, reviewed_at, reviewer, reason, proposal_id),
            )
            conn.commit()
        return result.rowcount > 0


def _row_to_proposal(row: sqlite3.Row) -> EvolveProposal:
    """Convert a sqlite3.Row to an EvolveProposal dataclass."""
    return EvolveProposal(
        proposal_id=row["proposal_id"],
        kind=row["kind"],
        title=row["title"],
        rationale=row["rationale"],
        draft=row["draft"],
        confidence=row["confidence"],
        fingerprint=row["fingerprint"],
        status=row["status"],
        created_at=row["created_at"],
        reviewed_at=row["reviewed_at"],
        reviewer=row["reviewer"],
        reject_reason=row["reject_reason"],
    )
