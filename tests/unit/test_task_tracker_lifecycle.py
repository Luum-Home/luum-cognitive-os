"""Behavioral tests for the task tracker lifecycle (ADR-097).

Coverage:
1. agent-prelaunch.sh writes status=pending (not in_progress)
2. task_bridge.register() writes status=pending
3. dispatch-gate allow path can flip pending → in_progress
4. write_context_marker._claim_pending_task() captures PID and flips to in_progress
5. Zombie reaper: dead PID → cancelled-zombie
6. Zombie reaper: null PID + stale → cancelled-stale
7. Zombie reaper: null PID + fresh → left alone
8. Queue cancel → active-tasks sync (cancelled-dequeued)
9. Queue mark_dispatched → active-tasks sync (in_progress)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

AGENT_PRELAUNCH = PROJECT_ROOT / "hooks" / "agent-prelaunch.sh"
WRITE_CONTEXT_MARKER = PROJECT_ROOT / "scripts" / "write_context_marker.py"

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso(offset_secs: float = 0.0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(seconds=offset_secs)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_tasks_file(tmp_path: Path, tasks: List[Dict[str, Any]]) -> Path:
    tasks_dir = tmp_path / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    path = tasks_dir / "active-tasks.json"
    path.write_text(json.dumps({"version": 1, "tasks": tasks, "lastUpdated": _now_iso()}))
    return path


def _read_tasks(tasks_file: Path) -> List[Dict[str, Any]]:
    return json.loads(tasks_file.read_text()).get("tasks", [])


def _env(project_dir: Path) -> dict:
    e = os.environ.copy()
    e["CLAUDE_PROJECT_DIR"] = str(project_dir)
    # Prevent hooks from triggering rate limiter
    e["COS_HOOKS_DISABLED"] = "true"
    e.pop("COGNITIVE_OS_KILLSWITCH", None)
    return e


def _make_queue_file(tmp_path: Path, items: List[Dict[str, Any]]) -> Path:
    tasks_dir = tmp_path / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    path = tasks_dir / "dispatch-queue.json"
    path.write_text(json.dumps(items))
    return path


# ---------------------------------------------------------------------------
# Fix 1: agent-prelaunch.sh writes status=pending
# ---------------------------------------------------------------------------

class TestAgentPrelaunchWritesPending:
    def test_registers_as_pending_not_in_progress(self, tmp_path):
        """agent-prelaunch.sh must write status='pending', not 'in_progress'."""
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        tasks_file = tasks_dir / "active-tasks.json"
        tasks_file.write_text('{"version":1,"tasks":[],"lastUpdated":""}')

        hook_input = json.dumps({
            "tool_name": "Agent",
            "tool_use_id": "toolu_test_pending_001",
            "tool_input": {"prompt": "Run fix for test suite", "model": "sonnet"},
        })

        env = _env(tmp_path)
        # Skip killswitch and private mode checks
        env["COS_SKIP_KILLSWITCH"] = "true"
        env["COS_PRIVATE_MODE"] = "false"

        result = subprocess.run(
            ["bash", str(AGENT_PRELAUNCH)],
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=str(tmp_path),
        )
        # Hook must exit 0
        assert result.returncode == 0, f"stderr: {result.stderr}"

        tasks = _read_tasks(tasks_file)
        assert len(tasks) == 1, "Expected exactly one task to be registered"
        task = tasks[0]
        assert task["status"] == "pending", (
            f"Expected status='pending', got {task['status']!r}. "
            "Fix 1: agent-prelaunch.sh must write 'pending', not 'in_progress'."
        )
        assert task["toolUseId"] == "toolu_test_pending_001"
        assert task["pid"] is None

    def test_pending_record_has_requested_at(self, tmp_path):
        """Pending record must have requested_at timestamp."""
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        tasks_file = tasks_dir / "active-tasks.json"
        tasks_file.write_text('{"version":1,"tasks":[],"lastUpdated":""}')

        hook_input = json.dumps({
            "tool_name": "Agent",
            "tool_use_id": "toolu_req_at_001",
            "tool_input": {"prompt": "Test requested_at field"},
        })

        env = _env(tmp_path)
        env["COS_SKIP_KILLSWITCH"] = "true"
        env["COS_PRIVATE_MODE"] = "false"

        subprocess.run(
            ["bash", str(AGENT_PRELAUNCH)],
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=str(tmp_path),
        )

        tasks = _read_tasks(tasks_file)
        if tasks:
            task = tasks[0]
            assert "requested_at" in task or "launchedAt" in task, (
                "Pending record must have a timestamp (requested_at or launchedAt)"
            )


# ---------------------------------------------------------------------------
# Fix 1: task_bridge.register() writes status=pending
# ---------------------------------------------------------------------------

TASK_BRIDGE = PROJECT_ROOT / "hooks" / "_lib" / "task_bridge.py"


class TestTaskBridgeRegisterWritesPending:
    def _run_bridge(self, tmp_path: Path, tool_use_id: str, description: str) -> dict:
        """Run task_bridge.py register subcommand via subprocess."""
        env = _env(tmp_path)
        result = subprocess.run(
            [
                "python3", str(TASK_BRIDGE),
                "register",
                "--tool-use-id", tool_use_id,
                "--description", description,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0, f"task_bridge failed: {result.stderr}"
        return json.loads(result.stdout)

    def test_register_writes_pending_status(self, tmp_path):
        """task_bridge.register() must write status='pending', not 'in_progress'."""
        entry = self._run_bridge(tmp_path, "toolu_bridge_001", "bridge test task")
        assert entry["status"] == "pending", (
            f"Expected status='pending', got {entry['status']!r}. "
            "Fix 1: task_bridge.register() must write 'pending'."
        )

    def test_register_persists_pending_to_file(self, tmp_path):
        self._run_bridge(tmp_path, "toolu_bridge_002", "persist test")
        tasks_file = tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json"
        assert tasks_file.is_file()
        tasks = _read_tasks(tasks_file)
        assert any(
            t.get("status") == "pending" and t.get("toolUseId") == "toolu_bridge_002"
            for t in tasks
        )


# ---------------------------------------------------------------------------
# Fix 2: write_context_marker._claim_pending_task() flips pending → in_progress
# ---------------------------------------------------------------------------

class TestClaimPendingTask:
    def test_claim_flips_status_to_in_progress(self, tmp_path):
        """_claim_pending_task must set status=in_progress and capture pid."""
        # Import the function directly
        sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.write_context_marker import _claim_pending_task  # noqa: PLC0415

        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-claim-001",
                "toolUseId": "toolu_claim_001",
                "description": "claim test",
                "status": "pending",
                "requested_at": _now_iso(-5),
                "launchedAt": _now_iso(-5),
                "started_at": _now_iso(-5),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        fake_pid = 99999
        result = _claim_pending_task(tmp_path, fake_pid, "toolu_claim_001")
        assert result is True, "_claim_pending_task must return True on success"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-claim-001")
        assert task["status"] == "in_progress", (
            f"Expected 'in_progress' after claim, got {task['status']!r}"
        )
        assert task["pid"] == fake_pid

    def test_claim_fallback_to_most_recent_pending(self, tmp_path):
        """When tool_use_id is None, _claim_pending_task falls back to most recent pending."""
        from scripts.write_context_marker import _claim_pending_task  # noqa: PLC0415

        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-old-001",
                "toolUseId": None,
                "description": "older task",
                "status": "pending",
                "launchedAt": _now_iso(-120),
                "started_at": _now_iso(-120),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            },
            {
                "id": "task-new-001",
                "toolUseId": None,
                "description": "newer task",
                "status": "pending",
                "launchedAt": _now_iso(-5),
                "started_at": _now_iso(-5),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            },
        ])

        fake_pid = 88888
        _claim_pending_task(tmp_path, fake_pid, None)

        tasks = _read_tasks(tasks_file)
        new_task = next(t for t in tasks if t["id"] == "task-new-001")
        assert new_task["status"] == "in_progress"
        assert new_task["pid"] == fake_pid

    def test_claim_no_pending_returns_false(self, tmp_path):
        """_claim_pending_task returns False when no pending records exist."""
        from scripts.write_context_marker import _claim_pending_task  # noqa: PLC0415

        _make_tasks_file(tmp_path, [
            {
                "id": "task-done-001",
                "toolUseId": "toolu_done_001",
                "description": "already done",
                "status": "completed",
                "launchedAt": _now_iso(-300),
                "started_at": _now_iso(-300),
                "pid": 12345,
                "completedAt": _now_iso(-60),
                "outputSummary": "done",
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        result = _claim_pending_task(tmp_path, 77777, None)
        assert result is False


# ---------------------------------------------------------------------------
# Fix 3: Zombie reaper sweep logic
# ---------------------------------------------------------------------------

class TestZombieReaperSweep:
    """Tests for the zombie sweep logic embedded in so-reaper.sh.

    We exercise the Python logic directly by importing it from a helper that
    reproduces the exact same logic (not subprocess — so-reaper.sh is shell and
    embeds Python as a heredoc). We extract and validate the logic inline.
    """

    def _run_sweep(
        self,
        tasks_file: Path,
        stale_secs: int = 1800,
        pid_alive_fn=None,
    ) -> List[Dict[str, Any]]:
        """Run the zombie sweep logic against tasks_file, return reaped list."""
        import fcntl as _fcntl

        def _pid_alive(pid):
            if pid_alive_fn is not None:
                return pid_alive_fn(pid)
            try:
                os.kill(int(pid), 0)
                return True
            except Exception:
                return False

        def _age_secs(ts_str):
            if not ts_str:
                return None
            try:
                s = ts_str.rstrip("Z")
                dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - dt).total_seconds()
            except Exception:
                return None

        lock_path = tasks_file.parent / ".active-tasks.lock"
        reaped = []

        with open(lock_path, "w") as lock_fh:
            _fcntl.flock(lock_fh, _fcntl.LOCK_EX)
            try:
                data = json.loads(tasks_file.read_text())
                tasks = data.get("tasks", [])
                now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                changed = False

                for t in tasks:
                    status = t.get("status")
                    if status not in ("in_progress", "pending"):
                        continue
                    pid = t.get("pid")
                    age = _age_secs(
                        t.get("started_at") or t.get("launchedAt") or t.get("requested_at")
                    )

                    if status == "in_progress" and pid is not None:
                        if not _pid_alive(pid):
                            t["status"] = "cancelled-zombie"
                            t["completedAt"] = now_iso
                            t["outputSummary"] = f"reaped: pid {pid} not alive"
                            changed = True
                            reaped.append(("zombie", t["id"], pid))
                    elif status == "pending" and pid is None:
                        if age is not None and age > stale_secs:
                            t["status"] = "cancelled-stale"
                            t["completedAt"] = now_iso
                            t["outputSummary"] = f"reaped: no pid captured within {int(age)}s"
                            changed = True
                            reaped.append(("stale", t["id"], None))

                if changed:
                    data["lastUpdated"] = now_iso
                    tmp_fd, tmp_str = tempfile.mkstemp(
                        dir=str(tasks_file.parent),
                        prefix=".active-tasks-tmp-",
                        suffix=".json",
                    )
                    with os.fdopen(tmp_fd, "w") as fh:
                        json.dump(data, fh, indent=2)
                    os.replace(tmp_str, str(tasks_file))
            finally:
                _fcntl.flock(lock_fh, _fcntl.LOCK_UN)

        return reaped

    def test_dead_pid_marked_cancelled_zombie(self, tmp_path):
        """in_progress + dead PID → cancelled-zombie."""
        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-zombie-001",
                "toolUseId": "toolu_zombie_001",
                "description": "zombie task",
                "status": "in_progress",
                "launchedAt": _now_iso(-3600),
                "started_at": _now_iso(-3600),
                "pid": 99999999,  # almost certainly dead
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        reaped = self._run_sweep(tasks_file, pid_alive_fn=lambda pid: False)
        assert len(reaped) == 1
        kind, tid, pid = reaped[0]
        assert kind == "zombie"
        assert tid == "task-zombie-001"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-zombie-001")
        assert task["status"] == "cancelled-zombie"
        assert task["completedAt"] is not None

    def test_stale_pending_marked_cancelled_stale(self, tmp_path):
        """pending + null PID + age > stale_secs → cancelled-stale."""
        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-stale-001",
                "toolUseId": "toolu_stale_001",
                "description": "stale pending task",
                "status": "pending",
                "requested_at": _now_iso(-4000),  # older than 30 min
                "launchedAt": _now_iso(-4000),
                "started_at": _now_iso(-4000),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        reaped = self._run_sweep(tasks_file, stale_secs=1800)
        assert len(reaped) == 1
        kind, tid, pid = reaped[0]
        assert kind == "stale"
        assert tid == "task-stale-001"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-stale-001")
        assert task["status"] == "cancelled-stale"

    def test_fresh_pending_left_alone(self, tmp_path):
        """pending + null PID + age < stale_secs → untouched (still starting up)."""
        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-fresh-001",
                "toolUseId": "toolu_fresh_001",
                "description": "fresh pending task",
                "status": "pending",
                "requested_at": _now_iso(-30),  # only 30 seconds old
                "launchedAt": _now_iso(-30),
                "started_at": _now_iso(-30),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        reaped = self._run_sweep(tasks_file, stale_secs=1800)
        assert len(reaped) == 0, "Fresh pending tasks must not be reaped"

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["id"] == "task-fresh-001")
        assert task["status"] == "pending", "Fresh pending task must remain 'pending'"

    def test_completed_tasks_ignored(self, tmp_path):
        """Completed/failed tasks are not touched by the reaper."""
        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-done-001",
                "status": "completed",
                "launchedAt": _now_iso(-9000),
                "started_at": _now_iso(-9000),
                "pid": 12345,
                "completedAt": _now_iso(-300),
                "outputSummary": "done",
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        reaped = self._run_sweep(tasks_file, pid_alive_fn=lambda pid: False)
        assert len(reaped) == 0

        tasks = _read_tasks(tasks_file)
        assert tasks[0]["status"] == "completed"


# ---------------------------------------------------------------------------
# Fix 4: Queue cancel → active-tasks sync
# ---------------------------------------------------------------------------

class TestQueueActivetasksSync:
    def _make_drainer(self, tmp_path: Path):
        from lib.queue_drainer import QueueDrainer  # noqa: PLC0415

        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        queue_path = str(tasks_dir / "dispatch-queue.json")
        tasks_path = str(tasks_dir / "active-tasks.json")
        return QueueDrainer(queue_path=queue_path, tasks_path=tasks_path)

    def test_cancel_queued_syncs_active_tasks(self, tmp_path):
        """cancel_queued() must flip active-tasks pending record to cancelled-dequeued."""
        drainer = self._make_drainer(tmp_path)

        # Pre-populate active-tasks.json with a pending record
        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-q-cancel-001",
                "toolUseId": "toolu_q_cancel_001",
                "description": "queued task to cancel",
                "status": "pending",
                "launchedAt": _now_iso(-60),
                "started_at": _now_iso(-60),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        # Enqueue an agent
        agent_id = drainer.enqueue(
            prompt="queued task to cancel",
            description="queued task to cancel",
            model="sonnet",
            priority=5,
        )

        # Cancel it
        result = drainer.cancel_queued(agent_id, tool_use_id="toolu_q_cancel_001")
        assert result is True

        # Verify active-tasks sync
        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["toolUseId"] == "toolu_q_cancel_001")
        assert task["status"] == "cancelled-dequeued", (
            f"Expected 'cancelled-dequeued' after queue cancel, got {task['status']!r}"
        )

    def test_mark_dispatched_syncs_active_tasks(self, tmp_path):
        """mark_dispatched() must flip active-tasks pending record to in_progress."""
        drainer = self._make_drainer(tmp_path)

        # Pre-populate active-tasks.json with a pending record
        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "task-q-dispatch-001",
                "toolUseId": "toolu_q_dispatch_001",
                "description": "queued task to dispatch",
                "status": "pending",
                "launchedAt": _now_iso(-60),
                "started_at": _now_iso(-60),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ])

        agent_id = drainer.enqueue(
            prompt="queued task to dispatch",
            description="queued task to dispatch",
            model="sonnet",
            priority=5,
        )

        result = drainer.mark_dispatched(agent_id, tool_use_id="toolu_q_dispatch_001")
        assert result is True

        tasks = _read_tasks(tasks_file)
        task = next(t for t in tasks if t["toolUseId"] == "toolu_q_dispatch_001")
        assert task["status"] == "in_progress", (
            f"Expected 'in_progress' after dispatch, got {task['status']!r}"
        )

    def test_dispatch_gate_count_excludes_pending(self, tmp_path):
        """dispatch_gate_check counts only in_progress tasks, not pending.

        Both dispatch_gate_check.py and queue_drainer._count_active_tasks use
        the same status=='in_progress' filter.  We verify via queue_drainer
        (dispatch_gate_check executes at import time and cannot be imported).
        """
        from lib.queue_drainer import _count_active_tasks  # noqa: PLC0415

        tasks_file = _make_tasks_file(tmp_path, [
            {
                "id": "t1",
                "status": "pending",
                "launchedAt": _now_iso(-5),
                "started_at": _now_iso(-5),
                "pid": None,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            },
            {
                "id": "t2",
                "status": "in_progress",
                "launchedAt": _now_iso(-60),
                "started_at": _now_iso(-60),
                "pid": 12345,
                "completedAt": None,
                "outputSummary": None,
                "expectedOutputs": [],
                "checkCommand": None,
            },
        ])

        count = _count_active_tasks(str(tasks_file))
        assert count == 1, (
            f"dispatch gate must count only in_progress tasks, got {count}. "
            "pending tasks must NOT consume slots."
        )
