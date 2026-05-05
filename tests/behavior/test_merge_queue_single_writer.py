from __future__ import annotations

import pytest

from lib.merge_queue import head_drift, try_acquire_worker_lock

pytestmark = pytest.mark.behavior


def test_merge_queue_worker_lock_serializes_landing_attempts(tmp_path):
    queue_file = tmp_path / "merge-queue.jsonl"
    first = try_acquire_worker_lock(queue_file)
    assert first is not None
    try:
        assert try_acquire_worker_lock(queue_file) is None
    finally:
        first.close()


def test_main_head_drift_blocks_landing_until_refetch_or_rebase() -> None:
    decision = head_drift(current_head="remote-head-b", expected_head="remote-head-a")

    assert decision["ok_to_land"] is False
    assert decision["action"] == "refetch-or-rebase"
