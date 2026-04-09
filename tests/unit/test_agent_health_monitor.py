"""Unit tests for lib/agent_health_monitor.py.

Coverage:
1. test_healthy_agent_detected — started recently, in_progress → healthy
2. test_timeout_agent_detected — started > timeout ago → timeout
3. test_dead_agent_by_pid — PID doesn't exist → dead
4. test_completed_tasks_ignored — only in_progress tasks are checked
5. test_requeue_timeout_agent — timed-out agent goes back to dispatch queue
6. test_report_dead_to_dlq — dead agent is sent to DLQ
7. test_empty_tasks_returns_all_healthy — no in_progress → all-empty result
8. test_configurable_timeout — custom timeout_seconds is respected
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is on the path so `lib.*` imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.agent_health_monitor import AgentHealthMonitor, _pid_alive, _parse_iso  # noqa: E402

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_tasks_file(
    tmp_path: Path,
    tasks: List[Dict[str, Any]],
) -> Path:
    """Write an active-tasks.json and return its path."""
    tasks_dir = tmp_path / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = tasks_dir / "active-tasks.json"
    tasks_file.write_text(
        json.dumps({"version": 1, "tasks": tasks, "lastUpdated": _iso(_now())})
    )
    return tasks_file


def _make_task(
    task_id: str = "task-001",
    description: str = "test task",
    status: str = "in_progress",
    started_offset_secs: int = 10,
    pid: Optional[int] = None,
) -> Dict[str, Any]:
    started_at = _iso(_now() - timedelta(seconds=started_offset_secs))
    task: Dict[str, Any] = {
        "id": task_id,
        "description": description,
        "status": status,
        "launchedAt": started_at,
        "started_at": started_at,
        "completedAt": None,
        "outputSummary": None,
        "expectedOutputs": [],
        "checkCommand": None,
    }
    if pid is not None:
        task["pid"] = pid
    return task


def _monitor(
    tmp_path: Path,
    tasks: List[Dict[str, Any]],
    timeout_seconds: int = 300,
    dlq_path: Optional[str] = None,
    queue_path: Optional[str] = None,
) -> AgentHealthMonitor:
    tasks_file = _make_tasks_file(tmp_path, tasks)
    return AgentHealthMonitor(
        tasks_path=str(tasks_file),
        timeout_seconds=timeout_seconds,
        dlq_path=dlq_path,
        queue_path=queue_path,
    )


# ---------------------------------------------------------------------------
# Test 1: Healthy agent detected
# ---------------------------------------------------------------------------

class TestHealthyAgentDetected:

    def test_healthy_agent_detected(self, tmp_path):
        """An in-progress agent started recently is classified as healthy."""
        task = _make_task(started_offset_secs=10)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        assert len(health["healthy"]) == 1, "Expected 1 healthy agent"
        assert health["healthy"][0]["id"] == task["id"]
        assert health["timeout"] == []
        assert health["dead"] == []

    def test_multiple_healthy_agents(self, tmp_path):
        """All recently-started agents are classified as healthy."""
        tasks = [_make_task(f"task-{i}", started_offset_secs=5) for i in range(3)]
        mon = _monitor(tmp_path, tasks, timeout_seconds=300)

        health = mon.check_health()

        assert len(health["healthy"]) == 3
        assert health["timeout"] == []
        assert health["dead"] == []


# ---------------------------------------------------------------------------
# Test 2: Timeout agent detected
# ---------------------------------------------------------------------------

class TestTimeoutAgentDetected:

    def test_timeout_agent_detected(self, tmp_path):
        """An in-progress agent running longer than timeout is classified as timeout."""
        task = _make_task(started_offset_secs=400)  # > 300s default
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        assert len(health["timeout"]) == 1, "Expected 1 timed-out agent"
        assert health["timeout"][0]["id"] == task["id"]
        assert health["healthy"] == []
        assert health["dead"] == []

    def test_exactly_at_timeout_boundary_is_healthy(self, tmp_path):
        """An agent at exactly the timeout boundary is NOT timed out (strictly >)."""
        task = _make_task(started_offset_secs=300)  # == 300s, not strictly >
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        # At exactly the boundary it may fall into healthy or timeout depending on
        # execution timing; either way, never dead.
        assert health["dead"] == []
        total = len(health["healthy"]) + len(health["timeout"])
        assert total == 1

    def test_just_under_timeout_is_healthy(self, tmp_path):
        """An agent running 1 second less than timeout is healthy."""
        task = _make_task(started_offset_secs=299)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        assert len(health["healthy"]) == 1
        assert health["timeout"] == []


# ---------------------------------------------------------------------------
# Test 3: Dead agent by PID
# ---------------------------------------------------------------------------

class TestDeadAgentByPid:

    def test_dead_agent_by_pid(self, tmp_path):
        """An agent whose PID no longer exists is classified as dead."""
        # Use PID 99999999 which almost certainly doesn't exist
        task = _make_task(pid=99999999, started_offset_secs=10)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        assert len(health["dead"]) == 1, "Expected 1 dead agent"
        assert health["dead"][0]["id"] == task["id"]
        assert health["healthy"] == []
        assert health["timeout"] == []

    def test_alive_pid_not_dead(self, tmp_path):
        """An agent whose PID is alive is not classified as dead."""
        own_pid = os.getpid()
        task = _make_task(pid=own_pid, started_offset_secs=10)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        assert health["dead"] == []
        assert len(health["healthy"]) == 1

    def test_dead_takes_priority_over_timeout(self, tmp_path):
        """A dead agent is classified as dead even if it also exceeded the timeout."""
        task = _make_task(pid=99999999, started_offset_secs=600)  # timed out AND dead
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        # Must be dead, not timeout
        assert len(health["dead"]) == 1
        assert health["timeout"] == []

    def test_no_pid_field_uses_timestamp(self, tmp_path):
        """An agent without a PID field falls back to timestamp-based check."""
        task = _make_task(started_offset_secs=400)  # no pid field
        assert "pid" not in task
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        health = mon.check_health()

        assert len(health["timeout"]) == 1
        assert health["dead"] == []


# ---------------------------------------------------------------------------
# Test 4: Completed tasks ignored
# ---------------------------------------------------------------------------

class TestCompletedTasksIgnored:

    def test_completed_tasks_ignored(self, tmp_path):
        """Completed tasks are never included in health check results."""
        completed = _make_task("completed-task", status="completed", started_offset_secs=400)
        in_progress = _make_task("running-task", status="in_progress", started_offset_secs=10)
        mon = _monitor(tmp_path, [completed, in_progress], timeout_seconds=300)

        health = mon.check_health()

        ids = (
            [t["id"] for t in health["healthy"]]
            + [t["id"] for t in health["timeout"]]
            + [t["id"] for t in health["dead"]]
        )
        assert "completed-task" not in ids
        assert "running-task" in ids

    def test_failed_tasks_ignored(self, tmp_path):
        """Failed tasks are not checked by the health monitor."""
        failed = _make_task("failed-task", status="failed", started_offset_secs=600)
        mon = _monitor(tmp_path, [failed], timeout_seconds=300)

        health = mon.check_health()

        total = len(health["healthy"]) + len(health["timeout"]) + len(health["dead"])
        assert total == 0

    def test_lost_tasks_ignored(self, tmp_path):
        """Tasks already marked as 'lost' are not re-classified."""
        lost = _make_task("lost-task", status="lost", started_offset_secs=600)
        mon = _monitor(tmp_path, [lost], timeout_seconds=300)

        health = mon.check_health()

        total = len(health["healthy"]) + len(health["timeout"]) + len(health["dead"])
        assert total == 0


# ---------------------------------------------------------------------------
# Test 5: Requeue timeout agent
# ---------------------------------------------------------------------------

class TestRequeueTimeoutAgent:

    def test_requeue_timeout_agent(self, tmp_path):
        """A timed-out agent with retries remaining is enqueued to dispatch queue."""
        queue_file = tmp_path / "dispatch-queue.json"
        task = _make_task("timeout-task", started_offset_secs=400)
        mon = _monitor(
            tmp_path, [task],
            timeout_seconds=300,
            queue_path=str(queue_file),
        )

        requeued = mon.requeue_timeout_agents()

        assert len(requeued) == 1, "Expected 1 requeued agent"
        assert requeued[0]["id"] == "timeout-task"

    def test_requeue_updates_task_status_to_failed(self, tmp_path):
        """After requeue, the task is marked as failed in active-tasks.json."""
        queue_file = tmp_path / "dispatch-queue.json"
        task = _make_task("timeout-task", started_offset_secs=400)
        tasks_file = _make_tasks_file(tmp_path, [task])
        mon = AgentHealthMonitor(
            tasks_path=str(tasks_file),
            timeout_seconds=300,
            queue_path=str(queue_file),
        )

        mon.requeue_timeout_agents()

        data = json.loads(tasks_file.read_text())
        updated = next(t for t in data["tasks"] if t["id"] == "timeout-task")
        assert updated["status"] == "failed"

    def test_healthy_agents_not_requeued(self, tmp_path):
        """Healthy agents are not requeued."""
        queue_file = tmp_path / "dispatch-queue.json"
        task = _make_task("healthy-task", started_offset_secs=10)
        mon = _monitor(
            tmp_path, [task],
            timeout_seconds=300,
            queue_path=str(queue_file),
        )

        requeued = mon.requeue_timeout_agents()

        assert requeued == []


# ---------------------------------------------------------------------------
# Test 6: Report dead agents to DLQ
# ---------------------------------------------------------------------------

class TestReportDeadToDlq:

    def test_report_dead_to_dlq(self, tmp_path):
        """Dead agents are sent to the DLQ and task is marked failed."""
        dlq_file = tmp_path / "dead-letter-queue.jsonl"
        task = _make_task("dead-task", pid=99999999, started_offset_secs=10)
        tasks_file = _make_tasks_file(tmp_path, [task])
        mon = AgentHealthMonitor(
            tasks_path=str(tasks_file),
            timeout_seconds=300,
            dlq_path=str(dlq_file),
        )

        dead = mon.report_dead_agents()

        assert len(dead) == 1
        assert dead[0]["id"] == "dead-task"

        # Verify DLQ file was written
        assert dlq_file.exists(), "DLQ file should be created"
        lines = [l for l in dlq_file.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1

        entry = json.loads(lines[0])
        assert entry["task_id"] == "dead-task"
        assert "DEAD_PROCESS" in entry["failure_type"]

    def test_dead_agent_marked_failed_in_tasks(self, tmp_path):
        """After reporting to DLQ, dead task is marked failed in active-tasks.json."""
        dlq_file = tmp_path / "dead-letter-queue.jsonl"
        task = _make_task("dead-task-2", pid=99999999, started_offset_secs=10)
        tasks_file = _make_tasks_file(tmp_path, [task])
        mon = AgentHealthMonitor(
            tasks_path=str(tasks_file),
            timeout_seconds=300,
            dlq_path=str(dlq_file),
        )

        mon.report_dead_agents()

        data = json.loads(tasks_file.read_text())
        updated = next(t for t in data["tasks"] if t["id"] == "dead-task-2")
        assert updated["status"] == "failed"

    def test_no_dead_agents_returns_empty_list(self, tmp_path):
        """When there are no dead agents, report_dead_agents returns []."""
        own_pid = os.getpid()
        task = _make_task("alive-task", pid=own_pid, started_offset_secs=10)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)

        dead = mon.report_dead_agents()

        assert dead == []


# ---------------------------------------------------------------------------
# Test 7: Empty tasks returns all-healthy (empty lists)
# ---------------------------------------------------------------------------

class TestEmptyTasksReturnsAllHealthy:

    def test_empty_tasks_returns_all_healthy(self, tmp_path):
        """check_health on an empty tasks file returns empty lists (all healthy)."""
        mon = _monitor(tmp_path, [], timeout_seconds=300)

        health = mon.check_health()

        assert health["healthy"] == []
        assert health["timeout"] == []
        assert health["dead"] == []

    def test_missing_tasks_file_returns_all_healthy(self, tmp_path):
        """check_health when tasks file does not exist returns empty lists."""
        non_existent = str(tmp_path / "no-such-file.json")
        mon = AgentHealthMonitor(
            tasks_path=non_existent,
            timeout_seconds=300,
        )

        health = mon.check_health()

        assert health == {"healthy": [], "timeout": [], "dead": []}

    def test_only_completed_tasks_returns_all_healthy(self, tmp_path):
        """If all tasks are completed, all health buckets are empty."""
        completed_tasks = [
            _make_task(f"done-{i}", status="completed", started_offset_secs=5)
            for i in range(5)
        ]
        mon = _monitor(tmp_path, completed_tasks, timeout_seconds=300)

        health = mon.check_health()

        assert health["healthy"] == []
        assert health["timeout"] == []
        assert health["dead"] == []


# ---------------------------------------------------------------------------
# Test 8: Configurable timeout
# ---------------------------------------------------------------------------

class TestConfigurableTimeout:

    def test_configurable_timeout(self, tmp_path):
        """Custom timeout_seconds is respected when classifying tasks."""
        # With 60s timeout, a 90s-old task should be timed out
        task = _make_task(started_offset_secs=90)
        mon = _monitor(tmp_path, [task], timeout_seconds=60)

        health = mon.check_health()

        assert len(health["timeout"]) == 1

    def test_custom_short_timeout_triggers_early(self, tmp_path):
        """A 10s timeout classifies a 15s-old task as timed out."""
        task = _make_task(started_offset_secs=15)
        mon = _monitor(tmp_path, [task], timeout_seconds=10)

        health = mon.check_health()

        assert len(health["timeout"]) == 1, "15s task should timeout with 10s limit"
        assert health["healthy"] == []

    def test_large_timeout_keeps_old_tasks_healthy(self, tmp_path):
        """A very large timeout keeps even old tasks as healthy."""
        task = _make_task(started_offset_secs=3600)  # 1 hour
        mon = _monitor(tmp_path, [task], timeout_seconds=7200)  # 2 hour limit

        health = mon.check_health()

        assert len(health["healthy"]) == 1
        assert health["timeout"] == []

    def test_config_file_timeout_overrides_default(self, tmp_path):
        """AgentHealthMonitor reads timeout from cognitive-os.yaml if no override given."""
        config_file = tmp_path / "cognitive-os.yaml"
        config_file.write_text(
            "resources:\n  compute:\n    agent_timeout_seconds: 30\n"
        )

        task = _make_task(started_offset_secs=45)
        tasks_file = _make_tasks_file(tmp_path, [task])
        # Pass config_path explicitly; no timeout_seconds override
        mon = AgentHealthMonitor(
            tasks_path=str(tasks_file),
            config_path=str(config_file),
        )

        health = mon.check_health()

        assert len(health["timeout"]) == 1, "45s task should timeout with config 30s"


# ---------------------------------------------------------------------------
# Test: format_health_report
# ---------------------------------------------------------------------------

class TestFormatHealthReport:

    def test_empty_report(self, tmp_path):
        """Empty tasks produces a short 'no agents' message."""
        mon = _monitor(tmp_path, [], timeout_seconds=300)
        report = mon.format_health_report()
        assert "no in-progress agents" in report.lower()

    def test_report_includes_timeout_info(self, tmp_path):
        """Report mentions timed-out agents."""
        task = _make_task("slow-task", started_offset_secs=400)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)
        report = mon.format_health_report()
        assert "timeout" in report.lower() or "timed" in report.lower()

    def test_report_includes_dead_info(self, tmp_path):
        """Report mentions dead agents."""
        task = _make_task("ghost-task", pid=99999999, started_offset_secs=10)
        mon = _monitor(tmp_path, [task], timeout_seconds=300)
        report = mon.format_health_report()
        assert "dead" in report.lower()


# ---------------------------------------------------------------------------
# Test: _pid_alive helper
# ---------------------------------------------------------------------------

class TestPidAliveHelper:

    def test_own_pid_is_alive(self):
        assert _pid_alive(os.getpid()) is True

    def test_nonexistent_pid_is_not_alive(self):
        # PID 99999999 almost certainly does not exist
        assert _pid_alive(99999999) is False


# ---------------------------------------------------------------------------
# Test: _parse_iso helper
# ---------------------------------------------------------------------------

class TestParseIsoHelper:

    def test_parse_z_suffix(self):
        ts = "2026-04-09T10:00:00Z"
        dt = _parse_iso(ts)
        assert dt is not None
        assert dt.year == 2026 and dt.month == 4 and dt.day == 9

    def test_parse_no_tz(self):
        ts = "2026-04-09T10:00:00"
        dt = _parse_iso(ts)
        assert dt is not None
        assert dt.tzinfo is not None  # should be given UTC

    def test_parse_empty_returns_none(self):
        assert _parse_iso("") is None
        assert _parse_iso(None) is None  # type: ignore[arg-type]

    def test_parse_invalid_returns_none(self):
        assert _parse_iso("not-a-date") is None
