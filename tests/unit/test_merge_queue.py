"""
Unit tests for lib/merge_queue.py  — P2.2 (ADR-116).

Coverage targets (8+ cases):
1.  enqueue / peek / dequeue roundtrip
2.  status query
3.  concurrent enqueue from 2 processes — no line interleaving
4.  list_pending filter
5.  dequeue marks completed
6.  failed dequeue keeps notes
7.  corrupt line tolerated (skipped on read)
8.  lock contention — 2 workers can't run concurrently (flock -n)
"""

from __future__ import annotations

import fcntl
import json
import multiprocessing
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure the repo root is on PYTHONPATH so ``lib.merge_queue`` resolves.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.merge_queue import (  # noqa: E402
    dequeue,
    enqueue,
    list_pending,
    peek,
    status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def queue_file(tmp_path):
    """Return a temporary queue file path."""
    return tmp_path / "merge-queue.jsonl"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _enqueue(branch: str, sid: str, qf: Path) -> str:
    return enqueue(branch, sid, queue_path=qf)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestEnqueuePeekDequeue:
    """Case 1: basic roundtrip."""

    def test_roundtrip(self, queue_file):
        entry_id = enqueue("session/abc", "s1", queue_path=queue_file)
        assert isinstance(entry_id, str) and len(entry_id) == 36  # UUID4

        peeked = peek(queue_path=queue_file)
        assert peeked is not None
        assert peeked["id"] == entry_id
        assert peeked["session_branch"] == "session/abc"
        assert peeked["session_id"] == "s1"
        assert peeked["status"] == "queued"
        assert peeked["completed_at"] is None

        ok = dequeue(entry_id, status="completed", queue_path=queue_file)
        assert ok is True

        # After dequeue the entry is terminal — peek should return None.
        assert peek(queue_path=queue_file) is None


class TestStatusQuery:
    """Case 2: status() reads a single entry by id."""

    def test_status_found(self, queue_file):
        eid = enqueue("session/x", "s2", queue_path=queue_file)
        entry = status(eid, queue_path=queue_file)
        assert entry is not None
        assert entry["id"] == eid
        assert entry["status"] == "queued"

    def test_status_not_found(self, queue_file):
        assert status("00000000-0000-0000-0000-000000000000", queue_path=queue_file) is None


class TestConcurrentEnqueue:
    """Case 3: 2 processes enqueue simultaneously — no JSONL line interleaving."""

    @staticmethod
    def _worker(branch: str, sid: str, queue_file: str, result_queue):
        try:
            from lib.merge_queue import enqueue as _enqueue  # noqa: PLC0415
            eid = _enqueue(branch, sid, queue_path=Path(queue_file))
            result_queue.put(("ok", eid))
        except Exception as exc:  # noqa: BLE001
            result_queue.put(("err", str(exc)))

    def test_no_interleaving(self, queue_file, tmp_path):
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        p1 = multiprocessing.Process(
            target=self._worker,
            args=("session/p1", "s-p1", str(queue_file), result_queue),
        )
        p2 = multiprocessing.Process(
            target=self._worker,
            args=("session/p2", "s-p2", str(queue_file), result_queue),
        )

        p1.start()
        p2.start()
        p1.join(timeout=10)
        p2.join(timeout=10)

        results = [result_queue.get_nowait() for _ in range(2)]
        for outcome, val in results:
            assert outcome == "ok", f"enqueue failed: {val}"

        # Every line must be valid JSON.
        lines = [l for l in queue_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        parsed = [json.loads(l) for l in lines]
        ids = {e["id"] for e in parsed}
        assert len(ids) == 2, "expected 2 distinct entries, lines may have interleaved"


class TestListPending:
    """Case 4: list_pending returns only queued/in-progress entries."""

    def test_filters_terminal(self, queue_file):
        id1 = enqueue("session/a", "s1", queue_path=queue_file)
        id2 = enqueue("session/b", "s2", queue_path=queue_file)
        dequeue(id1, status="completed", queue_path=queue_file)

        pending = list_pending(queue_path=queue_file)
        assert len(pending) == 1
        assert pending[0]["id"] == id2

    def test_empty_queue(self, queue_file):
        assert list_pending(queue_path=queue_file) == []


class TestDequeueCompleted:
    """Case 5: dequeue marks entry completed with timestamp."""

    def test_completed_timestamp(self, queue_file):
        eid = enqueue("session/c", "s3", queue_path=queue_file)
        dequeue(eid, status="completed", queue_path=queue_file)

        entry = status(eid, queue_path=queue_file)
        assert entry["status"] == "completed"
        assert entry["completed_at"] is not None


class TestDequeueFailedNotes:
    """Case 6: failed dequeue preserves notes."""

    def test_notes_preserved(self, queue_file):
        eid = enqueue("session/d", "s4", queue_path=queue_file)
        dequeue(eid, status="failed", notes="pytest smoke failed", queue_path=queue_file)

        entry = status(eid, queue_path=queue_file)
        assert entry["status"] == "failed"
        assert entry["notes"] == "pytest smoke failed"

    def test_invalid_status_raises(self, queue_file):
        eid = enqueue("session/e", "s5", queue_path=queue_file)
        with pytest.raises(ValueError, match="status must be"):
            dequeue(eid, status="bananas", queue_path=queue_file)


class TestCorruptLineTolerated:
    """Case 7: corrupt lines in the JSONL are silently skipped."""

    def test_corrupt_line_skipped(self, queue_file):
        eid = enqueue("session/f", "s6", queue_path=queue_file)

        # Inject a corrupt line after the valid entry.
        with queue_file.open("a") as fh:
            fh.write("NOT VALID JSON }{}\n")

        # Enqueue again — should succeed despite corrupt line.
        eid2 = enqueue("session/g", "s7", queue_path=queue_file)

        # peek/list_pending should work and return valid entries only.
        pending = list_pending(queue_path=queue_file)
        ids = {e["id"] for e in pending}
        assert eid in ids
        assert eid2 in ids
        # No entry from the corrupt line.
        assert len(pending) == 2


class TestLockContention:
    """Case 8: two workers cannot hold the queue lock concurrently."""

    def test_flock_exclusive(self, queue_file):
        # Use a lock file matching what the worker uses.
        lock_file = queue_file.with_suffix(".lock")
        lock_file.touch()

        # Acquire LOCK_EX from this process.
        with lock_file.open("a") as holder_fh:
            fcntl.flock(holder_fh, fcntl.LOCK_EX)
            try:
                # Try a non-blocking lock from a subprocess — must fail.
                result = subprocess.run(
                    [
                        "python3",
                        "-c",
                        (
                            f"import fcntl; f=open('{lock_file}','a'); "
                            "r=fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); "
                            "print('acquired')"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # Subprocess should raise BlockingIOError and exit non-zero.
                assert result.returncode != 0, (
                    "Expected subprocess to fail acquiring lock, but it succeeded"
                )
            finally:
                fcntl.flock(holder_fh, fcntl.LOCK_UN)

from lib.merge_queue import head_drift, record_validation_lane, try_acquire_worker_lock, worker_lock_path  # noqa: E402


def test_worker_lock_is_single_writer(queue_file):
    first = try_acquire_worker_lock(queue_file)
    assert first is not None
    try:
        assert try_acquire_worker_lock(queue_file) is None
        assert worker_lock_path(queue_file).name == "merge-queue.worker.lock"
    finally:
        first.close()


def test_head_drift_requires_refetch_or_rebase():
    decision = head_drift(current_head="new", expected_head="old")

    assert decision["ok_to_land"] is False
    assert decision["action"] == "refetch-or-rebase"
    assert "drifted" in decision["reason"]


def test_merge_queue_records_validation_lane_fields(queue_file):
    entry_id = enqueue("session/lane", "s-lane", queue_path=queue_file)

    assert record_validation_lane(entry_id, recommended_lane="landing", executed_lane="fast", rationale=["runtime script changed"], queue_path=queue_file)
    entry = status(entry_id, queue_path=queue_file)

    assert entry["recommended_lane"] == "landing"
    assert entry["executed_lane"] == "fast"
    assert entry["validation_rationale"] == ["runtime script changed"]


def test_enqueue_records_recommended_lane_from_expected_files(queue_file):
    entry_id = enqueue("session/hook", "s-hook", expected_files=["hooks/direct-main-guard.sh"], queue_path=queue_file)

    entry = status(entry_id, queue_path=queue_file)

    assert entry["recommended_lane"] == "laptop"
    assert entry["executed_lane"] is None
    assert entry["validation_rationale"] == ["hook changes require laptop lane"]
