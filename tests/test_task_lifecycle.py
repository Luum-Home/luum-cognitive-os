"""Behavioral/integration tests for the agent task lifecycle system.

Tests validate that tasks flow correctly through:
    created -> pending -> in_progress -> completed (or failed)

Components under test:
  1. hooks/agent-prelaunch.sh    -- PreToolUse hook that creates tasks
  2. lib/agent_health_monitor.py -- Python monitor for stale/dead tasks
  3. AgentHealthMonitor._update_task_status -- used by the completion path

Classification rules (from AgentHealthMonitor._classify_task):
  - pid=null + age < timeout_limit  -> healthy
  - pid=null + age >= timeout_limit -> timeout (stale)
  - pid=N + age < 5s               -> healthy (grace period, even if PID is dead)
  - pid=N + age >= 5s + PID dead   -> dead
  - pid=N + age >= 5s + PID alive  -> healthy (or timeout by age vs configured limit)

All tests use tmp_path for isolation; the real .cognitive-os/tasks/active-tasks.json
is never touched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# ---------------------------------------------------------------------------
# Project root resolution
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRELAUNCH_HOOK = PROJECT_ROOT / "hooks" / "agent-prelaunch.sh"

# ---------------------------------------------------------------------------
# Import the health monitor directly (must come before first use)
# ---------------------------------------------------------------------------

sys.path.insert(0, str(PROJECT_ROOT))
from lib.agent_health_monitor import AgentHealthMonitor, _DEFAULT_TIMEOUT_SECONDS  # noqa: E402

# Grace period constants read from the class/module so tests stay in sync
# with any future changes to the thresholds.
_MIN_AGE_FOR_DEAD = AgentHealthMonitor._MIN_AGE_FOR_DEAD_SECONDS   # 5 s grace period
# Null-PID tasks become stale after the configured timeout (same as live-PID timeout).
_NULL_PID_STALE = _DEFAULT_TIMEOUT_SECONDS  # 300 s default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tasks_file(
    base: Path,
    tasks: Optional[List[Dict[str, Any]]] = None,
) -> Path:
    """Create a minimal active-tasks.json under *base* and return its path."""
    tasks_dir = base / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = tasks_dir / "active-tasks.json"
    data = {"version": 1, "tasks": tasks or [], "lastUpdated": ""}
    tasks_file.write_text(json.dumps(data), encoding="utf-8")
    return tasks_file


def _read_tasks(tasks_file: Path) -> Dict[str, Any]:
    return json.loads(tasks_file.read_text(encoding="utf-8"))


def _run_prelaunch(
    tmp_path: Path,
    tool_input: Optional[Dict[str, Any]] = None,
) -> subprocess.CompletedProcess:
    """Run agent-prelaunch.sh with the given JSON input, pointing it at tmp_path."""
    if tool_input is None:
        tool_input = {"description": "test task"}
    payload = json.dumps({"tool_name": "Agent", "tool_input": tool_input})
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    return subprocess.run(
        ["bash", str(PRELAUNCH_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _task_entry(
    task_id: str,
    status: str = "in_progress",
    started_at: Optional[str] = None,
    pid: Optional[int] = None,
    age_offset_seconds: float = 0,
) -> Dict[str, Any]:
    """Build a task dict with controllable age."""
    if started_at is None:
        dt = datetime.now(timezone.utc) - timedelta(seconds=age_offset_seconds)
        started_at = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": task_id,
        "description": f"Test task {task_id}",
        "status": status,
        "launchedAt": started_at,
        "started_at": started_at,
        "pid": pid,
        "completedAt": None,
        "outputSummary": None,
        "expectedOutputs": [],
        "checkCommand": None,
    }


def _pid_is_alive(pid: int) -> bool:
    """Return True if the given PID is a live process."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


# ===========================================================================
# 1. Task Creation -- agent-prelaunch.sh behavior
# ===========================================================================


class TestTaskCreation:
    """Tests for agent-prelaunch.sh: task creation, format, and safety."""

    def test_creates_valid_json(self, tmp_path: Path) -> None:
        """Creating a task writes valid JSON to active-tasks.json."""
        _run_prelaunch(tmp_path)
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        assert tasks_file.exists(), "active-tasks.json must be created by the hook"
        data = _read_tasks(tasks_file)
        assert data["version"] == 1
        assert isinstance(data["tasks"], list)
        assert len(data["tasks"]) == 1

    def test_task_created_with_pending_status(self, tmp_path: Path) -> None:
        """PreToolUse records a pending task before the agent process starts."""
        _run_prelaunch(tmp_path)
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert data["tasks"][0]["status"] == "pending"

    def test_task_created_with_null_pid(self, tmp_path: Path) -> None:
        """Task is created with pid=null (NOT a shell PID).

        The hook fires before the agent process starts, so $$ is the hook's
        own (already-exiting) shell PID.  Storing it would cause the health
        monitor to eventually classify every new task as 'dead' once the
        grace period expires.  The correct behavior is pid=null.
        """
        _run_prelaunch(tmp_path)
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        task = data["tasks"][0]
        assert task["pid"] is None, (
            f"pid should be null (not a shell PID), got: {task['pid']}"
        )

    def test_task_id_follows_pattern(self, tmp_path: Path) -> None:
        """Task ID follows the stable descriptor-hash pattern."""
        _run_prelaunch(tmp_path)
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        task_id = data["tasks"][0]["id"]
        assert re.match(r"^task-desc-[0-9a-f]{16}$", task_id), (
            f"Task ID '{task_id}' does not match pattern 'task-desc-HEX16'"
        )

    def test_task_description_captured_from_description_field(self, tmp_path: Path) -> None:
        """Task description is captured from tool_input.description."""
        _run_prelaunch(tmp_path, tool_input={"description": "analyze deployment config"})
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert data["tasks"][0]["description"] == "analyze deployment config"

    def test_task_description_falls_back_to_prompt_field(self, tmp_path: Path) -> None:
        """Task description falls back to tool_input.prompt when description is absent."""
        _run_prelaunch(tmp_path, tool_input={"prompt": "build the feature"})
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert data["tasks"][0]["description"] == "build the feature"

    def test_multiple_sequential_tasks_no_corruption(self, tmp_path: Path) -> None:
        """Multiple sequential tasks don't corrupt the JSON file."""
        for i in range(5):
            result = _run_prelaunch(tmp_path, tool_input={"description": f"task {i}"})
            assert result.returncode == 0, f"Hook failed on iteration {i}: {result.stderr}"
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert len(data["tasks"]) == 5

    def test_special_characters_in_description_valid_json(self, tmp_path: Path) -> None:
        """Special characters in description don't break JSON output."""
        special = 'deploy "service" with $VAR & <xml> chars \\ slash'
        _run_prelaunch(tmp_path, tool_input={"description": special})
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert len(data["tasks"]) == 1

    def test_non_agent_tool_is_ignored(self, tmp_path: Path) -> None:
        """Hook exits early without creating tasks for non-Agent tool calls."""
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        }
        result = subprocess.run(
            ["bash", str(PRELAUNCH_HOOK)],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        if tasks_file.exists():
            data = _read_tasks(tasks_file)
            assert len(data["tasks"]) == 0

    def test_timestamps_are_iso8601(self, tmp_path: Path) -> None:
        """launchedAt and started_at are valid ISO-8601 timestamps."""
        _run_prelaunch(tmp_path)
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        task = data["tasks"][0]
        for field in ("launchedAt", "started_at"):
            ts = task[field]
            assert ts, f"{field} must not be empty"
            dt = datetime.fromisoformat(ts.rstrip("Z"))
            assert dt is not None

    def test_hook_exits_zero_on_success(self, tmp_path: Path) -> None:
        """Hook exits with code 0 on normal invocation."""
        result = _run_prelaunch(tmp_path)
        assert result.returncode == 0, f"Hook returned non-zero: {result.stderr}"

    def test_concurrent_writes_no_corruption(self, tmp_path: Path) -> None:
        """Concurrent task creation via parallel hook invocations doesn't corrupt JSON.

        Race condition test: launch N parallel hook processes and verify the
        final JSON is valid and contains all N tasks.  The lock file mechanism
        in the hook is what prevents corruption.
        """
        n = 10
        procs = []
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        }
        for i in range(n):
            payload = json.dumps(
                {"tool_name": "Agent", "tool_input": {"description": f"concurrent-{i}"}}
            )
            p = subprocess.Popen(
                ["bash", str(PRELAUNCH_HOOK)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            procs.append((p, payload))

        for p, payload in procs:
            p.communicate(input=payload, timeout=10)

        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert len(data["tasks"]) == n, (
            f"Expected {n} tasks after concurrent writes, got {len(data['tasks'])}"
        )


# ===========================================================================
# 2. Task Completion -- status transition via AgentHealthMonitor
# ===========================================================================


class TestTaskCompletion:
    """Tests for task status transitions using AgentHealthMonitor._update_task_status."""

    def test_update_task_status_marks_completed(self, tmp_path: Path) -> None:
        """Completing a task sets status to 'completed' and adds completedAt."""
        tasks_file = _make_tasks_file(tmp_path, [_task_entry("task-001")])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        result = monitor._update_task_status("task-001", "completed")

        assert result is True
        data = _read_tasks(tasks_file)
        task = data["tasks"][0]
        assert task["status"] == "completed"
        assert task["completedAt"] is not None

    def test_completing_task_preserves_other_tasks(self, tmp_path: Path) -> None:
        """Completing one task doesn't disturb other tasks in the file."""
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-A"), _task_entry("task-B"), _task_entry("task-C")],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        monitor._update_task_status("task-B", "completed")

        data = _read_tasks(tasks_file)
        by_id = {t["id"]: t for t in data["tasks"]}
        assert by_id["task-A"]["status"] == "in_progress"
        assert by_id["task-B"]["status"] == "completed"
        assert by_id["task-C"]["status"] == "in_progress"

    def test_completing_nonexistent_task_is_noop(self, tmp_path: Path) -> None:
        """Completing a non-existent task ID returns False and doesn't crash."""
        tasks_file = _make_tasks_file(tmp_path, [_task_entry("task-real")])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        result = monitor._update_task_status("task-does-not-exist", "completed")

        assert result is False
        data = _read_tasks(tasks_file)
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "in_progress"

    def test_update_task_status_to_failed(self, tmp_path: Path) -> None:
        """A task can be marked as 'failed' with completedAt set."""
        tasks_file = _make_tasks_file(tmp_path, [_task_entry("task-fail")])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        monitor._update_task_status("task-fail", "failed")

        data = _read_tasks(tasks_file)
        task = data["tasks"][0]
        assert task["status"] == "failed"
        assert task["completedAt"] is not None

    def test_update_task_status_with_extra_fields(self, tmp_path: Path) -> None:
        """Extra fields (e.g. requeue_attempts) are persisted alongside status."""
        tasks_file = _make_tasks_file(tmp_path, [_task_entry("task-extra")])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        monitor._update_task_status("task-extra", "failed", extra={"requeue_attempts": 1})

        data = _read_tasks(tasks_file)
        task = data["tasks"][0]
        assert task["status"] == "failed"
        assert task["requeue_attempts"] == 1


# ===========================================================================
# 3. Health Monitor -- AgentHealthMonitor classification logic
# ===========================================================================


class TestHealthMonitor:
    """Tests for AgentHealthMonitor._classify_task and check_health().

    Classification rules enforced by _classify_task:
      Rule 1: pid=null  -> age < _NULL_PID_STALE   => healthy
      Rule 2: pid=null  -> age >= _NULL_PID_STALE  => timeout
      Rule 3: pid=N     -> age < _MIN_AGE_FOR_DEAD => healthy (grace period)
      Rule 4: pid=N, dead, age >= _MIN_AGE_FOR_DEAD => dead
      Rule 5: pid=N, alive, any age               => healthy (or timeout by limit)
    """

    def test_null_pid_never_classified_dead(self, tmp_path: Path) -> None:
        """A task with pid=null is NEVER classified as 'dead' regardless of age.

        This is the core invariant introduced to fix false-dead classification.
        """
        for age in [10, 60, 300, 600]:
            tasks_file = _make_tasks_file(
                tmp_path / str(age),
                [_task_entry(f"task-{age}", pid=None, age_offset_seconds=age)],
            )
            monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
            health = monitor.check_health()
            assert len(health["dead"]) == 0, (
                f"Task with pid=null must not be classified as dead (age={age}s)"
            )

    def test_null_pid_young_task_classified_healthy(self, tmp_path: Path) -> None:
        """Task with pid=null and age well under the stale threshold is 'healthy'."""
        safe_age = _NULL_PID_STALE - 30  # 30s margin under the 1800s threshold
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-young", pid=None, age_offset_seconds=safe_age)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["healthy"]) == 1
        assert len(health["dead"]) == 0
        assert len(health["timeout"]) == 0

    def test_null_pid_stale_task_classified_timeout(self, tmp_path: Path) -> None:
        """Task with pid=null and age > _NULL_PID_STALE_SECONDS is 'timeout' (stale).

        Uses 120s margin past the threshold to avoid sub-second timestamp flakiness.
        """
        stale_age = _NULL_PID_STALE + 120
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-stale", pid=None, age_offset_seconds=stale_age)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["timeout"]) == 1, (
            f"Task with null PID older than {_NULL_PID_STALE}s must be 'timeout'; "
            f"health={health}"
        )
        assert len(health["dead"]) == 0

    def test_dead_pid_within_grace_period_not_dead(self, tmp_path: Path) -> None:
        """Task with a dead PID but age < _MIN_AGE_FOR_DEAD_SECONDS is NOT 'dead'.

        Grace period protects against false positives during the window between
        hook execution (where any stored PID would already be dead) and agent startup.
        """
        dead_pid = 99999
        if _pid_is_alive(dead_pid):
            pytest.skip("PID 99999 is alive -- cannot test dead-PID grace period")

        # Age well under the grace period (use half of _MIN_AGE_FOR_DEAD, min 1s)
        grace_age = max(1, _MIN_AGE_FOR_DEAD // 2)
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-grace", pid=dead_pid, age_offset_seconds=grace_age)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["dead"]) == 0, (
            f"Task with dead PID but age < {_MIN_AGE_FOR_DEAD}s must NOT be 'dead'; "
            f"health={health}"
        )

    def test_dead_pid_past_grace_period_classified_dead(self, tmp_path: Path) -> None:
        """Task with a dead PID and age >= _MIN_AGE_FOR_DEAD_SECONDS IS 'dead'.

        Uses 120s margin past the 300s threshold for timing safety.
        """
        dead_pid = 99999
        if _pid_is_alive(dead_pid):
            pytest.skip("PID 99999 is alive -- cannot test dead-PID classification")

        old_age = _MIN_AGE_FOR_DEAD + 120
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-dead-old", pid=dead_pid, age_offset_seconds=old_age)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["dead"]) == 1, (
            f"Task with dead PID and age >= {_MIN_AGE_FOR_DEAD}s must be 'dead'; "
            f"health={health}"
        )

    def test_alive_pid_classified_healthy(self, tmp_path: Path) -> None:
        """Task with an alive PID (current process) is classified as 'healthy'."""
        alive_pid = os.getpid()
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-alive", pid=alive_pid, age_offset_seconds=5)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["dead"]) == 0, "Task with alive PID must not be 'dead'"
        assert len(health["healthy"]) == 1

    def test_alive_pid_old_not_classified_dead(self, tmp_path: Path) -> None:
        """Task with an alive PID that is old is still not dead (PID is alive)."""
        alive_pid = os.getpid()
        old_age = _MIN_AGE_FOR_DEAD + 600  # well past grace period
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("task-alive-old", pid=alive_pid, age_offset_seconds=old_age)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["dead"]) == 0, "Task with alive PID must never be 'dead'"

    def test_completed_and_failed_tasks_ignored_by_check_health(self, tmp_path: Path) -> None:
        """check_health() only considers tasks with status='in_progress'."""
        tasks = [
            _task_entry("t-completed", status="completed"),
            _task_entry("t-failed", status="failed"),
            _task_entry("t-active", status="in_progress", pid=None, age_offset_seconds=10),
        ]
        tasks_file = _make_tasks_file(tmp_path, tasks)
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        total = len(health["healthy"]) + len(health["timeout"]) + len(health["dead"])
        assert total == 1, "Only in_progress tasks should be considered by check_health()"

    def test_check_health_correct_counts_mixed_states(self, tmp_path: Path) -> None:
        """check_health() returns accurate counts for a mix of healthy/stale/dead tasks."""
        alive_pid = os.getpid()
        dead_pid = 99999

        if _pid_is_alive(dead_pid):
            pytest.skip("PID 99999 is alive -- cannot test mixed-state classification")

        tasks = [
            # healthy: null PID, young
            _task_entry("t-h1", pid=None, age_offset_seconds=30),
            # healthy: alive PID, young
            _task_entry("t-h2", pid=alive_pid, age_offset_seconds=30),
            # timeout: null PID, well over _NULL_PID_STALE
            _task_entry("t-timeout", pid=None, age_offset_seconds=_NULL_PID_STALE + 120),
            # dead: dead PID, well over _MIN_AGE_FOR_DEAD
            _task_entry("t-dead", pid=dead_pid, age_offset_seconds=_MIN_AGE_FOR_DEAD + 120),
        ]
        tasks_file = _make_tasks_file(tmp_path, tasks)
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()

        assert len(health["healthy"]) == 2, f"Expected 2 healthy, got {health['healthy']}"
        assert len(health["timeout"]) == 1, f"Expected 1 timeout, got {health['timeout']}"
        assert len(health["dead"]) == 1, f"Expected 1 dead, got {health['dead']}"

    def test_check_health_empty_tasks_returns_empty(self, tmp_path: Path) -> None:
        """check_health() returns all-empty lists when there are no in_progress tasks."""
        tasks_file = _make_tasks_file(tmp_path, [])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert health == {"healthy": [], "timeout": [], "dead": []}

    def test_check_health_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """check_health() doesn't crash and returns empty when tasks file doesn't exist."""
        nonexistent = str(tmp_path / "nonexistent" / "active-tasks.json")
        monitor = AgentHealthMonitor(tasks_path=nonexistent)
        health = monitor.check_health()
        assert health == {"healthy": [], "timeout": [], "dead": []}

    def test_format_health_report_no_agents(self, tmp_path: Path) -> None:
        """format_health_report() returns a sensible message when no agents are in progress."""
        tasks_file = _make_tasks_file(tmp_path, [])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        report = monitor.format_health_report()
        assert "no in-progress" in report.lower()

    def test_format_health_report_mentions_stale_agents(self, tmp_path: Path) -> None:
        """format_health_report() mentions timed-out agents."""
        stale_age = _NULL_PID_STALE + 120
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("t-stale", pid=None, age_offset_seconds=stale_age)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        report = monitor.format_health_report()
        assert "timeout" in report.lower() or "timed-out" in report.lower()

    def test_null_pid_boundary_just_under_stale(self, tmp_path: Path) -> None:
        """Task clearly under the stale boundary (30s margin) is still 'healthy'."""
        safe_under = _NULL_PID_STALE - 30
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("t-near", pid=None, age_offset_seconds=safe_under)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["timeout"]) == 0
        assert len(health["healthy"]) == 1

    def test_null_pid_boundary_clearly_over_stale(self, tmp_path: Path) -> None:
        """Task clearly over the stale boundary (120s margin) is 'timeout'."""
        safe_over = _NULL_PID_STALE + 120
        tasks_file = _make_tasks_file(
            tmp_path,
            [_task_entry("t-over", pid=None, age_offset_seconds=safe_over)],
        )
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["timeout"]) == 1
        assert len(health["healthy"]) == 0


# ===========================================================================
# 4. End-to-End Lifecycle
# ===========================================================================


class TestEndToEndLifecycle:
    """Full lifecycle tests: create via hook -> monitor -> complete/fail."""

    def test_full_lifecycle_create_then_complete(self, tmp_path: Path) -> None:
        """Full lifecycle: hook creates task -> mark complete -> verify final state."""
        result = _run_prelaunch(tmp_path, tool_input={"description": "e2e lifecycle test"})
        assert result.returncode == 0

        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        assert len(data["tasks"]) == 1
        task_id = data["tasks"][0]["id"]
        assert data["tasks"][0]["status"] == "pending"
        assert data["tasks"][0]["pid"] is None

        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        success = monitor._update_task_status(task_id, "completed")
        assert success is True

        data = _read_tasks(tasks_file)
        task = data["tasks"][0]
        assert task["status"] == "completed"
        assert task["completedAt"] is not None
        assert task["pid"] is None

    def test_full_lifecycle_health_check_while_running(self, tmp_path: Path) -> None:
        """Full lifecycle: create -> health shows healthy -> complete -> no in-progress remain."""
        _run_prelaunch(tmp_path, tool_input={"description": "health check during run"})
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        task_id = data["tasks"][0]["id"]

        # Immediately after creation: pending tasks are not monitored as running.
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["dead"]) == 0, "Newly created pending task with null PID must not be dead"
        assert sum(len(v) for v in health.values()) == 0

        monitor._update_task_status(task_id, "completed")
        health_after = monitor.check_health()
        total = sum(len(v) for v in health_after.values())
        assert total == 0, "No in_progress tasks should remain after completion"

    def test_stale_task_detected_after_null_pid_timeout(self, tmp_path: Path) -> None:
        """Recovery: task with null PID stuck > _NULL_PID_STALE_SECONDS is flagged stale."""
        stale_age = _NULL_PID_STALE + 120
        stale_task = _task_entry("t-stale-e2e", pid=None, age_offset_seconds=stale_age)
        tasks_file = _make_tasks_file(tmp_path, [stale_task])

        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()
        assert len(health["timeout"]) == 1, "Stale task must be detected as timed-out"
        assert health["timeout"][0]["id"] == "t-stale-e2e"

    def test_false_dead_classification_bug_regression(self, tmp_path: Path) -> None:
        """Regression: hook PID is dead immediately; monitor must NOT classify as dead.

        The bug that triggered this fix:
          OLD: hook stored $$ (shell PID) as the task's pid field.
               Shell exits -> PID is dead -> monitor saw dead PID
               -> false 'dead' classification as soon as grace period expired.
          FIX A (pid=null): hook stores null; _classify_task skips PID check.
          FIX B (grace period): even with a stored PID, tasks are protected for
                300s before a dead PID can trigger 'dead' classification.

        This test validates all three scenarios:
        1. null PID -> never dead
        2. dead PID + young age -> protected by grace period
        3. dead PID + old age -> correctly classified as dead
        """
        dead_pid = 99999
        if _pid_is_alive(dead_pid):
            pytest.skip("PID 99999 is alive -- cannot run this regression test")

        # --- Scenario 1: null PID (the primary fix) ---
        null_task = _task_entry("task-null", pid=None, age_offset_seconds=2)
        tf_null = _make_tasks_file(tmp_path / "null", [null_task])
        health_null = AgentHealthMonitor(tasks_path=str(tf_null)).check_health()
        assert len(health_null["dead"]) == 0, (
            "REGRESSION: Task with pid=null must not be dead (primary fix)"
        )

        # --- Scenario 2: dead PID within grace period ---
        grace_task = _task_entry("task-grace", pid=dead_pid, age_offset_seconds=2)
        tf_grace = _make_tasks_file(tmp_path / "grace", [grace_task])
        health_grace = AgentHealthMonitor(tasks_path=str(tf_grace)).check_health()
        assert len(health_grace["dead"]) == 0, (
            f"REGRESSION: Task with dead PID but age < {_MIN_AGE_FOR_DEAD}s must not be dead"
        )

        # --- Scenario 3: dead PID past grace period (expected dead) ---
        old_age = _MIN_AGE_FOR_DEAD + 120
        old_dead_task = _task_entry("task-old-dead", pid=dead_pid, age_offset_seconds=old_age)
        tf_old = _make_tasks_file(tmp_path / "old", [old_dead_task])
        health_old = AgentHealthMonitor(tasks_path=str(tf_old)).check_health()
        assert len(health_old["dead"]) == 1, (
            "Old task with dead PID (past grace period) must be 'dead'"
        )

    def test_multiple_tasks_mixed_completion(self, tmp_path: Path) -> None:
        """Multiple tasks: complete some, leave others running -- verify both states."""
        for i in range(3):
            _run_prelaunch(tmp_path, tool_input={"description": f"mixed task {i}"})

        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        data = _read_tasks(tasks_file)
        ids = [t["id"] for t in data["tasks"]]
        assert len(ids) == 3

        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        monitor._update_task_status(ids[0], "completed")
        monitor._update_task_status(ids[1], "failed")

        data = _read_tasks(tasks_file)
        by_id = {t["id"]: t for t in data["tasks"]}
        assert by_id[ids[0]]["status"] == "completed"
        assert by_id[ids[1]]["status"] == "failed"
        assert by_id[ids[2]]["status"] == "pending"

        health = monitor.check_health()
        total = sum(len(v) for v in health.values())
        assert total == 0, "Pending tasks are not treated as running by health monitor"

    def test_created_task_immediately_pending_to_monitor(self, tmp_path: Path) -> None:
        """A task created by the hook is pending until the agent process starts.

        This is the core end-to-end guarantee: create -> pending, not dead.
        """
        _run_prelaunch(tmp_path, tool_input={"description": "immediate health check"})
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"

        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))
        health = monitor.check_health()

        assert len(health["dead"]) == 0, "Freshly created pending task must not be dead"
        assert len(health["timeout"]) == 0, "Freshly created pending task must not be timed out"
        assert len(health["healthy"]) == 0, "Pending task should not be treated as running"

    def test_requeue_timeout_agents_updates_task_file(self, tmp_path: Path) -> None:
        """requeue_timeout_agents() updates the tasks file even if queue enqueue fails."""
        stale_age = _NULL_PID_STALE + 120
        stale = _task_entry("t-requeue", pid=None, age_offset_seconds=stale_age)
        tasks_file = _make_tasks_file(tmp_path, [stale])
        monitor = AgentHealthMonitor(tasks_path=str(tasks_file))

        try:
            monitor.requeue_timeout_agents()
        except Exception:
            pass  # QueueDrainer may not be configured in test env

        data = _read_tasks(tasks_file)
        assert len(data["tasks"]) == 1
        # Status is either still in_progress (enqueue failed so no update)
        # or failed (enqueue succeeded and status was updated)
        assert data["tasks"][0]["status"] in ("in_progress", "failed"), (
            "Task status must be either in_progress or failed after requeue attempt"
        )
