"""Unit tests for lib/queue_drainer.py."""

from __future__ import annotations

import json
import time

import pytest

from lib.queue_drainer import QueueDrainer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_drainer(tmp_path, active_tasks=0, max_parallel=5):
    """Create a QueueDrainer wired to temp files with controllable slot count."""
    queue_file = str(tmp_path / "dispatch-queue.json")
    tasks_file = str(tmp_path / "active-tasks.json")

    # Write a minimal active-tasks.json with the requested in_progress count
    tasks_data = {
        "version": 1,
        "tasks": [
            {"id": f"t-{i}", "status": "in_progress", "description": f"task {i}"}
            for i in range(active_tasks)
        ],
    }
    with open(tasks_file, "w") as fh:
        json.dump(tasks_data, fh)

    return QueueDrainer(
        queue_path=queue_file,
        tasks_path=tasks_file,
        max_parallel=max_parallel,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnqueue:
    def test_enqueue_adds_to_queue(self, tmp_path):
        drainer = make_drainer(tmp_path)
        agent_id = drainer.enqueue(
            prompt="Implement auth endpoint",
            description="Auth task",
            model="sonnet",
            priority=5,
        )

        assert agent_id is not None
        assert len(agent_id) == 36  # UUID format
        assert drainer.queue_length(status="queued") == 1

    def test_queue_persists_to_file(self, tmp_path):
        drainer = make_drainer(tmp_path)
        drainer.enqueue(prompt="Write tests", description="Test task", model="haiku")

        # Reload from disk
        with open(drainer.queue_path) as fh:
            saved = json.load(fh)

        assert len(saved) == 1
        assert saved[0]["description"] == "Test task"
        assert saved[0]["model"] == "haiku"
        assert saved[0]["status"] == "queued"

    def test_idempotent_enqueue_same_prompt_no_duplicate(self, tmp_path):
        drainer = make_drainer(tmp_path)
        prompt = "Deploy service X to staging"

        id1 = drainer.enqueue(prompt=prompt, description="Deploy")
        id2 = drainer.enqueue(prompt=prompt, description="Deploy again")

        # Same prompt → same id, still only 1 item
        assert id1 == id2
        assert drainer.queue_length(status="queued") == 1

    def test_different_prompts_create_separate_entries(self, tmp_path):
        drainer = make_drainer(tmp_path)
        drainer.enqueue(prompt="Task A", description="A")
        drainer.enqueue(prompt="Task B", description="B")

        assert drainer.queue_length(status="queued") == 2

    def test_empty_prompt_is_rejected(self, tmp_path):
        drainer = make_drainer(tmp_path)

        with pytest.raises(ValueError, match="prompt is empty"):
            drainer.enqueue(prompt="   ", description="lost payload")

        assert drainer.queue_length() == 0


class TestDequeuePriority:
    def test_dequeue_respects_priority(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=0, max_parallel=5)

        drainer.enqueue(prompt="Low priority work", priority=8)
        drainer.enqueue(prompt="Critical work", priority=1)
        drainer.enqueue(prompt="Normal work", priority=5)

        ready = drainer.get_ready_agents(max_count=3)

        # Should be sorted: 1, 5, 8
        priorities = [r["priority"] for r in ready]
        assert priorities == sorted(priorities)
        assert priorities[0] == 1

    def test_dequeue_respects_slot_availability(self, tmp_path):
        # 4 active tasks out of 5 max → only 1 slot free
        drainer = make_drainer(tmp_path, active_tasks=4, max_parallel=5)

        drainer.enqueue(prompt="Task alpha", priority=1)
        drainer.enqueue(prompt="Task beta", priority=2)
        drainer.enqueue(prompt="Task gamma", priority=3)

        ready = drainer.get_ready_agents()

        assert len(ready) == 1  # only 1 slot available
        assert ready[0]["priority"] == 1  # highest priority first

    def test_no_ready_agents_when_no_slots(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=5, max_parallel=5)

        drainer.enqueue(prompt="Task waiting", priority=1)
        ready = drainer.get_ready_agents()

        assert ready == []

    def test_empty_queue_returns_empty_list(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=0, max_parallel=5)
        ready = drainer.get_ready_agents()
        assert ready == []

    def test_corrupt_empty_prompt_item_is_quarantined_not_ready(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=0, max_parallel=5)
        corrupt = {
            "id": "empty-prompt",
            "prompt": "",
            "description": "agent task",
            "model": "sonnet",
            "priority": 5,
            "enqueued_at": "2026-05-20T00:00:00Z",
            "status": "queued",
            "_enqueued_epoch": time.time(),
            "_fingerprint": "e3b0c44298fc1c14",
        }
        with open(drainer.queue_path, "w") as fh:
            json.dump([corrupt], fh)

        ready = drainer.get_ready_agents(use_advisor=False)

        assert ready == []
        with open(drainer.queue_path) as fh:
            saved = json.load(fh)
        assert saved[0]["status"] == "corrupt"
        assert saved[0]["corruption_reason"] == "empty Agent prompt"


class TestMarkDispatched:
    def test_mark_dispatched_updates_status(self, tmp_path):
        drainer = make_drainer(tmp_path)
        agent_id = drainer.enqueue(prompt="Do something", description="Work")

        result = drainer.mark_dispatched(agent_id)

        assert result is True
        # Reload and check status on disk
        with open(drainer.queue_path) as fh:
            saved = json.load(fh)
        assert saved[0]["status"] == "dispatching"
        assert "dispatched_at" in saved[0]

    def test_mark_dispatched_nonexistent_returns_false(self, tmp_path):
        drainer = make_drainer(tmp_path)
        result = drainer.mark_dispatched("nonexistent-id")
        assert result is False

    def test_dispatching_items_not_returned_in_get_ready(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=0, max_parallel=5)

        id1 = drainer.enqueue(prompt="First task", priority=1)
        drainer.enqueue(prompt="Second task", priority=2)

        drainer.mark_dispatched(id1)

        ready = drainer.get_ready_agents()
        # Only the un-dispatched item should appear
        assert len(ready) == 1
        assert ready[0]["priority"] == 2


class TestRemoveCompleted:
    def test_remove_completed_removes_item(self, tmp_path):
        drainer = make_drainer(tmp_path)
        agent_id = drainer.enqueue(prompt="Completed task")

        result = drainer.remove_completed(agent_id)

        assert result is True
        assert drainer.queue_length() == 0

    def test_remove_completed_nonexistent_returns_false(self, tmp_path):
        drainer = make_drainer(tmp_path)
        result = drainer.remove_completed("ghost-id")
        assert result is False


class TestFormatDrainInstruction:
    def test_format_with_queued_agents_and_slots(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=2, max_parallel=5)
        drainer.enqueue(prompt="Task 1")
        drainer.enqueue(prompt="Task 2")
        drainer.enqueue(prompt="Task 3")

        msg = drainer.format_drain_instruction()

        assert "QUEUE DRAIN" in msg
        assert "3" in msg  # 3 slots available (5-2)
        assert "queued" in msg.lower()

    def test_format_empty_queue(self, tmp_path):
        drainer = make_drainer(tmp_path)
        msg = drainer.format_drain_instruction()
        assert "empty" in msg.lower()

    def test_format_no_slots_available(self, tmp_path):
        drainer = make_drainer(tmp_path, active_tasks=5, max_parallel=5)
        drainer.enqueue(prompt="Waiting task")
        msg = drainer.format_drain_instruction()
        assert "no slots" in msg.lower() or "queued" in msg.lower()


class TestQueueFileFormat:
    def test_queue_file_has_correct_schema(self, tmp_path):
        drainer = make_drainer(tmp_path)
        drainer.enqueue(
            prompt="Full prompt text here",
            description="Short desc",
            model="opus",
            priority=3,
        )

        with open(drainer.queue_path) as fh:
            items = json.load(fh)

        assert len(items) == 1
        item = items[0]
        assert "id" in item
        assert "prompt" in item
        assert "description" in item
        assert "model" in item
        assert "priority" in item
        assert "enqueued_at" in item
        assert "status" in item
        assert item["model"] == "opus"
        assert item["priority"] == 3
        assert item["status"] == "queued"

    def test_priority_clamped_to_valid_range(self, tmp_path):
        drainer = make_drainer(tmp_path)
        drainer.enqueue(prompt="High", priority=0)   # below min → 1
        drainer.enqueue(prompt="Low", priority=99)   # above max → 10

        with open(drainer.queue_path) as fh:
            items = json.load(fh)

        {i["description"][:4]: i["priority"] for i in items}
        # Both should be clamped (0→1, 99→10)
        for item in items:
            assert 1 <= item["priority"] <= 10
