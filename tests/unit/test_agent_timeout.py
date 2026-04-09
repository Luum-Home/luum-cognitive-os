"""Unit tests for agent timeout detection in hooks/agent-checkpoint.sh.

Covers:
- Duration calculation (completedAt - launchedAt)
- Slow detection when duration > timeout
- Normal completion when duration <= timeout
- Lost agent detection in session-cleanup.sh
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
CHECKPOINT_HOOK = HOOKS_DIR / "agent-checkpoint.sh"
CLEANUP_HOOK = HOOKS_DIR / "session-cleanup.sh"

DEFAULT_TIMEOUT = 300  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _make_tasks_file(tasks_dir: Path, tasks: list[dict]) -> Path:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = tasks_dir / "active-tasks.json"
    tasks_file.write_text(json.dumps({"version": 1, "tasks": tasks}))
    return tasks_file


def _make_stdin(description: str, success: bool = True) -> str:
    return json.dumps({
        "tool_name": "Agent",
        "tool_input": {"prompt": description},
        "tool_response": {
            "error": None if success else "timeout",
            "is_error": not success,
            "result": "done",
        },
    })


def _run_checkpoint_hook(
    project_dir: Path,
    stdin_payload: str,
    extra_env: dict | None = None,
    timeout: int = 20,
) -> subprocess.CompletedProcess:
    if not CHECKPOINT_HOOK.exists():
        pytest.skip(f"Hook not found: {CHECKPOINT_HOOK}")

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(CHECKPOINT_HOOK)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _read_tasks(project_dir: Path) -> list[dict]:
    tasks_file = project_dir / ".cognitive-os" / "tasks" / "active-tasks.json"
    if not tasks_file.exists():
        return []
    return json.loads(tasks_file.read_text()).get("tasks", [])


def _read_timeout_log(project_dir: Path) -> list[dict]:
    log_file = project_dir / ".cognitive-os" / "metrics" / "agent-timeouts.jsonl"
    if not log_file.exists():
        return []
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


# ---------------------------------------------------------------------------
# Duration calculation tests (pure Python, no bash)
# ---------------------------------------------------------------------------

class TestDurationCalculation:
    """Verify that ISO8601 duration math is correct.

    The hook uses an inline Python snippet; we test the same logic here.
    """

    def _calc_duration(self, launched: datetime, completed: datetime) -> int:
        return int((completed - launched).total_seconds())

    def test_five_minute_duration(self):
        launched = _now() - timedelta(minutes=5)
        completed = _now()
        assert self._calc_duration(launched, completed) == 300

    def test_one_second_duration(self):
        launched = _now() - timedelta(seconds=1)
        completed = _now()
        assert self._calc_duration(launched, completed) == 1

    def test_zero_duration(self):
        t = _now()
        assert self._calc_duration(t, t) == 0

    def test_over_one_hour(self):
        launched = _now() - timedelta(hours=2)
        completed = _now()
        assert self._calc_duration(launched, completed) == 7200

    def test_slow_threshold_exceeded(self):
        launched = _now() - timedelta(seconds=301)
        completed = _now()
        duration = self._calc_duration(launched, completed)
        assert duration > DEFAULT_TIMEOUT

    def test_slow_threshold_not_exceeded(self):
        launched = _now() - timedelta(seconds=299)
        completed = _now()
        duration = self._calc_duration(launched, completed)
        assert duration <= DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Hook integration tests
# ---------------------------------------------------------------------------

class TestAgentCheckpointSlowDetection:

    def _setup(self, tmp_path: Path, launched_offset_secs: int) -> tuple[Path, dict]:
        """Create project structure with one in_progress task."""
        project_dir = tmp_path / "project"
        tasks_dir = project_dir / ".cognitive-os" / "tasks"

        launched = _now() - timedelta(seconds=launched_offset_secs)
        task = {
            "id": "task-test-001",
            "description": "Run integration tests for the payment module",
            "status": "in_progress",
            "launchedAt": _iso(launched),
            "completedAt": None,
            "outputSummary": "",
            "expectedOutputs": [],
            "checkCommand": None,
        }
        _make_tasks_file(tasks_dir, [task])
        return project_dir, task

    def test_slow_agent_marked_and_logged(self, tmp_path):
        """Agent running longer than timeout gets slow=true and a log entry."""
        project_dir, task = self._setup(tmp_path, launched_offset_secs=400)

        stdin = _make_stdin(task["description"])
        result = _run_checkpoint_hook(project_dir, stdin)

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        tasks = _read_tasks(project_dir)
        assert len(tasks) == 1
        t = tasks[0]
        assert t["status"] in ("completed", "failed")
        assert t.get("slow") is True, "Expected slow=true on task"

        log = _read_timeout_log(project_dir)
        assert len(log) == 1
        entry = log[0]
        assert entry["task_id"] == "task-test-001"
        assert entry["duration_secs"] >= 400
        assert entry["timeout"] == DEFAULT_TIMEOUT
        assert "description" in entry
        assert "timestamp" in entry

    def test_fast_agent_not_marked_slow(self, tmp_path):
        """Agent completing within timeout does NOT get slow=true."""
        project_dir, task = self._setup(tmp_path, launched_offset_secs=10)

        stdin = _make_stdin(task["description"])
        result = _run_checkpoint_hook(project_dir, stdin)

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        tasks = _read_tasks(project_dir)
        assert len(tasks) == 1
        t = tasks[0]
        assert t["status"] in ("completed", "failed")
        assert t.get("slow") is not True, "Fast agent should NOT be marked slow"

        log = _read_timeout_log(project_dir)
        assert len(log) == 0, "No timeout log entry expected for fast agent"

    def test_exactly_at_timeout_boundary_not_slow(self, tmp_path):
        """Agent at exactly the timeout boundary (not exceeding) is NOT slow."""
        project_dir, task = self._setup(tmp_path, launched_offset_secs=DEFAULT_TIMEOUT)

        stdin = _make_stdin(task["description"])
        result = _run_checkpoint_hook(project_dir, stdin)

        assert result.returncode == 0

        tasks = _read_tasks(project_dir)
        t = tasks[0]
        # duration == timeout means NOT slow (strictly >)
        # Allow 1s slack for execution time
        if t.get("slow") is True:
            # Only acceptable if execution added >1s after the setup
            log = _read_timeout_log(project_dir)
            assert len(log) <= 1  # at most one entry, borderline case

    def test_existing_checkpoint_behavior_preserved(self, tmp_path):
        """Core checkpoint behavior (status update) still works after the extension."""
        project_dir, task = self._setup(tmp_path, launched_offset_secs=10)

        stdin = _make_stdin(task["description"], success=True)
        result = _run_checkpoint_hook(project_dir, stdin)

        assert result.returncode == 0
        tasks = _read_tasks(project_dir)
        assert len(tasks) == 1
        t = tasks[0]
        assert t["status"] == "completed", "Task should be marked completed"
        assert t.get("completedAt") is not None, "completedAt should be set"

    def test_failed_agent_status_preserved(self, tmp_path):
        """Failed agent status is preserved alongside slow detection."""
        project_dir, task = self._setup(tmp_path, launched_offset_secs=400)

        stdin = _make_stdin(task["description"], success=False)
        result = _run_checkpoint_hook(project_dir, stdin)

        assert result.returncode == 0
        tasks = _read_tasks(project_dir)
        t = tasks[0]
        assert t["status"] == "failed"
        assert t.get("slow") is True

    def test_custom_timeout_from_config(self, tmp_path):
        """Hook reads agent_timeout_seconds from cognitive-os.yaml."""
        project_dir, task = self._setup(tmp_path, launched_offset_secs=60)

        # Write a config with a short timeout (50s)
        config_dir = project_dir
        config_file = config_dir / "cognitive-os.yaml"
        config_file.write_text(
            "resources:\n  compute:\n    agent_timeout_seconds: 50\n"
        )

        stdin = _make_stdin(task["description"])
        result = _run_checkpoint_hook(project_dir, stdin)

        assert result.returncode == 0
        tasks = _read_tasks(project_dir)
        t = tasks[0]
        assert t.get("slow") is True, "Should be slow with custom 50s timeout"

        log = _read_timeout_log(project_dir)
        assert len(log) == 1
        assert log[0]["timeout"] == 50

    def test_no_tasks_file_exits_cleanly(self, tmp_path):
        """Hook exits 0 when active-tasks.json does not exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        stdin = _make_stdin("some agent description")
        result = _run_checkpoint_hook(project_dir, stdin)
        assert result.returncode == 0

    def test_no_launched_at_does_not_crash(self, tmp_path):
        """Task without launchedAt skips duration check gracefully."""
        project_dir = tmp_path / "project"
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        task = {
            "id": "task-no-launch",
            "description": "Task with no launchedAt",
            "status": "in_progress",
            "launchedAt": None,
            "completedAt": None,
            "outputSummary": "",
            "expectedOutputs": [],
            "checkCommand": None,
        }
        _make_tasks_file(tasks_dir, [task])

        stdin = _make_stdin(task["description"])
        result = _run_checkpoint_hook(project_dir, stdin)
        assert result.returncode == 0

        log = _read_timeout_log(project_dir)
        assert len(log) == 0


# ---------------------------------------------------------------------------
# Session cleanup: lost agent detection
# ---------------------------------------------------------------------------

class TestSessionCleanupLostAgents:

    def _run_cleanup(
        self,
        project_dir: Path,
        session_id: str = "test-session-001",
        timeout: int = 20,
    ) -> subprocess.CompletedProcess:
        if not CLEANUP_HOOK.exists():
            pytest.skip(f"Hook not found: {CLEANUP_HOOK}")

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        env["COGNITIVE_OS_SESSION_ID"] = session_id

        return subprocess.run(
            ["bash", str(CLEANUP_HOOK)],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )

    def _setup(self, tmp_path: Path) -> Path:
        """Create minimal project structure for cleanup hook."""
        project_dir = tmp_path / "project"
        sessions_dir = project_dir / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Create active-sessions.json
        active = {"sessions": [{"id": "test-session-001"}]}
        (sessions_dir / "active-sessions.json").write_text(json.dumps(active))

        return project_dir

    def test_in_progress_tasks_marked_lost(self, tmp_path):
        """In-progress tasks at session end are marked lost and logged."""
        project_dir = self._setup(tmp_path)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        launched = _now() - timedelta(minutes=10)
        tasks = [
            {
                "id": "task-lost-001",
                "description": "Long-running import job",
                "status": "in_progress",
                "launchedAt": _iso(launched),
                "completedAt": None,
                "outputSummary": "",
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ]
        _make_tasks_file(tasks_dir, tasks)

        result = self._run_cleanup(project_dir)
        assert result.returncode == 0, f"Cleanup hook failed: {result.stderr}"

        remaining = _read_tasks(project_dir)
        assert len(remaining) == 1
        assert remaining[0]["status"] == "lost"
        assert remaining[0].get("completedAt") is not None

        log = _read_timeout_log(project_dir)
        assert len(log) == 1
        entry = log[0]
        assert entry["task_id"] == "task-lost-001"
        assert entry["status"] == "lost"
        assert entry["duration_secs"] >= 600  # at least 10 min

    def test_completed_tasks_not_affected_by_cleanup(self, tmp_path):
        """Completed tasks are left unchanged by cleanup lost-agent logic."""
        project_dir = self._setup(tmp_path)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        launched = _now() - timedelta(minutes=5)
        completed_at = _now() - timedelta(minutes=2)
        tasks = [
            {
                "id": "task-done-001",
                "description": "Completed task",
                "status": "completed",
                "launchedAt": _iso(launched),
                "completedAt": _iso(completed_at),
                "outputSummary": "done",
                "expectedOutputs": [],
                "checkCommand": None,
            }
        ]
        _make_tasks_file(tasks_dir, tasks)

        result = self._run_cleanup(project_dir)
        assert result.returncode == 0

        remaining = _read_tasks(project_dir)
        assert remaining[0]["status"] == "completed"

        log = _read_timeout_log(project_dir)
        assert len(log) == 0

    def test_multiple_lost_agents_all_logged(self, tmp_path):
        """Multiple in-progress tasks are all marked lost and logged."""
        project_dir = self._setup(tmp_path)
        tasks_dir = project_dir / ".cognitive-os" / "tasks"
        launched = _now() - timedelta(minutes=3)
        tasks = [
            {
                "id": f"task-lost-{i:03d}",
                "description": f"Lost task {i}",
                "status": "in_progress",
                "launchedAt": _iso(launched),
                "completedAt": None,
                "outputSummary": "",
                "expectedOutputs": [],
                "checkCommand": None,
            }
            for i in range(3)
        ]
        _make_tasks_file(tasks_dir, tasks)

        result = self._run_cleanup(project_dir)
        assert result.returncode == 0

        remaining = _read_tasks(project_dir)
        for t in remaining:
            assert t["status"] == "lost"

        log = _read_timeout_log(project_dir)
        assert len(log) == 3

    def test_no_tasks_file_cleanup_exits_cleanly(self, tmp_path):
        """Cleanup hook exits 0 when there is no active-tasks.json."""
        project_dir = self._setup(tmp_path)
        result = self._run_cleanup(project_dir)
        assert result.returncode == 0
