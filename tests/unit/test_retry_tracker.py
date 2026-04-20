"""Unit tests for lib/retry_tracker.py (ADR-038 Gap #7).

Tests:
1. record_attempt writes a record to the JSONL.
2. approach_seen returns True when the same hash was recorded.
3. approaches_tried returns ordered list of all recorded hashes.
4. concurrent-safe: two distinct agent_ids are isolated from each other.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.retry_tracker import approach_seen, approaches_tried, record_attempt


@pytest.fixture()
def tmp_project(tmp_path):
    """Minimal project dir with metrics dir pre-created."""
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    return tmp_path


class TestRetryTracker:
    def test_record_writes_jsonl(self, tmp_project):
        """record_attempt appends a valid JSON record to retry-tracker.jsonl."""
        record_attempt("agent-1", "try-direct-import", project_dir=str(tmp_project))

        jsonl = tmp_project / ".cognitive-os" / "metrics" / "retry-tracker.jsonl"
        assert jsonl.exists(), "retry-tracker.jsonl should be created"

        lines = [l for l in jsonl.read_text().splitlines() if l.strip()]
        assert len(lines) == 1

        rec = json.loads(lines[0])
        assert rec["agent_id"] == "agent-1"
        assert rec["approach_hash"] == "try-direct-import"
        assert "timestamp_epoch" in rec

    def test_approach_seen_true_when_recorded(self, tmp_project):
        """approach_seen returns True when the hash has been recorded."""
        record_attempt("agent-2", "patch-and-retry", project_dir=str(tmp_project))

        assert approach_seen("agent-2", "patch-and-retry", project_dir=str(tmp_project)) is True

    def test_approach_seen_false_when_not_recorded(self, tmp_project):
        """approach_seen returns False for an unknown hash."""
        record_attempt("agent-3", "first-approach", project_dir=str(tmp_project))

        assert approach_seen("agent-3", "brand-new-approach", project_dir=str(tmp_project)) is False

    def test_approaches_tried_returns_ordered_list(self, tmp_project):
        """approaches_tried returns all hashes in insertion order."""
        record_attempt("agent-4", "approach-A", project_dir=str(tmp_project))
        record_attempt("agent-4", "approach-B", project_dir=str(tmp_project))
        record_attempt("agent-4", "approach-C", project_dir=str(tmp_project))

        result = approaches_tried("agent-4", project_dir=str(tmp_project))
        assert result == ["approach-A", "approach-B", "approach-C"]

    def test_agent_ids_are_isolated(self, tmp_project):
        """Two distinct agent_ids do not see each other's approach hashes."""
        record_attempt("agent-X", "shared-name", project_dir=str(tmp_project))

        # agent-Y has not recorded anything
        assert approach_seen("agent-Y", "shared-name", project_dir=str(tmp_project)) is False
        assert approaches_tried("agent-Y", project_dir=str(tmp_project)) == []

    def test_approaches_tried_empty_when_no_file(self, tmp_project):
        """approaches_tried returns [] when the JSONL does not exist yet."""
        result = approaches_tried("ghost-agent", project_dir=str(tmp_project))
        assert result == []
