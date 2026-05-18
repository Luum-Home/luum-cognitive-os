"""Behavioral tests for lib/outcome_failure_queue.py (ADR-209)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.outcome_failure_queue import (
    drain_queue,
    enqueue_failure,
    mark_processed,
    regression_count,
)

pytestmark = pytest.mark.unit


@pytest.fixture()
def queue_file(tmp_path: Path) -> Path:
    return tmp_path / "outcome-failure-queue.jsonl"


# ---------------------------------------------------------------------------
# enqueue_failure
# ---------------------------------------------------------------------------


def test_enqueue_creates_file_and_appends_entry(queue_file: Path) -> None:
    enqueue_failure(
        "exp-001",
        "failed",
        {"guardrail_regressed": True},
        queue_path=queue_file,
    )
    assert queue_file.exists()
    lines = queue_file.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["experiment_id"] == "exp-001"
    assert entry["outcome"] == "failed"
    assert entry["status"] == "pending"
    assert "enqueued_at" in entry


def test_enqueue_inconclusive_is_accepted(queue_file: Path) -> None:
    enqueue_failure("exp-002", "inconclusive", {}, queue_path=queue_file)
    entry = json.loads(queue_file.read_text().strip())
    assert entry["outcome"] == "inconclusive"


def test_enqueue_rejects_passing_outcome(queue_file: Path) -> None:
    with pytest.raises(ValueError, match="outcome must be one of"):
        enqueue_failure("exp-003", "passed", {}, queue_path=queue_file)


def test_enqueue_multiple_entries_are_appended(queue_file: Path) -> None:
    enqueue_failure("exp-001", "failed", {"a": 1}, queue_path=queue_file)
    enqueue_failure("exp-001", "inconclusive", {"b": 2}, queue_path=queue_file)
    lines = queue_file.read_text().strip().splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# drain_queue
# ---------------------------------------------------------------------------


def test_drain_returns_empty_list_when_no_file(tmp_path: Path) -> None:
    result = drain_queue(queue_path=tmp_path / "missing.jsonl")
    assert result == []


def test_drain_returns_pending_entries(queue_file: Path) -> None:
    enqueue_failure("exp-A", "failed", {}, queue_path=queue_file)
    enqueue_failure("exp-B", "inconclusive", {}, queue_path=queue_file)
    result = drain_queue(queue_path=queue_file)
    assert len(result) == 2
    ids = {e["experiment_id"] for e in result}
    assert ids == {"exp-A", "exp-B"}


# ---------------------------------------------------------------------------
# mark_processed
# ---------------------------------------------------------------------------


def test_mark_processed_updates_status(queue_file: Path) -> None:
    enqueue_failure("exp-X", "failed", {}, queue_path=queue_file)
    updated = mark_processed("exp-X", queue_path=queue_file)
    assert updated == 1
    remaining = drain_queue(queue_path=queue_file, status_filter="pending")
    assert remaining == []


def test_mark_processed_leaves_other_experiments_pending(queue_file: Path) -> None:
    enqueue_failure("exp-Y", "failed", {}, queue_path=queue_file)
    enqueue_failure("exp-Z", "inconclusive", {}, queue_path=queue_file)
    mark_processed("exp-Y", queue_path=queue_file)
    pending = drain_queue(queue_path=queue_file, status_filter="pending")
    assert len(pending) == 1
    assert pending[0]["experiment_id"] == "exp-Z"


def test_mark_processed_returns_zero_when_no_file(tmp_path: Path) -> None:
    result = mark_processed("exp-X", queue_path=tmp_path / "missing.jsonl")
    assert result == 0


# ---------------------------------------------------------------------------
# regression_count
# ---------------------------------------------------------------------------


def test_regression_count_counts_only_failed_pending(queue_file: Path) -> None:
    enqueue_failure("exp-1", "failed", {}, queue_path=queue_file)
    enqueue_failure("exp-2", "failed", {}, queue_path=queue_file)
    enqueue_failure("exp-3", "inconclusive", {}, queue_path=queue_file)
    assert regression_count(queue_path=queue_file) == 2


def test_regression_count_excludes_processed(queue_file: Path) -> None:
    enqueue_failure("exp-1", "failed", {}, queue_path=queue_file)
    mark_processed("exp-1", queue_path=queue_file)
    assert regression_count(queue_path=queue_file) == 0


def test_regression_count_zero_when_no_queue(tmp_path: Path) -> None:
    assert regression_count(queue_path=tmp_path / "missing.jsonl") == 0
