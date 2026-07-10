"""ADR-209 Outcome-failure queue and regression handler.

Persists failed/inconclusive canary outcomes to a JSONL queue so that
regressions are not silently dropped.  Consumers (Maintainer, operator
dashboard, CI hooks) can drain the queue and act on it without re-reading
raw experiment state.

Queue location: .cognitive-os/tasks/outcome-failure-queue.jsonl
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

QUEUE_PATH = Path(".cognitive-os/tasks/outcome-failure-queue.jsonl")

# Outcomes that should be enqueued for follow-up.
FAILURE_OUTCOMES = frozenset({"failed", "inconclusive"})


def _default_queue_path() -> Path:
    """Resolve queue path relative to cwd (allows test overrides)."""
    return QUEUE_PATH


def enqueue_failure(
    experiment_id: str,
    outcome: str,
    measurement: dict[str, Any],
    *,
    queue_path: Path | None = None,
) -> None:
    """Append a failed or inconclusive outcome to the persistent queue.

    Parameters
    ----------
    experiment_id:
        Stable identifier for the experiment (from the experiment contract).
    outcome:
        One of "failed" or "inconclusive".  Raises ValueError for other values.
    measurement:
        Raw measurement dict as returned by the canary evaluator.
    queue_path:
        Override the default queue path (used in tests).
    """
    if outcome not in FAILURE_OUTCOMES:
        raise ValueError(
            f"outcome must be one of {sorted(FAILURE_OUTCOMES)}, got {outcome!r}"
        )

    path = queue_path or _default_queue_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    entry: dict[str, Any] = {
        "enqueued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment_id": experiment_id,
        "outcome": outcome,
        "measurement": measurement,
        "status": "pending",
    }

    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def drain_queue(
    *,
    queue_path: Path | None = None,
    status_filter: str | None = "pending",
) -> list[dict[str, Any]]:
    """Return all queue entries matching ``status_filter``.

    Does NOT mutate the queue file; callers are responsible for downstream
    actions and calling ``mark_processed`` when done.
    """
    path = queue_path or _default_queue_path()
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if status_filter is None or entry.get("status") == status_filter:
                entries.append(entry)

    return entries


def mark_processed(
    experiment_id: str,
    *,
    queue_path: Path | None = None,
) -> int:
    """Flip status from "pending" to "processed" for all entries matching
    ``experiment_id``.  Returns the number of entries updated."""
    path = queue_path or _default_queue_path()
    if not path.exists():
        return 0

    updated = 0
    new_lines: list[str] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if entry.get("experiment_id") == experiment_id and entry.get("status") == "pending":
                entry["status"] = "processed"
                updated += 1
            new_lines.append(json.dumps(entry) + "\n")

    path.write_text("".join(new_lines), encoding="utf-8")
    return updated


def regression_count(*, queue_path: Path | None = None) -> int:
    """Return the number of pending *failed* entries (guardrail regressions)."""
    pending = drain_queue(queue_path=queue_path, status_filter="pending")
    return sum(1 for e in pending if e.get("outcome") == "failed")
