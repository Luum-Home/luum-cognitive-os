# SCOPE: os-only
"""Agent Health Monitor — filesystem-based health checks for in-progress agents.

Detects dead/stuck agents without requiring Valkey or any external service.
Reads active-tasks.json and uses timestamp comparison + PID existence checks.

Usage:
    from lib.agent_health_monitor import AgentHealthMonitor

    monitor = AgentHealthMonitor()
    health = monitor.check_health()
    # health == {"healthy": [...], "timeout": [...], "dead": [...]}

    # Requeue timed-out agents that have retries remaining
    requeued = monitor.requeue_timeout_agents()

    # Move dead (orphaned) agents to the DLQ
    dead = monitor.report_dead_agents()

    print(monitor.format_health_report())

Python 3.9+ compatible. No external dependencies.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.config_loader import read_int_from_file as _cl_read_int_from_file
from lib.paths import project_root

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COGNITIVE_OS_DIR = ".cognitive-os"
_DEFAULT_TASKS_PATH = os.path.join(_COGNITIVE_OS_DIR, "tasks", "active-tasks.json")
_DEFAULT_CONFIG_PATH = "cognitive-os.yaml"
_DEFAULT_TIMEOUT_SECONDS = 300
_DEFAULT_MAX_RETRIES = 3

# How many times a timed-out agent can be requeued before going to DLQ
_MAX_REQUEUE_ATTEMPTS = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse ISO-8601 timestamp (with or without trailing Z) to UTC datetime."""
    if not ts:
        return None
    try:
        s = ts.rstrip("Z")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _age_seconds(started_at: str) -> Optional[float]:
    """Return how many seconds ago started_at was, or None if unparseable."""
    dt = _parse_iso(started_at)
    if dt is None:
        return None
    return (_now_utc() - dt).total_seconds()


def _pid_alive(pid: int) -> bool:
    """Return True if the process with the given PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


def _read_timeout_seconds(config_path: Optional[str] = None) -> int:
    """Parse agent_timeout_seconds from cognitive-os.yaml without PyYAML.

    Delegates to :func:`lib.config_loader.read_int_from_file` via a
    candidate-path list that preserves the characterised search order:

        1. ``${CLAUDE_PROJECT_DIR or COGNITIVE_OS_PROJECT_DIR}/cognitive-os.yaml``
        2. ``config_path`` argument (if provided)
        3. ``_DEFAULT_CONFIG_PATH`` (``"cognitive-os.yaml"``, cwd-relative)

    The search-order CONTRACT is:  project-dir candidate is checked FIRST,
    then the explicit arg, then the cwd-relative default.  This matches the
    locked behaviour in ``TestReadTimeoutSeconds.test_project_dir_yaml_takes_precedence_over_explicit_arg``.

    ``read_int_from_file`` returns ``None`` when the key is absent (not the
    default), so "key absent, try next candidate" vs "key found with default
    value, stop here" are correctly distinguished.
    """
    project_dir = project_root()

    candidates: List[str] = []
    if project_dir:
        candidates.append(os.path.join(str(project_dir), "cognitive-os.yaml"))
    if config_path:
        candidates.append(config_path)
    candidates.append(_DEFAULT_CONFIG_PATH)

    for path in candidates:
        if not os.path.isfile(path):
            continue
        value = _cl_read_int_from_file("agent_timeout_seconds", path)
        if value is not None:
            return value

    return _DEFAULT_TIMEOUT_SECONDS


def _resolve_paths(
    tasks_path: Optional[str],
    config_path: Optional[str],
) -> tuple[str, str]:
    """Return (tasks_path, config_path) with project-dir resolution."""
    project_dir = project_root()
    if not tasks_path:
        if project_dir:
            tasks_path = os.path.join(project_dir, _DEFAULT_TASKS_PATH)
        else:
            tasks_path = _DEFAULT_TASKS_PATH
    if not config_path:
        if project_dir:
            config_path = os.path.join(project_dir, _DEFAULT_CONFIG_PATH)
        else:
            config_path = _DEFAULT_CONFIG_PATH
    return tasks_path, config_path


# ---------------------------------------------------------------------------
# AgentHealthMonitor
# ---------------------------------------------------------------------------


class AgentHealthMonitor:
    """Filesystem-based health checker for in-progress agent tasks.

    Classifies each ``in_progress`` task as one of:

    * **healthy**  — task is running and within the timeout window
    * **timeout**  — task has been ``in_progress`` longer than ``agent_timeout_seconds``
    * **dead**     — task has a ``pid`` field and that PID no longer exists

    Dead agents trump timeout: if a PID is known and the process is gone, the
    task is classified as dead regardless of elapsed time.
    """

    def __init__(
        self,
        tasks_path: Optional[str] = None,
        config_path: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        dlq_path: Optional[str] = None,
        queue_path: Optional[str] = None,
    ) -> None:
        self.tasks_path, self.config_path = _resolve_paths(tasks_path, config_path)
        self._timeout_seconds = timeout_seconds  # None → read from config lazily
        self._dlq_path = dlq_path
        self._queue_path = queue_path

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def timeout_seconds(self) -> int:
        if self._timeout_seconds is not None:
            return self._timeout_seconds
        return _read_timeout_seconds(self.config_path)

    # ------------------------------------------------------------------ #
    # Core API                                                             #
    # ------------------------------------------------------------------ #

    def check_health(self) -> Dict[str, List[Dict[str, Any]]]:
        """Classify all in-progress tasks.

        Returns a dict with three lists:
            {
                "healthy":  [task, ...],
                "timeout":  [task, ...],
                "dead":     [task, ...],
            }

        Only tasks with ``status == "in_progress"`` are considered.
        Completed, failed, and lost tasks are ignored.
        """
        result: Dict[str, List[Dict[str, Any]]] = {
            "healthy": [],
            "timeout": [],
            "dead": [],
        }
        tasks = self._read_in_progress_tasks()
        if not tasks:
            return result

        limit = self.timeout_seconds

        for task in tasks:
            classification = self._classify_task(task, limit)
            result[classification].append(task)

        return result

    def requeue_timeout_agents(self) -> List[Dict[str, Any]]:
        """Move timed-out agents back to the dispatch queue (if retries remain).

        For each timed-out task:
        - If ``requeue_attempts`` < _MAX_REQUEUE_ATTEMPTS: enqueue to dispatch
          queue and mark task as ``failed`` in active-tasks.json.
        - Otherwise: call ``report_dead_agents`` logic (DLQ) instead.

        Returns the list of tasks that were successfully requeued.
        """
        health = self.check_health()
        requeued: List[Dict[str, Any]] = []

        for task in health["timeout"]:
            attempts = task.get("requeue_attempts", 0)
            if attempts < _MAX_REQUEUE_ATTEMPTS:
                enqueued = self._enqueue_to_dispatch(task)
                if enqueued:
                    self._update_task_status(
                        task["id"],
                        "failed",
                        extra={"requeue_attempts": attempts + 1},
                    )
                    requeued.append(task)
            else:
                # Exceeded requeue budget → send to DLQ
                self._send_to_dlq(task, reason="TIMEOUT_EXCEEDED_REQUEUE_LIMIT")

        return requeued

    def report_dead_agents(self) -> List[Dict[str, Any]]:
        """Send dead (orphaned) agents to the Dead Letter Queue.

        Returns the list of tasks that were sent to the DLQ.
        """
        health = self.check_health()
        dead_tasks = health["dead"]

        for task in dead_tasks:
            self._send_to_dlq(task, reason="DEAD_PROCESS")
            self._update_task_status(task["id"], "failed")

        return dead_tasks

    def format_health_report(self) -> str:
        """Return a human-readable summary of agent health."""
        health = self.check_health()
        n_healthy = len(health["healthy"])
        n_timeout = len(health["timeout"])
        n_dead = len(health["dead"])
        total = n_healthy + n_timeout + n_dead

        if total == 0:
            return "Agent Health: no in-progress agents."

        lines = [
            f"Agent Health: {total} agent(s) — "
            f"{n_healthy} healthy, {n_timeout} timeout, {n_dead} dead"
        ]

        if health["timeout"]:
            lines.append("")
            lines.append("TIMED-OUT agents:")
            for t in health["timeout"]:
                age = _age_seconds(t.get("started_at") or t.get("launchedAt") or "")
                age_str = f"{int(age)}s" if age is not None else "unknown age"
                lines.append(
                    f"  ⏱  [{t.get('id', '?')}] {t.get('description', '')[:80]}"
                    f"  (running {age_str}, limit {self.timeout_seconds}s)"
                )

        if health["dead"]:
            lines.append("")
            lines.append("DEAD agents (PID gone):")
            for t in health["dead"]:
                lines.append(
                    f"  ✗  [{t.get('id', '?')}] {t.get('description', '')[:80]}"
                    f"  (pid={t.get('pid', 'n/a')})"
                )

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    # Minimum task age before a dead PID can trigger "dead" classification.
    # PreToolUse hooks may record a now-dead shell PID before the agent process
    # actually starts.  A 5-second grace period covers that race condition
    # without hiding genuine orphaned agents.
    _MIN_AGE_FOR_DEAD_SECONDS: int = 5  # seconds

    def _classify_task(self, task: Dict[str, Any], limit: int) -> str:
        """Return 'healthy', 'timeout', or 'dead' for a single task.

        Classification rules:
        1. If PID is null/missing → skip PID check entirely; rely on age only.
           Tasks become stale (→ timeout) after the configured timeout limit.
        2. If PID is present and the process is dead, only classify as 'dead'
           when the task has been running for at least _MIN_AGE_FOR_DEAD_SECONDS
           (default 5 s).  This prevents false-positives during the brief window
           between the PreToolUse hook recording a transient PID and the actual
           agent process starting.
        3. Age-based timeout uses the configured limit.
        """
        ts = task.get("started_at") or task.get("launchedAt")
        age = _age_seconds(ts) if ts else None

        pid = task.get("pid")

        if pid is None:
            # No PID recorded — age-only classification using the configured limit.
            if age is not None and age > limit:
                return "timeout"
            return "healthy"

        # PID present — check liveness, but only after the short grace period.
        try:
            pid_int = int(pid)
            task_past_grace = age is not None and age >= self._MIN_AGE_FOR_DEAD_SECONDS
            if task_past_grace and not _pid_alive(pid_int):
                return "dead"
        except (TypeError, ValueError):
            # Unparseable PID — treat as missing.
            if age is not None and age > limit:
                return "timeout"
            return "healthy"

        # Timeout check: use the configured limit regardless of PID status.
        if age is not None and age > limit:
            return "timeout"

        return "healthy"

    def _read_in_progress_tasks(self) -> List[Dict[str, Any]]:
        """Load active-tasks.json and return only in_progress entries."""
        if not os.path.isfile(self.tasks_path):
            return []
        try:
            with open(self.tasks_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return [
                t for t in data.get("tasks", [])
                if isinstance(t, dict) and t.get("status") == "in_progress"
            ]
        except (json.JSONDecodeError, OSError):
            return []

    def _update_task_status(
        self,
        task_id: str,
        new_status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update the status (and optional extra fields) of a task in-place."""
        if not os.path.isfile(self.tasks_path):
            return False
        try:
            with open(self.tasks_path, encoding="utf-8") as fh:
                data = json.load(fh)

            found = False
            for task in data.get("tasks", []):
                if task.get("id") == task_id:
                    task["status"] = new_status
                    task["completedAt"] = _now_iso()
                    if extra:
                        task.update(extra)
                    found = True
                    break

            if found:
                data["lastUpdated"] = _now_iso()
                tmp_path = self.tasks_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2)
                os.replace(tmp_path, self.tasks_path)

            return found
        except (json.JSONDecodeError, OSError):
            return False

    def _enqueue_to_dispatch(self, task: Dict[str, Any]) -> bool:
        """Enqueue a task back to the dispatch queue for re-launch."""
        try:
            # Import lazily to avoid circular dependencies
            import sys

            project_dir = project_root()
            if project_dir:
                sys.path.insert(0, str(project_dir))

            from lib.queue_drainer import QueueDrainer  # type: ignore[import]

            kwargs: Dict[str, Any] = {}
            if self._queue_path:
                kwargs["queue_path"] = self._queue_path

            drainer = QueueDrainer(**kwargs)
            prompt = task.get("description", task.get("id", "unknown task"))
            drainer.enqueue(
                prompt=prompt,
                description=prompt[:200],
                model=task.get("model", "sonnet"),
                priority=task.get("priority", 5),
            )
            return True
        except Exception:  # noqa: BLE001
            return False

    def _send_to_dlq(self, task: Dict[str, Any], reason: str) -> bool:
        """Append a dead/exhausted task to the Dead Letter Queue."""
        try:
            import sys

            project_dir = project_root()
            if project_dir:
                sys.path.insert(0, str(project_dir))

            from lib.dead_letter_queue import DeadLetterQueue  # type: ignore[import]

            kwargs: Dict[str, Any] = {}
            if self._dlq_path:
                kwargs["dlq_file"] = Path(self._dlq_path)

            dlq = DeadLetterQueue(**kwargs)
            ts = task.get("started_at") or task.get("launchedAt") or ""
            age = _age_seconds(ts)
            age_str = f"{int(age)}s" if age is not None else "unknown"

            dlq.enqueue_dead_letter(
                task_id=task.get("id", "unknown"),
                description=task.get("description", "no description")[:500],
                failure_type=reason,
                retry_history=[],
                diagnosis=(
                    f"Agent health monitor: {reason}. "
                    f"Task was in_progress for {age_str}. "
                    f"pid={task.get('pid', 'n/a')}"
                ),
            )
            return True
        except Exception:  # noqa: BLE001
            return False
