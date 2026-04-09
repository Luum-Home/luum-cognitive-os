"""Tests for lib/scheduled_drain.py — Phase 4A of agent orchestration plan."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_queue_file(tmp_dir: str, items: list) -> str:
    """Write a dispatch-queue.json and return its path."""
    queue_dir = os.path.join(tmp_dir, "tasks")
    os.makedirs(queue_dir, exist_ok=True)
    path = os.path.join(queue_dir, "dispatch-queue.json")
    with open(path, "w") as fh:
        json.dump(items, fh)
    return path


def _make_tasks_file(tmp_dir: str, tasks: list) -> str:
    """Write an active-tasks.json and return its path."""
    tasks_dir = os.path.join(tmp_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    path = os.path.join(tasks_dir, "active-tasks.json")
    with open(path, "w") as fh:
        json.dump({"tasks": tasks}, fh)
    return path


def _make_queued_item(item_id: str = "abc123", priority: int = 5) -> dict:
    """Build a minimal queued item dict."""
    import time
    return {
        "id": item_id,
        "prompt": f"Do something important for task {item_id}",
        "description": f"Test task {item_id}",
        "model": "sonnet",
        "priority": priority,
        "enqueued_at": "2026-04-09T10:00:00Z",
        "status": "queued",
        "_enqueued_epoch": time.time(),
        "_fingerprint": "deadbeef12345678",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDrainAndReport:
    """drain_and_report() — combined queue + health output."""

    def test_drain_and_report_with_empty_queue(self, tmp_path):
        """When the queue is empty the drain line says so and no error raised."""
        from lib.scheduled_drain import drain_and_report

        queue_path = str(tmp_path / "tasks" / "dispatch-queue.json")
        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")

        result = drain_and_report(
            queue_path=queue_path,
            tasks_path=tasks_path,
            max_parallel=5,
        )

        assert "QUEUE DRAIN" in result
        assert "empty" in result.lower()
        # Two sections separated by a blank line
        assert "\n\n" in result

    def test_drain_and_report_with_queued_agents(self, tmp_path):
        """When agents are queued the drain line reports ready count."""
        from lib.scheduled_drain import drain_and_report

        # Create a queue with one item
        tmp_dir = str(tmp_path)
        queue_path = _make_queue_file(tmp_dir, [_make_queued_item("id-001")])
        # No active tasks → all slots free
        tasks_path = _make_tasks_file(tmp_dir, [])

        result = drain_and_report(
            queue_path=queue_path,
            tasks_path=tasks_path,
            max_parallel=5,
        )

        assert "QUEUE DRAIN" in result
        # Should report at least 1 agent ready
        assert "ready" in result.lower() or "agent" in result.lower()

    def test_drain_and_report_no_slots_available(self, tmp_path):
        """When all slots are full the drain reports no slots available."""
        from lib.scheduled_drain import drain_and_report

        tmp_dir = str(tmp_path)
        queue_path = _make_queue_file(tmp_dir, [_make_queued_item("id-002")])
        # Fill all slots with in_progress tasks
        active_tasks = [
            {"id": f"t{i}", "status": "in_progress"} for i in range(5)
        ]
        tasks_path = _make_tasks_file(tmp_dir, active_tasks)

        result = drain_and_report(
            queue_path=queue_path,
            tasks_path=tasks_path,
            max_parallel=5,
        )

        assert "QUEUE DRAIN" in result
        assert "no slots" in result.lower() or "remain queued" in result.lower()

    def test_drain_and_report_returns_string(self, tmp_path):
        """drain_and_report always returns a plain string."""
        from lib.scheduled_drain import drain_and_report

        result = drain_and_report(
            queue_path=str(tmp_path / "tasks" / "q.json"),
            tasks_path=str(tmp_path / "tasks" / "t.json"),
            max_parallel=3,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_drain_and_report_includes_health_section(self, tmp_path):
        """Output has two sections (queue drain + health) separated by blank line."""
        from lib.scheduled_drain import drain_and_report

        result = drain_and_report(
            queue_path=str(tmp_path / "q.json"),
            tasks_path=str(tmp_path / "t.json"),
            max_parallel=5,
        )

        parts = result.split("\n\n", 1)
        assert len(parts) == 2, "Expected two sections separated by blank line"
        # First section is queue drain
        assert "QUEUE DRAIN" in parts[0]
        # Second section is health (or fallback message)
        assert "AGENT HEALTH" in parts[1] or "health" in parts[1].lower() or "monitor" in parts[1].lower()


class TestCronSpec:
    """get_cron_create_spec() — CronCreate specification format."""

    def test_cron_spec_format(self):
        """Spec has the required keys for CronCreate."""
        from lib.scheduled_drain import get_cron_create_spec

        spec = get_cron_create_spec()

        assert isinstance(spec, dict)
        assert "cron" in spec
        assert "prompt" in spec
        assert "recurring" in spec
        assert "description" in spec

    def test_cron_spec_every_five_minutes(self):
        """Default cron expression runs every 5 minutes."""
        from lib.scheduled_drain import get_cron_create_spec

        spec = get_cron_create_spec()

        assert "*/5" in spec["cron"], f"Expected */5 in cron expression, got: {spec['cron']}"

    def test_cron_spec_prompt_contains_drain_call(self):
        """Prompt instructs the scheduled session to call drain_and_report."""
        from lib.scheduled_drain import get_cron_create_spec

        spec = get_cron_create_spec()

        assert "drain_and_report" in spec["prompt"]
        assert "scheduled_drain" in spec["prompt"]

    def test_cron_spec_prompt_handles_empty_queue(self):
        """Prompt explicitly tells the session to stop if queue is empty."""
        from lib.scheduled_drain import get_cron_create_spec

        spec = get_cron_create_spec()

        assert "empty" in spec["prompt"].lower()
        assert "reschedule" in spec["prompt"].lower() or "not reschedule" in spec["prompt"].lower()

    def test_cron_spec_recurring_is_true(self):
        """Spec marks the task as recurring (runs on the interval)."""
        from lib.scheduled_drain import get_cron_create_spec

        spec = get_cron_create_spec()

        assert spec["recurring"] is True


class TestShouldScheduleDrain:
    """should_schedule_drain() — gate for creating the CronCreate task."""

    def test_should_schedule_when_queue_has_items(self, tmp_path):
        """Returns True when there are queued items."""
        from lib.scheduled_drain import should_schedule_drain

        tmp_dir = str(tmp_path)
        queue_path = _make_queue_file(tmp_dir, [_make_queued_item("id-x")])
        tasks_path = _make_tasks_file(tmp_dir, [])

        assert should_schedule_drain(queue_path=queue_path, tasks_path=tasks_path) is True

    def test_should_not_schedule_when_queue_empty(self, tmp_path):
        """Returns False when queue is empty."""
        from lib.scheduled_drain import should_schedule_drain

        queue_path = str(tmp_path / "tasks" / "dispatch-queue.json")
        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")

        assert should_schedule_drain(queue_path=queue_path, tasks_path=tasks_path) is False

    def test_should_schedule_when_item_is_dispatching(self, tmp_path):
        """Returns True for items with 'dispatching' status (launch in progress)."""
        import time
        from lib.scheduled_drain import should_schedule_drain

        dispatching_item = {
            "id": "disp-001",
            "prompt": "some task",
            "description": "test",
            "model": "sonnet",
            "priority": 5,
            "enqueued_at": "2026-04-09T10:00:00Z",
            "status": "dispatching",
            "_enqueued_epoch": time.time(),
            "_fingerprint": "aabbccdd",
        }
        tmp_dir = str(tmp_path)
        queue_path = _make_queue_file(tmp_dir, [dispatching_item])
        tasks_path = _make_tasks_file(tmp_dir, [])

        assert should_schedule_drain(queue_path=queue_path, tasks_path=tasks_path) is True

    def test_should_not_schedule_when_queue_file_missing(self, tmp_path):
        """Returns False gracefully when queue file doesn't exist yet."""
        from lib.scheduled_drain import should_schedule_drain

        queue_path = str(tmp_path / "nonexistent" / "q.json")
        tasks_path = str(tmp_path / "nonexistent" / "t.json")

        # Should not raise — just return False
        result = should_schedule_drain(queue_path=queue_path, tasks_path=tasks_path)
        assert result is False

    def test_should_not_schedule_with_only_completed_items(self, tmp_path):
        """Returns False when all items have been removed (completed)."""
        # Empty list = all items removed
        from lib.scheduled_drain import should_schedule_drain

        tmp_dir = str(tmp_path)
        queue_path = _make_queue_file(tmp_dir, [])
        tasks_path = _make_tasks_file(tmp_dir, [])

        assert should_schedule_drain(queue_path=queue_path, tasks_path=tasks_path) is False
