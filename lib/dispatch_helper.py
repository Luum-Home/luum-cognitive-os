# SCOPE: both
"""Dispatch Helper — lightweight scheduling helper for dispatch-gate.sh.

Called by hooks/dispatch-gate.sh on every Agent PreToolUse to decide whether
to allow a new agent launch, enqueue it for later, or drain the ready queue.

Design constraints (runs on every PreToolUse):
- No heavy imports at module level — only stdlib
- Graceful degradation when config / task files / queue are missing
- Falls back to simple priority sort (WorkloadScheduler removed 2026-04-20)
- Never raises — all errors are caught and surfaced in the returned dict

Public API:
    check_slot_availability() -> dict
    enqueue_agent(description, priority) -> str
    dequeue_ready_agents() -> list[dict]
    format_dispatch_status() -> str

Usage from shell:
    python3 -c "from lib.dispatch_helper import check_slot_availability; \
        import json, sys; print(json.dumps(check_slot_availability()))"

Python 3.9+ compatible. Author: luum.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from lib.config_loader import read_top_level_int as _cl_read_top_level_int
from lib.paths import project_root

# ---------------------------------------------------------------------------
# Internal helpers — thin shims that delegate to lib.config_loader
# ---------------------------------------------------------------------------

_DEFAULT_MAX_PARALLEL = 5
_STALE_STARTING_SECONDS = 30 * 60
_COGNITIVE_OS_DIR = ".cognitive-os"
_TASKS_PATH = os.path.join(_COGNITIVE_OS_DIR, "tasks", "active-tasks.json")


def _find_config_path() -> Optional[str]:
    """Return the first readable cognitive-os.yaml found on the search path.

    Uses :func:`lib.paths.project_root` for env-var resolution (Pattern A),
    then falls back to cwd-relative candidates.  Delegates the full candidate
    logic to :mod:`lib.config_loader`.
    """
    # Preserve the explicit project_root() call to satisfy the R1 contract test
    # in test_project_dir_resolution.py (PATTERN_A_MIGRATED_CALL check).
    project_dir = project_root()
    candidates = [
        "cognitive-os.yaml",
        os.path.join(_COGNITIVE_OS_DIR, "cognitive-os.yaml"),
    ]
    if project_dir:
        candidates.insert(0, os.path.join(str(project_dir), "cognitive-os.yaml"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _read_max_parallel_agents(config_path: Optional[str] = None) -> int:
    """Parse max_parallel_agents from cognitive-os.yaml.

    Delegates to :func:`lib.config_loader.read_top_level_int`.
    Falls back to _DEFAULT_MAX_PARALLEL on any error.
    """
    return _cl_read_top_level_int(
        "max_parallel_agents", _DEFAULT_MAX_PARALLEL, config_path or _find_config_path()
    )


def _age_seconds(task: Dict[str, Any]) -> Optional[float]:
    """Return task age from lifecycle timestamps, or None when unavailable."""
    ts = task.get("started_at") or task.get("launchedAt") or task.get("requested_at")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).rstrip("Z")).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except (TypeError, ValueError):
        return None


def _pid_alive(pid: Any) -> bool:
    """Return True when pid appears alive, False for dead/invalid PIDs."""
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _is_dispatch_active(task: Dict[str, Any]) -> bool:
    """Return whether a task should consume a dispatch slot.

    ADR-102 rule:
    - pending records never consume slots.
    - in_progress + live PID consumes a slot.
    - in_progress + dead PID does not consume a slot; reaper marks terminal.
    - in_progress + pid=null consumes a startup grace slot only while fresh.
    """
    if task.get("status") != "in_progress":
        return False
    pid = task.get("pid")
    if pid is not None:
        return _pid_alive(pid)
    age = _age_seconds(task)
    return age is None or age <= _STALE_STARTING_SECONDS


def _count_active_tasks(tasks_path: Optional[str] = None) -> int:
    """Count tasks that should consume dispatch slots from active-tasks.json.

    Returns 0 on any error (missing file, parse failure, etc.).
    """
    path = tasks_path or _TASKS_PATH
    if not os.path.isfile(path):
        return 0

    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        tasks = data.get("tasks", [])
        return sum(1 for t in tasks if _is_dispatch_active(t))
    except (json.JSONDecodeError, TypeError, OSError, KeyError):
        return 0


def _get_queue() -> Any:
    """Return a RateLimitQueue instance, or None on import failure."""
    try:
        from lib.rate_limiter import RateLimitQueue  # noqa: PLC0415

        return RateLimitQueue()
    except Exception:  # pragma: no cover — import failure in unusual envs
        return None


def _count_queued(queue: Any) -> int:
    """Return the number of items currently in the queue."""
    if queue is None:
        return 0
    try:
        return len(queue.peek())
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_slot_availability(
    config_path: Optional[str] = None,
    tasks_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Check whether a new agent launch slot is available.

    Args:
        config_path: Optional override for cognitive-os.yaml location.
        tasks_path:  Optional override for active-tasks.json location.

    Returns:
        {
            "available": bool,   # True when active < max
            "active":   int,     # Current in_progress task count
            "max":      int,     # max_parallel_agents from config
            "queued":   int,     # Items currently in the rate-limit queue
        }
    """
    max_agents = _read_max_parallel_agents(config_path)
    active = _count_active_tasks(tasks_path)
    queue = _get_queue()
    queued = _count_queued(queue)

    return {
        "available": active < max_agents,
        "active": active,
        "max": max_agents,
        "queued": queued,
    }


def enqueue_agent(description: str, priority: int = 5) -> str:
    """Enqueue a blocked agent launch for retry after cooldown.

    Args:
        description: Human-readable description of the blocked agent task.
        priority:    Priority level 1–10 (1=critical, 5=normal, 10=low).

    Returns:
        A queue_id string (8-char hex UUID prefix).
        Returns "queue-unavailable" if the queue cannot be reached.
    """
    queue = _get_queue()
    if queue is None:
        return "queue-unavailable"

    try:
        queue_id = queue.enqueue(
            action_type="agent_launch",
            context={"description": description},
            priority=max(1, min(10, priority)),
        )
        return queue_id
    except Exception:
        return "queue-error"


def dequeue_ready_agents() -> List[Dict[str, Any]]:
    """Return agents whose cooldown has expired and are ready to launch.

    Filters to items of type 'agent_launch' only.

    Returns:
        List of dicts, each containing:
            queue_id, description, priority, enqueued_at
        Ordered by priority (ascending), then FIFO within same priority.
        Returns [] on any error.
    """
    queue = _get_queue()
    if queue is None:
        return []

    try:
        ready_items = queue.dequeue_ready()
    except Exception:
        return []

    result: List[Dict[str, Any]] = []
    for item in ready_items:
        if item.get("action_type") != "agent_launch":
            continue
        context = item.get("context", {})
        result.append(
            {
                "queue_id": item.get("queue_id", ""),
                "description": context.get("description", ""),
                "priority": item.get("priority", 5),
                "enqueued_at": item.get("enqueued_at", 0.0),
            }
        )

    return result


def format_dispatch_status(
    config_path: Optional[str] = None,
    tasks_path: Optional[str] = None,
) -> str:
    """Return a human-readable one-line dispatch status for stderr output.

    Example outputs:
        "Dispatch: 2/5 slots active, 0 queued — AVAILABLE"
        "Dispatch: 5/5 slots active, 3 queued — FULL (agent enqueued)"

    Args:
        config_path: Optional override for cognitive-os.yaml location.
        tasks_path:  Optional override for active-tasks.json location.

    Returns:
        Single-line status string (no trailing newline).
    """
    status = check_slot_availability(config_path=config_path, tasks_path=tasks_path)
    active = status["active"]
    max_agents = status["max"]
    queued = status["queued"]
    availability = "AVAILABLE" if status["available"] else "FULL (agent enqueued)"

    queued_part = f", {queued} queued" if queued > 0 else ", 0 queued"
    return f"Dispatch: {active}/{max_agents} slots active{queued_part} — {availability}"
