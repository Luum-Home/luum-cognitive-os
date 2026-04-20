"""Unit tests: RateLimitQueue flock-based concurrent access (D45 flock gap).

Tests that concurrent enqueue/dequeue operations:
  1. Never lose writes (no item dropped due to race).
  2. Never double-dequeue the same item.
  3. Log a timeout event and continue gracefully when lock cannot be acquired.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from lib.rate_limiter import (  # noqa: E402
    RateLimitQueue,
    _queue_file_lock,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test 1: 10 concurrent enqueues — all 10 items must survive
# ---------------------------------------------------------------------------

def test_concurrent_enqueue_no_lost_writes(tmp_path: Path) -> None:
    """10 threads each enqueue 1 item; all 10 must appear in the queue."""
    queue_path = str(tmp_path / "queue.json")
    errors: list[Exception] = []
    results: list[str] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        q = RateLimitQueue(state_path=queue_path, cooldown_seconds=300)
        try:
            qid = q.enqueue("bash_command", {"description": f"item-{index}"}, retry_count=0)
            with lock:
                results.append(qid)
        except Exception as exc:
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Unexpected errors: {errors}"
    assert len(results) == 10, f"Expected 10 queue IDs, got {len(results)}"
    assert len(set(results)) == 10, "Duplicate queue IDs detected"

    # Verify persisted count — reload from disk via a fresh queue instance
    # (JSONL append-only format: use the queue API, not raw JSON parse)
    verify_q = RateLimitQueue(state_path=queue_path, cooldown_seconds=300)
    persisted = verify_q.peek()
    assert len(persisted) == 10, f"Expected 10 persisted items, got {len(persisted)}"


# ---------------------------------------------------------------------------
# Test 2: concurrent dequeue — no double-dequeue
# ---------------------------------------------------------------------------

def test_dequeue_under_lock_contention(tmp_path: Path) -> None:
    """Two threads dequeue concurrently; the same item must not be returned twice."""
    queue_path = str(tmp_path / "queue.json")

    # Pre-populate queue with 2 items (both immediately eligible)
    setup_q = RateLimitQueue(state_path=queue_path, cooldown_seconds=1)
    for i in range(2):
        qid = setup_q.enqueue(
            "bash_command", {"description": f"ready-{i}"}, retry_count=0
        )
        # Force eligible_at to the past
        items = setup_q._load()
        for item in items:
            if item["queue_id"] == qid:
                item["eligible_at"] = time.time() - 1
        setup_q._items = items
        setup_q._save()

    dequeued_ids: list[str] = []
    lock = threading.Lock()

    def dequeue_worker() -> None:
        q = RateLimitQueue(state_path=queue_path, cooldown_seconds=1)
        ready = q.dequeue_ready()
        with lock:
            dequeued_ids.extend(item["queue_id"] for item in ready)

    t1 = threading.Thread(target=dequeue_worker)
    t2 = threading.Thread(target=dequeue_worker)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Total dequeued should equal 2 (no double-dequeue)
    assert len(dequeued_ids) == 2, f"Expected 2 dequeued items, got {len(dequeued_ids)}"
    assert len(set(dequeued_ids)) == 2, "Same item dequeued twice!"


# ---------------------------------------------------------------------------
# Test 3: lock timeout logs gracefully and does not raise
# ---------------------------------------------------------------------------

def test_lock_timeout_logged_and_no_deadlock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When flock cannot be acquired within timeout, a log entry is written
    and _queue_file_lock yields (no exception, no deadlock)."""
    import fcntl

    log_path = str(tmp_path / "queue-lock-timeout.jsonl")
    monkeypatch.setenv("_QUEUE_LOCK_TIMEOUT_LOG", log_path)
    # Patch the module-level constant so _log_lock_timeout writes to our log
    import lib.rate_limiter as rl_mod
    original_log = rl_mod._QUEUE_LOCK_TIMEOUT_LOG
    monkeypatch.setattr(rl_mod, "_QUEUE_LOCK_TIMEOUT_LOG", log_path)

    queue_path = str(tmp_path / "queue.json")
    lock_path = queue_path + ".lock"
    Path(lock_path).touch()

    # Hold an exclusive lock externally so _queue_file_lock times out
    with open(lock_path, "w") as holder_fd:
        fcntl.flock(holder_fd, fcntl.LOCK_EX)
        try:
            # _queue_file_lock should time out quickly (use tiny timeout)
            with _queue_file_lock(queue_path, timeout=0.15):
                pass  # Must not raise, must not deadlock
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)

    # Timeout must be logged
    assert Path(log_path).exists(), "Lock timeout log not created"
    records = [json.loads(line) for line in Path(log_path).read_text().splitlines() if line.strip()]
    assert len(records) >= 1
    assert records[0]["event"] == "lock_timeout"
    assert records[0]["queue_path"] == queue_path
