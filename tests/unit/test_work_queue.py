"""Tests for lib/work_queue.py — persistent cross-session work queue."""

import json
import pytest
from lib.work_queue import WorkQueue


@pytest.fixture
def queue_file(tmp_path):
    return str(tmp_path / "work-queue.json")


@pytest.fixture
def populated_queue(queue_file):
    data = {
        "version": 1,
        "last_updated": "2026-04-11",
        "priority_queue": [
            {"id": "task-a", "description": "First task", "priority": 1,
             "status": "pending", "depends_on": [], "context": "ctx-a"},
            {"id": "task-b", "description": "Depends on A", "priority": 2,
             "status": "pending", "depends_on": ["task-a"], "context": "ctx-b"},
            {"id": "task-c", "description": "Done task", "priority": 1,
             "status": "completed", "depends_on": []},
        ],
        "user_concerns": ["pip-first always"],
        "completed_this_sprint": ["WS1 done"],
    }
    with open(queue_file, "w") as f:
        json.dump(data, f)
    return queue_file


class TestWorkQueueBasics:
    def test_load_missing_file(self, queue_file):
        q = WorkQueue(queue_file)
        assert q.get_pending() == []

    def test_load_existing(self, populated_queue):
        q = WorkQueue(populated_queue)
        assert len(q.get_pending()) == 2

    def test_get_pending_excludes_completed(self, populated_queue):
        q = WorkQueue(populated_queue)
        ids = [t["id"] for t in q.get_pending()]
        assert "task-c" not in ids

    def test_get_pending_sorted_by_priority(self, populated_queue):
        q = WorkQueue(populated_queue)
        pending = q.get_pending()
        assert pending[0]["id"] == "task-a"  # priority 1
        assert pending[1]["id"] == "task-b"  # priority 2


class TestDependencies:
    def test_get_next_respects_deps(self, populated_queue):
        q = WorkQueue(populated_queue)
        # task-b depends on task-a, so next should be task-a
        nxt = q.get_next()
        assert nxt["id"] == "task-a"

    def test_get_next_after_completion(self, populated_queue):
        q = WorkQueue(populated_queue)
        q.complete_task("task-a", "done")
        nxt = q.get_next()
        assert nxt["id"] == "task-b"

    def test_get_next_all_done(self, populated_queue):
        q = WorkQueue(populated_queue)
        q.complete_task("task-a")
        q.complete_task("task-b")
        assert q.get_next() is None


class TestMutations:
    def test_complete_task(self, populated_queue):
        q = WorkQueue(populated_queue)
        q.complete_task("task-a", "finished")
        reloaded = WorkQueue(populated_queue)
        task = next(t for t in reloaded._data["priority_queue"] if t["id"] == "task-a")
        assert task["status"] == "completed"
        assert "completed_at" in task

    def test_add_task(self, queue_file):
        q = WorkQueue(queue_file)
        assert q.add_task("new-task", "New description", priority=2)
        reloaded = WorkQueue(queue_file)
        assert len(reloaded.get_pending()) == 1

    def test_add_duplicate_skipped(self, populated_queue):
        q = WorkQueue(populated_queue)
        assert not q.add_task("task-a", "Duplicate")

    def test_add_concern(self, populated_queue):
        q = WorkQueue(populated_queue)
        q.add_concern("new concern")
        assert "new concern" in q.get_concerns()

    def test_add_duplicate_concern_skipped(self, populated_queue):
        q = WorkQueue(populated_queue)
        q.add_concern("pip-first always")
        assert q.get_concerns().count("pip-first always") == 1

    def test_record_completion(self, populated_queue):
        q = WorkQueue(populated_queue)
        q.record_completion("WS2 done")
        assert "WS2 done" in q._data["completed_this_sprint"]


class TestFormatting:
    def test_format_brief_has_header(self, populated_queue):
        q = WorkQueue(populated_queue)
        brief = q.format_session_brief()
        assert "WORK QUEUE BRIEF" in brief

    def test_format_brief_shows_next(self, populated_queue):
        q = WorkQueue(populated_queue)
        brief = q.format_session_brief()
        assert "task-a" in brief

    def test_format_brief_shows_concerns(self, populated_queue):
        q = WorkQueue(populated_queue)
        brief = q.format_session_brief()
        assert "pip-first" in brief

    def test_format_brief_empty_queue(self, queue_file):
        q = WorkQueue(queue_file)
        brief = q.format_session_brief()
        assert "Pending: 0" in brief


class TestPlanSync:
    def test_sync_completed_plan(self, populated_queue, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        (plans_dir / "task-a.md").write_text("# Plan\n**Status**: COMPLETED\n")
        q = WorkQueue(populated_queue)
        synced = q.sync_from_plans(str(plans_dir))
        assert synced == 1
        reloaded = WorkQueue(populated_queue)
        task = next(t for t in reloaded._data["priority_queue"] if t["id"] == "task-a")
        assert task["status"] == "completed"

    def test_sync_no_plans_dir(self, populated_queue):
        q = WorkQueue(populated_queue)
        assert q.sync_from_plans("/nonexistent") == 0


class TestContextSize:
    def test_brief_under_2000_chars(self, queue_file):
        """Brief must not saturate context. Max 2000 chars."""
        q = WorkQueue(queue_file)
        for i in range(20):
            q.add_task(f"task-{i}", f"Description for task {i} " * 5, priority=i % 5)
        brief = q.format_session_brief()
        assert len(brief) < 2000, f"Brief is {len(brief)} chars, should be under 2000"
