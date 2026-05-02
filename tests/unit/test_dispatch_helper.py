"""Unit tests for lib/dispatch_helper.py

Covers:
- check_slot_availability: slot counting, config reading, degradation
- enqueue_agent / dequeue_ready_agents: round-trip cycle
- format_dispatch_status: string output format
- Graceful degradation: missing config, missing tasks file, bad JSON
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_tasks(path: str, tasks: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"version": 1, "tasks": tasks}, fh)


def _write_config(path: str, max_parallel: int = 5) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(
            f"project:\n  phase: reconstruction\n"
            f"resources:\n  compute:\n    max_parallel_agents: {max_parallel}\n"
        )


def _iso_age(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ---------------------------------------------------------------------------
# check_slot_availability
# ---------------------------------------------------------------------------


class TestCheckSlotAvailability:
    """Tests for check_slot_availability()."""

    def test_available_when_no_active_tasks(self, tmp_path):
        """Returns available=True when no tasks are in progress."""
        from lib.dispatch_helper import check_slot_availability

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        _write_tasks(tasks_path, [])
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=3)

        result = check_slot_availability(config_path=cfg_path, tasks_path=tasks_path)

        assert result["available"] is True
        assert result["active"] == 0
        assert result["max"] == 3
        assert isinstance(result["queued"], int)

    def test_not_available_when_full(self, tmp_path):
        """Returns available=False when active == max."""
        from lib.dispatch_helper import check_slot_availability

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=2)

        in_progress = [
            {"id": f"t{i}", "status": "in_progress", "description": "x"}
            for i in range(2)
        ]
        _write_tasks(tasks_path, in_progress)

        result = check_slot_availability(config_path=cfg_path, tasks_path=tasks_path)

        assert result["available"] is False
        assert result["active"] == 2
        assert result["max"] == 2

    def test_counts_only_in_progress_tasks(self, tmp_path):
        """Only dispatch-active in_progress tasks count toward the active slot total."""
        from lib.dispatch_helper import check_slot_availability

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=5)

        mixed = [
            {"id": "t1", "status": "completed", "description": "done"},
            {"id": "t2", "status": "in_progress", "description": "running", "pid": os.getpid()},
            {"id": "t3", "status": "pending", "description": "waiting"},
            {"id": "t4", "status": "failed", "description": "dead"},
            {"id": "t5", "status": "in_progress", "description": "starting", "pid": None, "started_at": _iso_age(30)},
        ]
        _write_tasks(tasks_path, mixed)

        result = check_slot_availability(config_path=cfg_path, tasks_path=tasks_path)

        assert result["active"] == 2

    def test_excludes_dead_pid_and_stale_pidless_in_progress(self, tmp_path):
        """Zombie and stale-starting in_progress records must not saturate slots."""
        from lib.dispatch_helper import check_slot_availability

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=5)
        _write_tasks(
            tasks_path,
            [
                {"id": "live", "status": "in_progress", "pid": os.getpid()},
                {"id": "dead", "status": "in_progress", "pid": 99999999},
                {
                    "id": "stale-pidless",
                    "status": "in_progress",
                    "pid": None,
                    "started_at": _iso_age(4000),
                },
                {
                    "id": "fresh-pidless",
                    "status": "in_progress",
                    "pid": None,
                    "started_at": _iso_age(30),
                },
                {"id": "pending", "status": "pending", "pid": None},
            ],
        )

        result = check_slot_availability(config_path=cfg_path, tasks_path=tasks_path)

        assert result["active"] == 2

    def test_defaults_when_config_missing(self, tmp_path):
        """Falls back to DEFAULT_MAX_PARALLEL when config file is absent."""
        from lib.dispatch_helper import _DEFAULT_MAX_PARALLEL, check_slot_availability

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        _write_tasks(tasks_path, [])

        result = check_slot_availability(
            config_path="/nonexistent/path.yaml",
            tasks_path=tasks_path,
        )

        assert result["max"] == _DEFAULT_MAX_PARALLEL
        assert isinstance(result["available"], bool)

    def test_defaults_when_tasks_file_missing(self, tmp_path):
        """Returns active=0 when active-tasks.json does not exist."""
        from lib.dispatch_helper import check_slot_availability

        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=4)

        result = check_slot_availability(
            config_path=cfg_path,
            tasks_path="/nonexistent/tasks.json",
        )

        assert result["active"] == 0
        assert result["available"] is True

    def test_defaults_when_tasks_file_bad_json(self, tmp_path):
        """Returns active=0 on malformed JSON rather than raising."""
        from lib.dispatch_helper import check_slot_availability

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        os.makedirs(os.path.dirname(tasks_path), exist_ok=True)
        with open(tasks_path, "w") as fh:
            fh.write("not json {{{")

        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=5)

        result = check_slot_availability(config_path=cfg_path, tasks_path=tasks_path)

        assert result["active"] == 0
        assert "available" in result

    def test_result_contains_all_keys(self, tmp_path):
        """Result dict always contains the four required keys."""
        from lib.dispatch_helper import check_slot_availability

        result = check_slot_availability(
            config_path="/nonexistent.yaml",
            tasks_path="/nonexistent-tasks.json",
        )

        assert set(result.keys()) >= {"available", "active", "max", "queued"}


# ---------------------------------------------------------------------------
# enqueue_agent / dequeue_ready_agents
# ---------------------------------------------------------------------------


class TestEnqueueDequeue:
    """Tests for enqueue_agent() and dequeue_ready_agents()."""

    def test_enqueue_returns_string_id(self, tmp_path):
        """enqueue_agent() returns a non-empty string queue_id."""
        from lib.dispatch_helper import enqueue_agent
        from lib.rate_limiter import RateLimitQueue

        queue_path = str(tmp_path / "queue.json")
        mock_queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=0)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            queue_id = enqueue_agent("Run the test suite", priority=3)

        assert isinstance(queue_id, str)
        assert len(queue_id) > 0
        assert queue_id not in ("queue-unavailable", "queue-error")

    def test_enqueue_dequeue_round_trip(self, tmp_path):
        """An enqueued agent is returned by dequeue_ready_agents()."""
        from lib.dispatch_helper import dequeue_ready_agents, enqueue_agent
        from lib.rate_limiter import RateLimitQueue

        queue_path = str(tmp_path / "queue.json")
        # cooldown_seconds=0 so items are immediately eligible
        mock_queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=0)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            queue_id = enqueue_agent("Deploy staging", priority=2)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            ready = dequeue_ready_agents()

        assert len(ready) == 1
        item = ready[0]
        assert item["queue_id"] == queue_id
        assert item["description"] == "Deploy staging"
        assert item["priority"] == 2
        assert "enqueued_at" in item

    def test_dequeue_filters_non_agent_launch_items(self, tmp_path):
        """dequeue_ready_agents() only returns agent_launch items."""
        from lib.dispatch_helper import dequeue_ready_agents
        from lib.rate_limiter import RateLimitQueue

        queue_path = str(tmp_path / "queue.json")
        mock_queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=0)
        # Enqueue a non-agent_launch item directly
        mock_queue.enqueue("tool_call", {"description": "some tool"}, priority=5)
        mock_queue.enqueue("agent_launch", {"description": "real agent"}, priority=5)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            ready = dequeue_ready_agents()

        assert all(item.get("description") != "some tool" for item in ready)
        assert any(item["description"] == "real agent" for item in ready)

    def test_dequeue_returns_empty_when_nothing_ready(self, tmp_path):
        """Returns empty list when queue is empty or nothing eligible yet."""
        from lib.dispatch_helper import dequeue_ready_agents
        from lib.rate_limiter import RateLimitQueue

        queue_path = str(tmp_path / "queue.json")
        # cooldown_seconds=3600 means nothing is ready yet
        mock_queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)
        mock_queue.enqueue("agent_launch", {"description": "later"}, priority=5)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            ready = dequeue_ready_agents()

        assert ready == []

    def test_priority_clamped_to_valid_range(self, tmp_path):
        """Priority outside 1–10 is silently clamped."""
        from lib.dispatch_helper import enqueue_agent
        from lib.rate_limiter import RateLimitQueue

        queue_path = str(tmp_path / "queue.json")
        mock_queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=0)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            enqueue_agent("too high", priority=99)
            enqueue_agent("too low", priority=-5)

        items = mock_queue.peek()
        for item in items:
            assert 1 <= item["priority"] <= 10

    def test_enqueue_returns_fallback_when_queue_unavailable(self):
        """Returns 'queue-unavailable' gracefully when import fails."""
        from lib.dispatch_helper import enqueue_agent

        with patch("lib.dispatch_helper._get_queue", return_value=None):
            result = enqueue_agent("anything")

        assert result == "queue-unavailable"

    def test_dequeue_returns_empty_when_queue_unavailable(self):
        """Returns [] gracefully when queue cannot be reached."""
        from lib.dispatch_helper import dequeue_ready_agents

        with patch("lib.dispatch_helper._get_queue", return_value=None):
            result = dequeue_ready_agents()

        assert result == []


# ---------------------------------------------------------------------------
# format_dispatch_status
# ---------------------------------------------------------------------------


class TestFormatDispatchStatus:
    """Tests for format_dispatch_status()."""

    def test_contains_slot_counts(self, tmp_path):
        """Output includes active/max slot ratio."""
        from lib.dispatch_helper import format_dispatch_status

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=4)
        _write_tasks(
            tasks_path,
            [{"id": "t1", "status": "in_progress", "description": "x"}],
        )

        status = format_dispatch_status(config_path=cfg_path, tasks_path=tasks_path)

        assert "1/4" in status

    def test_shows_available_when_slots_open(self, tmp_path):
        """Shows AVAILABLE when active < max."""
        from lib.dispatch_helper import format_dispatch_status

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=5)
        _write_tasks(tasks_path, [])

        status = format_dispatch_status(config_path=cfg_path, tasks_path=tasks_path)

        assert "AVAILABLE" in status

    def test_shows_full_when_no_slots(self, tmp_path):
        """Shows FULL when active == max."""
        from lib.dispatch_helper import format_dispatch_status

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=2)
        _write_tasks(
            tasks_path,
            [
                {"id": "t1", "status": "in_progress", "description": "x"},
                {"id": "t2", "status": "in_progress", "description": "y"},
            ],
        )

        status = format_dispatch_status(config_path=cfg_path, tasks_path=tasks_path)

        assert "FULL" in status

    def test_returns_string(self, tmp_path):
        """Always returns a string, even with missing files."""
        from lib.dispatch_helper import format_dispatch_status

        status = format_dispatch_status(
            config_path="/nonexistent.yaml",
            tasks_path="/nonexistent-tasks.json",
        )

        assert isinstance(status, str)
        assert len(status) > 0

    def test_shows_queued_count(self, tmp_path):
        """Queued count is mentioned in the output string."""
        from lib.dispatch_helper import format_dispatch_status
        from lib.rate_limiter import RateLimitQueue

        tasks_path = str(tmp_path / "tasks" / "active-tasks.json")
        cfg_path = str(tmp_path / "cognitive-os.yaml")
        _write_config(cfg_path, max_parallel=5)
        _write_tasks(tasks_path, [])

        queue_path = str(tmp_path / "queue.json")
        mock_queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)
        mock_queue.enqueue("agent_launch", {"description": "waiting"}, priority=5)

        with patch("lib.dispatch_helper._get_queue", return_value=mock_queue):
            status = format_dispatch_status(
                config_path=cfg_path, tasks_path=tasks_path
            )

        # Should mention 1 queued item
        assert "1 queued" in status


# ---------------------------------------------------------------------------
# Module-level import smoke test
# ---------------------------------------------------------------------------


class TestModuleImport:
    """Verifies no heavy computation runs at import time."""

    def test_import_is_fast(self):
        """Module can be imported without triggering file I/O on import."""
        import importlib
        import time
        import lib.dispatch_helper as mod

        start = time.monotonic()
        importlib.reload(mod)  # Re-import to confirm no side effects
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"import took {elapsed:.2f}s — unexpectedly slow (suggests file I/O at import)"

    def test_check_slot_availability_is_callable(self):
        """check_slot_availability exists and is callable."""
        from lib.dispatch_helper import check_slot_availability

        assert callable(check_slot_availability)

    def test_enqueue_agent_is_callable(self):
        """enqueue_agent exists and is callable."""
        from lib.dispatch_helper import enqueue_agent

        assert callable(enqueue_agent)

    def test_dequeue_ready_agents_is_callable(self):
        """dequeue_ready_agents exists and is callable."""
        from lib.dispatch_helper import dequeue_ready_agents

        assert callable(dequeue_ready_agents)

    def test_format_dispatch_status_is_callable(self):
        """format_dispatch_status exists and is callable."""
        from lib.dispatch_helper import format_dispatch_status

        assert callable(format_dispatch_status)
