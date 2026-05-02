# SCOPE: both
# scope: both
"""
File-based serialized merge queue — P2.2 (ADR-116).

Sessions enqueue their per-session branches.  A single-writer worker
dequeues one entry at a time, runs basic gates, ff-merges to main, and
pushes.  Concurrency safety is provided by ``fcntl.flock`` (LOCK_EX)
around all read-modify-write operations on the JSONL file, ensuring no
two writers interleave on the same line.

Architecture note
-----------------
The single-writer assumption (one worker running at a time) is enforced
by the worker acquiring a *separate* flock on ``merge-queue.worker.lock``.  This
library's own LOCK_EX is per-operation (enqueue/dequeue/peek) and guards
only the JSONL file integrity — it does NOT prevent two workers from
running concurrently.  flock on the worker's lock file is the *only*
protection against that scenario.

Queue file location: ``.cognitive-os/sessions/merge-queue.jsonl``

Schema (one JSON object per line)::

    {
        "id":             "<uuid4>",
        "session_branch": "<git branch name>",
        "session_id":     "<string>",
        "expected_files": ["<path>", ...],   # optional verification list
        "enqueued_at":    "<ISO-8601 UTC>",
        "status":         "queued|in-progress|completed|failed",
        "completed_at":   null,
        "notes":          null
    }

Public API
----------
enqueue(session_branch, session_id, expected_files=None, *, queue_path=None) -> str
peek(*, queue_path=None) -> dict | None
dequeue(entry_id, status='completed', notes=None, *, queue_path=None) -> bool
status(entry_id, *, queue_path=None) -> dict | None
list_pending(*, queue_path=None) -> list[dict]

Events emitted (via event_bus)
-------------------------------
merge_queued      — on enqueue
merge_completed   — on dequeue with status='completed'
merge_failed      — on dequeue with status='failed'

Python 3.9+ compatible.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_QUEUE_PATH = ".cognitive-os/sessions/merge-queue.jsonl"

PENDING_STATUSES = frozenset({"queued", "in-progress"})
TERMINAL_STATUSES = frozenset({"completed", "failed"})
ALL_STATUSES = PENDING_STATUSES | TERMINAL_STATUSES


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_queue_path(queue_path: Optional[str | Path] = None) -> Path:
    if queue_path is not None:
        return Path(queue_path).expanduser().resolve()
    env_path = os.environ.get("MERGE_QUEUE_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".cognitive-os").is_dir():
            return candidate / _DEFAULT_QUEUE_PATH
    return cwd / _DEFAULT_QUEUE_PATH


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _read_all(path: Path) -> list[dict]:
    """Read all valid JSON lines from the queue file.

    Corrupt or non-JSON lines are silently skipped (logged at DEBUG level).
    """
    entries: list[dict] = []
    if not path.exists():
        return entries
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                logger.debug(
                    "merge_queue: skipping corrupt line %d in %s: %s",
                    lineno,
                    path,
                    exc,
                )
    return entries


def _write_all(path: Path, entries: list[dict]) -> None:
    """Overwrite the queue file with *entries* (one JSON object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _emit_event(event_type: str, payload: dict, session_id: str) -> None:
    """Emit a bus event — best-effort; never raises."""
    try:
        from lib.event_bus import emit  # type: ignore[import]

        emit(event_type, payload, session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("merge_queue: event_bus emit failed (best-effort): %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enqueue(
    session_branch: str,
    session_id: str,
    expected_files: Optional[List[str]] = None,
    *,
    queue_path: Optional[str | Path] = None,
) -> str:
    """Append a new entry to the merge queue.

    Parameters
    ----------
    session_branch:
        The git branch name (e.g. ``session/abc123-my-feature``).
    session_id:
        Identifier for the session that owns this branch.
    expected_files:
        Optional list of file paths the worker should verify exist on the
        branch tip before merging.
    queue_path:
        Override queue file location (useful in tests).

    Returns
    -------
    str
        The UUID of the new queue entry.
    """
    path = _resolve_queue_path(queue_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_id = str(uuid.uuid4())
    entry: dict = {
        "id": entry_id,
        "session_branch": session_branch,
        "session_id": session_id,
        "expected_files": expected_files or [],
        "enqueued_at": _now_iso(),
        "status": "queued",
        "completed_at": None,
        "notes": None,
    }

    # Atomic append under exclusive lock.
    with path.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)

    _emit_event(
        "merge_queued",
        {"entry_id": entry_id, "session_branch": session_branch},
        session_id=session_id,
    )
    logger.info("merge_queue: enqueued %s (branch=%s)", entry_id, session_branch)
    return entry_id


def peek(*, queue_path: Optional[str | Path] = None) -> Optional[dict]:
    """Return the first non-completed entry without modifying the queue.

    Returns ``None`` if the queue is empty or all entries are terminal.
    """
    path = _resolve_queue_path(queue_path)
    entries = _read_all(path)
    for entry in entries:
        if entry.get("status") in PENDING_STATUSES:
            return dict(entry)
    return None


def dequeue(
    entry_id: str,
    status: str = "completed",
    notes: Optional[str] = None,
    *,
    queue_path: Optional[str | Path] = None,
) -> bool:
    """Mark an entry as terminal (completed or failed).

    Uses LOCK_EX around the read-modify-write cycle so concurrent workers
    cannot interleave updates.

    Parameters
    ----------
    entry_id:
        UUID of the entry to mark.
    status:
        Must be ``'completed'`` or ``'failed'``.
    notes:
        Optional human-readable notes (e.g. failure reason).
    queue_path:
        Override queue file location.

    Returns
    -------
    bool
        ``True`` if the entry was found and updated, ``False`` otherwise.
    """
    if status not in TERMINAL_STATUSES:
        raise ValueError(
            f"status must be one of {sorted(TERMINAL_STATUSES)}, got {status!r}"
        )

    path = _resolve_queue_path(queue_path)

    # We use a lock *file* for the read-modify-write so we hold a single fd
    # open for the duration, preventing concurrent dequeue races.
    lock_file = path.with_suffix(".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    session_id = "unknown"
    updated = False

    with lock_file.open("a", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            entries = _read_all(path)
            for entry in entries:
                if entry.get("id") == entry_id:
                    session_id = entry.get("session_id", "unknown")
                    entry["status"] = status
                    entry["completed_at"] = _now_iso()
                    entry["notes"] = notes
                    updated = True
                    break
            if updated:
                _write_all(path, entries)
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)

    if updated:
        event_type = "merge_completed" if status == "completed" else "merge_failed"
        _emit_event(
            event_type,
            {"entry_id": entry_id, "notes": notes},
            session_id=session_id,
        )
        logger.info("merge_queue: dequeued %s -> %s", entry_id, status)

    return updated


def status(
    entry_id: str,
    *,
    queue_path: Optional[str | Path] = None,
) -> Optional[dict]:
    """Return the queue entry for *entry_id*, or ``None`` if not found."""
    path = _resolve_queue_path(queue_path)
    for entry in _read_all(path):
        if entry.get("id") == entry_id:
            return dict(entry)
    return None


def list_pending(*, queue_path: Optional[str | Path] = None) -> list[dict]:
    """Return all entries whose status is ``'queued'`` or ``'in-progress'``."""
    path = _resolve_queue_path(queue_path)
    return [
        dict(e) for e in _read_all(path) if e.get("status") in PENDING_STATUSES
    ]
