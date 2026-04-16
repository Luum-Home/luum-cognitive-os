"""Dead letter queue (DLQ) for agents that exhaust all retries.

When an agent fails after the maximum number of retries, the orchestrator
enqueues the task here so it is not silently lost.  Operators can inspect
the DLQ, re-queue individual entries for another attempt, or use the report
to identify systemic problems.

Storage: JSONL file at .cognitive-os/metrics/dead-letter-queue.jsonl
         (one JSON object per line, append-only for new entries;
          re-queue updates are written as a new entry with status="requeued"
          referencing the original entry_id).

Usage:
    from lib.dead_letter_queue import DeadLetterQueue

    dlq = DeadLetterQueue()
    dlq.enqueue_dead_letter(
        task_id="sdd-apply-auth-001",
        description="Implement JWT auth middleware",
        failure_type="BUILD_ERROR",
        retry_history=[{"attempt": 1, "error": "..."}, ...],
        diagnosis="Missing dependency in go.mod",
    )

    for entry in dlq.list_dead_letters(limit=10):
        print(entry)

    dlq.requeue_dead_letter("sdd-apply-auth-001")

Python 3.9+ compatible. No external dependencies.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Default path
# ---------------------------------------------------------------------------

def _default_dlq_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / ".cognitive-os" / "metrics" / "dead-letter-queue.jsonl"


# ---------------------------------------------------------------------------
# DeadLetterQueue
# ---------------------------------------------------------------------------


class DeadLetterQueue:
    """JSONL-backed dead letter queue for exhausted agent tasks."""

    def __init__(self, dlq_file: Optional[Path] = None):
        self._dlq_file = Path(dlq_file) if dlq_file is not None else _default_dlq_path()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue_dead_letter(
        self,
        task_id: str,
        description: str,
        failure_type: str,
        retry_history: List[Dict[str, Any]],
        diagnosis: str,
    ) -> Dict[str, Any]:
        """Append a failed task to the dead letter queue.

        Args:
            task_id:       Unique identifier for the task (e.g. "sdd-apply-auth-001").
            description:   Human-readable description of what the task was supposed to do.
            failure_type:  Error category (e.g. "BUILD_ERROR", "TEST_FAILURE").
            retry_history: List of dicts describing each retry attempt.
            diagnosis:     Agent's best guess at the root cause.

        Returns:
            The DLQ entry that was written.
        """
        entry: Dict[str, Any] = {
            "entry_id": str(uuid.uuid4()),
            "task_id": task_id,
            "description": description,
            "failure_type": failure_type,
            "retry_history": retry_history,
            "diagnosis": diagnosis,
            "status": "dead",
            "enqueued_at": _now_iso(),
            "requeued_at": None,
        }
        self._append(entry)
        return entry

    def list_dead_letters(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent DLQ entries (newest first).

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of entry dicts, newest first, up to *limit* entries.
        """
        entries = self._read_all()
        return entries[-limit:][::-1]  # last N entries, reversed to newest-first

    def requeue_dead_letter(self, entry_id: str) -> Dict[str, Any]:
        """Mark a dead letter as requeued for another attempt.

        Writes a new JSONL line with status="requeued" so the original
        append-only log is not mutated.

        Args:
            entry_id: The ``entry_id`` field of the DLQ entry to requeue.

        Returns:
            The updated entry dict.

        Raises:
            KeyError: If no entry with the given entry_id is found.
        """
        entries = self._read_all()
        original = next((e for e in entries if e.get("entry_id") == entry_id), None)
        if original is None:
            raise KeyError(f"No DLQ entry found with entry_id={entry_id!r}")

        updated = {**original, "status": "requeued", "requeued_at": _now_iso()}
        self._append(updated)
        return updated

    def format_dlq_report(self) -> str:
        """Return a human-readable summary of the dead letter queue."""
        entries = self._read_all()
        if not entries:
            return "Dead Letter Queue: empty."

        # Summarise by status
        dead_count = sum(1 for e in entries if e.get("status") == "dead")
        requeued_count = sum(1 for e in entries if e.get("status") == "requeued")
        total = len(entries)

        lines = [
            f"Dead Letter Queue: {total} entries"
            f" ({dead_count} dead, {requeued_count} requeued)",
        ]

        # Show the 10 most recent dead entries
        dead_entries = [e for e in reversed(entries) if e.get("status") == "dead"]
        for entry in dead_entries[:10]:
            lines.append(
                f"  ✗ [{entry.get('failure_type', '?')}]"
                f" {entry.get('task_id', '?')}"
                f"  ({entry.get('enqueued_at', '?')})"
                f"\n    {entry.get('description', '')}"
                f"\n    Diagnosis: {entry.get('diagnosis', 'n/a')}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, entry: Dict[str, Any]) -> None:
        self._dlq_file.parent.mkdir(parents=True, exist_ok=True)
        with self._dlq_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self._dlq_file.exists():
            return []
        entries: List[Dict[str, Any]] = []
        for line in self._dlq_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries


# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
