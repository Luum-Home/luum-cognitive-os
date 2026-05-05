from __future__ import annotations

import pytest

from lib.merge_queue import enqueue, record_validation_lane, status
from lib.validation_lanes import recommend_lane

pytestmark = pytest.mark.behavior


def test_merge_queue_report_captures_recommended_and_executed_lane(tmp_path):
    queue_file = tmp_path / "merge-queue.jsonl"
    entry_id = enqueue("session/runtime", "s1", queue_path=queue_file)
    rec = recommend_lane(["scripts/cos_validate.py"])

    assert record_validation_lane(
        entry_id,
        recommended_lane=rec.recommended_lane,
        executed_lane="landing",
        rationale=rec.rationale,
        queue_path=queue_file,
    )
    entry = status(entry_id, queue_path=queue_file)

    assert entry["recommended_lane"] == "landing"
    assert entry["executed_lane"] == "landing"
    assert entry["validation_rationale"]
