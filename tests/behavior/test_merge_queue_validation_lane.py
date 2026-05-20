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


def test_merge_queue_cli_enqueue_records_recommended_lane(tmp_path):
    import json
    import os
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    queue_file = tmp_path / "merge-queue.jsonl"
    env = {**os.environ, "MERGE_QUEUE_PATH": str(queue_file)}

    result = subprocess.run(
        ["bash", str(repo / "scripts" / "cos-merge-queue.sh"), "enqueue", "session/cli", "s-cli", "hooks/direct-main-guard.sh"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    entry_id = result.stdout.strip()
    rows = [json.loads(line) for line in queue_file.read_text(encoding="utf-8").splitlines()]
    entry = next(row for row in rows if row["id"] == entry_id)
    assert entry["recommended_lane"] == "laptop"
    assert entry["validation_rationale"] == ["hook changes require laptop lane"]
