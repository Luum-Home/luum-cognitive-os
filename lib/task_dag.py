# scope: both
"""Task DAG — Directed Acyclic Graph runner for agent orchestration.

Lets the orchestrator declare task dependencies and the system handles
execution order, parallelism detection, and state persistence. The DAG
does NOT launch agents itself — it tells the orchestrator what to launch.

Usage:
    from lib.task_dag import TaskDAG

    dag = TaskDAG(name="implement-auth")
    dag.add_task(id="research", description="Research auth", prompt="...", model="sonnet")
    dag.add_task(id="design", description="Design arch", prompt="...", depends_on=["research"])

    ready = dag.get_ready_tasks()   # Tasks whose deps are all completed
    dag.start_task("research")
    dag.complete_task("research", result="Done")
    ready = dag.get_ready_tasks()   # Now returns ["design"]

    dag.save()                      # Persist to .cognitive-os/tasks/dag-{name}.json
    dag = TaskDAG.load("implement-auth")  # Resume from disk

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COGNITIVE_OS_DIR = ".cognitive-os"
_DAG_DIR = os.path.join(_COGNITIVE_OS_DIR, "tasks")
_MAX_RETRIES = 3


class TaskStatus(str, Enum):
    """State machine for individual tasks."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_FINAL = "failed_final"


# Valid transitions
_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.READY},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.PENDING},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.FAILED: {TaskStatus.READY, TaskStatus.FAILED_FINAL},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED_FINAL: set(),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# TaskNode
# ---------------------------------------------------------------------------


@dataclass
class TaskNode:
    """A single task in the DAG."""

    id: str
    description: str
    prompt: str = ""
    model: str = "sonnet"
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = _MAX_RETRIES
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    agent_id: Optional[str] = None
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "prompt": self.prompt,
            "model": self.model,
            "depends_on": list(self.depends_on),
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "agent_id": self.agent_id,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskNode:
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            prompt=data.get("prompt", ""),
            model=data.get("model", "sonnet"),
            depends_on=data.get("depends_on", []),
            status=TaskStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", _MAX_RETRIES),
            created_at=data.get("created_at", _now_iso()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            agent_id=data.get("agent_id"),
            priority=data.get("priority", 5),
        )


# ---------------------------------------------------------------------------
# TaskDAG
# ---------------------------------------------------------------------------


class TaskDAG:
    """Directed Acyclic Graph of tasks with dependency tracking.

    The DAG manages task states, validates the graph structure (no cycles),
    computes execution waves, and persists state to disk for crash recovery.

    Args:
        name: Human-readable DAG name (used in the filename).
        dag_dir: Directory for DAG persistence files.
    """

    def __init__(self, name: str, dag_dir: str = _DAG_DIR) -> None:
        self.name = name
        self.dag_dir = dag_dir
        self._tasks: Dict[str, TaskNode] = {}
        self.created_at: str = _now_iso()
        self.updated_at: str = self.created_at

    # ------------------------------------------------------------------ #
    # Task management                                                      #
    # ------------------------------------------------------------------ #

    def add_task(
        self,
        id: str,
        description: str,
        prompt: str = "",
        model: str = "sonnet",
        depends_on: Optional[List[str]] = None,
        priority: int = 5,
        max_retries: int = _MAX_RETRIES,
    ) -> TaskNode:
        """Add a task to the DAG.

        Validates that:
        - The task ID is unique
        - All dependencies exist
        - Adding this task would not create a cycle

        Args:
            id: Unique task identifier.
            description: Human-readable description.
            prompt: Full agent prompt for execution.
            model: Model to use (e.g. "sonnet", "opus").
            depends_on: List of task IDs this task depends on.
            priority: Priority (1=critical, 10=low).
            max_retries: Max retry attempts on failure.

        Returns:
            The created TaskNode.

        Raises:
            ValueError: If ID exists, deps are missing, or cycle detected.
        """
        if id in self._tasks:
            raise ValueError(f"Task '{id}' already exists in DAG '{self.name}'")

        deps = depends_on or []

        # Validate deps exist
        for dep_id in deps:
            if dep_id not in self._tasks:
                raise ValueError(
                    f"Dependency '{dep_id}' not found in DAG '{self.name}'. "
                    f"Add it before '{id}'."
                )

        node = TaskNode(
            id=id,
            description=description,
            prompt=prompt,
            model=model,
            depends_on=deps,
            priority=priority,
            max_retries=max_retries,
        )

        # Temporarily add to check for cycles
        self._tasks[id] = node
        try:
            self._detect_cycles()
        except ValueError:
            del self._tasks[id]
            raise

        # Set initial status
        self._refresh_status(id)
        self.updated_at = _now_iso()
        return node

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the DAG.

        Also removes this task from any other task's depends_on list.

        Raises:
            KeyError: If task_id not found.
        """
        if task_id not in self._tasks:
            raise KeyError(f"Task '{task_id}' not found in DAG '{self.name}'")

        del self._tasks[task_id]
        for task in self._tasks.values():
            if task_id in task.depends_on:
                task.depends_on.remove(task_id)
        self._refresh_all_statuses()
        self.updated_at = _now_iso()

    def get_task(self, task_id: str) -> TaskNode:
        """Get a task by ID.

        Raises:
            KeyError: If not found.
        """
        if task_id not in self._tasks:
            raise KeyError(f"Task '{task_id}' not found in DAG '{self.name}'")
        return self._tasks[task_id]

    @property
    def tasks(self) -> Dict[str, TaskNode]:
        """All tasks in the DAG."""
        return dict(self._tasks)

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    # ------------------------------------------------------------------ #
    # State transitions                                                    #
    # ------------------------------------------------------------------ #

    def start_task(self, task_id: str, agent_id: Optional[str] = None) -> None:
        """Mark a task as RUNNING.

        Raises:
            KeyError: If not found.
            ValueError: If task is not in READY state.
        """
        task = self.get_task(task_id)
        if task.status != TaskStatus.READY:
            raise ValueError(
                f"Cannot start task '{task_id}': status is {task.status.value}, "
                f"expected 'ready'"
            )
        task.status = TaskStatus.RUNNING
        task.started_at = _now_iso()
        task.agent_id = agent_id
        self.updated_at = _now_iso()

    def complete_task(self, task_id: str, result: str = "") -> None:
        """Mark a task as COMPLETED and refresh downstream tasks.

        Raises:
            KeyError: If not found.
            ValueError: If task is not RUNNING.
        """
        task = self.get_task(task_id)
        if task.status != TaskStatus.RUNNING:
            raise ValueError(
                f"Cannot complete task '{task_id}': status is {task.status.value}, "
                f"expected 'running'"
            )
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = _now_iso()
        self._refresh_all_statuses()
        self.updated_at = _now_iso()

    def fail_task(self, task_id: str, error: str = "") -> None:
        """Mark a task as FAILED. If retries remain, set to FAILED (retryable).
        If retries exhausted, set to FAILED_FINAL and block downstream.

        Raises:
            KeyError: If not found.
            ValueError: If task is not RUNNING.
        """
        task = self.get_task(task_id)
        if task.status != TaskStatus.RUNNING:
            raise ValueError(
                f"Cannot fail task '{task_id}': status is {task.status.value}, "
                f"expected 'running'"
            )
        task.retries += 1
        task.error = error
        if task.retries >= task.max_retries:
            task.status = TaskStatus.FAILED_FINAL
        else:
            task.status = TaskStatus.FAILED
        self._refresh_all_statuses()
        self.updated_at = _now_iso()

    def retry_task(self, task_id: str) -> None:
        """Move a FAILED task back to READY for retry.

        Raises:
            KeyError: If not found.
            ValueError: If task is not in FAILED state.
        """
        task = self.get_task(task_id)
        if task.status != TaskStatus.FAILED:
            raise ValueError(
                f"Cannot retry task '{task_id}': status is {task.status.value}, "
                f"expected 'failed'"
            )
        task.status = TaskStatus.READY
        task.agent_id = None
        self.updated_at = _now_iso()

    # ------------------------------------------------------------------ #
    # Query methods                                                        #
    # ------------------------------------------------------------------ #

    def get_ready_tasks(self) -> List[TaskNode]:
        """Return all tasks that are ready to launch.

        A task is ready when:
        - All dependencies are COMPLETED
        - The task itself is PENDING or READY

        Returns sorted by priority (lower number = higher priority).
        """
        self._refresh_all_statuses()
        ready = [t for t in self._tasks.values() if t.status == TaskStatus.READY]
        ready.sort(key=lambda t: (t.priority, t.created_at))
        return ready

    def get_execution_plan(self) -> List[List[str]]:
        """Compute execution waves (topological levels).

        Returns a list of waves, where each wave is a list of task IDs
        that can execute in parallel. Tasks in wave N+1 depend on tasks
        in wave N or earlier.

        Returns:
            List of waves, e.g. [["a", "b"], ["c"], ["d", "e"]]
        """
        if not self._tasks:
            return []

        # Kahn's algorithm for topological level assignment
        in_degree: Dict[str, int] = {}
        adj: Dict[str, List[str]] = {tid: [] for tid in self._tasks}

        for tid, task in self._tasks.items():
            in_degree[tid] = len(task.depends_on)
            for dep_id in task.depends_on:
                adj[dep_id].append(tid)

        queue = deque(tid for tid, deg in in_degree.items() if deg == 0)
        waves: List[List[str]] = []

        while queue:
            wave = list(queue)
            wave.sort(key=lambda tid: (self._tasks[tid].priority, tid))
            waves.append(wave)
            next_queue: deque[str] = deque()
            for tid in wave:
                for child in adj[tid]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue

        return waves

    def is_complete(self) -> bool:
        """True if all tasks are COMPLETED."""
        return all(t.status == TaskStatus.COMPLETED for t in self._tasks.values())

    def is_blocked(self) -> bool:
        """True if no tasks can make progress (deadlock or all final-failed)."""
        if self.is_complete():
            return False
        if not self._tasks:
            return False

        for task in self._tasks.values():
            if task.status in (
                TaskStatus.READY,
                TaskStatus.RUNNING,
                TaskStatus.FAILED,
            ):
                return False
        return True

    def completed_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)

    def failed_count(self) -> int:
        return sum(
            1 for t in self._tasks.values()
            if t.status in (TaskStatus.FAILED, TaskStatus.FAILED_FINAL)
        )

    # ------------------------------------------------------------------ #
    # Validation                                                           #
    # ------------------------------------------------------------------ #

    def validate(self) -> None:
        """Validate the DAG structure.

        Checks:
        - All dependency references point to existing tasks
        - No cycles exist

        Raises:
            ValueError: On validation failure.
        """
        for tid, task in self._tasks.items():
            for dep_id in task.depends_on:
                if dep_id not in self._tasks:
                    raise ValueError(
                        f"Task '{tid}' depends on '{dep_id}' which does not exist"
                    )
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        """Detect cycles using Kahn's algorithm.

        Raises ValueError if a cycle is found.
        """
        in_degree: Dict[str, int] = {}
        adj: Dict[str, List[str]] = {tid: [] for tid in self._tasks}

        for tid, task in self._tasks.items():
            in_degree[tid] = len(task.depends_on)
            for dep_id in task.depends_on:
                if dep_id in adj:
                    adj[dep_id].append(tid)

        queue = deque(tid for tid, deg in in_degree.items() if deg == 0)
        visited = 0

        while queue:
            tid = queue.popleft()
            visited += 1
            for child in adj[tid]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if visited != len(self._tasks):
            # Find the cycle members for a useful error message
            cycle_members = [
                tid for tid, deg in in_degree.items() if deg > 0
            ]
            raise ValueError(
                f"Cycle detected in DAG '{self.name}' involving tasks: "
                f"{', '.join(cycle_members)}"
            )

    # ------------------------------------------------------------------ #
    # Status refresh                                                       #
    # ------------------------------------------------------------------ #

    def _refresh_status(self, task_id: str) -> None:
        """Refresh a single task's status based on dependencies."""
        task = self._tasks[task_id]
        if task.status in (
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.FAILED_FINAL,
        ):
            return

        all_deps_completed = all(
            self._tasks[dep_id].status == TaskStatus.COMPLETED
            for dep_id in task.depends_on
            if dep_id in self._tasks
        )

        any_dep_failed_final = any(
            self._tasks[dep_id].status == TaskStatus.FAILED_FINAL
            for dep_id in task.depends_on
            if dep_id in self._tasks
        )

        if any_dep_failed_final:
            # Downstream of a permanently failed task stays pending
            task.status = TaskStatus.PENDING
        elif all_deps_completed:
            task.status = TaskStatus.READY
        else:
            task.status = TaskStatus.PENDING

    def _refresh_all_statuses(self) -> None:
        """Refresh all task statuses in topological order."""
        for wave in self.get_execution_plan():
            for tid in wave:
                self._refresh_status(tid)

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _dag_path(self) -> str:
        return os.path.join(self.dag_dir, f"dag-{self.name}.json")

    def save(self) -> str:
        """Persist DAG state to disk.

        Uses fcntl file locking for concurrent access safety.

        Returns:
            The file path written to.
        """
        os.makedirs(self.dag_dir, exist_ok=True)
        path = self._dag_path()
        data = {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": _now_iso(),
            "tasks": {tid: task.to_dict() for tid, task in self._tasks.items()},
        }

        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                json.dump(data, fh, indent=2)
                fh.flush()
                fcntl.flock(fh, fcntl.LOCK_UN)
            os.replace(tmp_path, path)
        except OSError:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        return path

    @classmethod
    def load(cls, name: str, dag_dir: str = _DAG_DIR) -> TaskDAG:
        """Load a DAG from disk.

        Args:
            name: DAG name (matches the filename dag-{name}.json).
            dag_dir: Directory containing DAG files.

        Returns:
            A restored TaskDAG instance.

        Raises:
            FileNotFoundError: If the DAG file doesn't exist.
            json.JSONDecodeError: If the file is corrupted.
        """
        path = os.path.join(dag_dir, f"dag-{name}.json")
        with open(path) as fh:
            fcntl.flock(fh, fcntl.LOCK_SH)
            try:
                data = json.load(fh)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

        dag = cls(name=data.get("name", name), dag_dir=dag_dir)
        dag.created_at = data.get("created_at", _now_iso())
        dag.updated_at = data.get("updated_at", _now_iso())

        tasks_data = data.get("tasks", {})
        for tid, tdata in tasks_data.items():
            dag._tasks[tid] = TaskNode.from_dict(tdata)

        return dag

    @classmethod
    def list_dags(cls, dag_dir: str = _DAG_DIR) -> List[str]:
        """List all persisted DAG names.

        Returns:
            List of DAG names (without the dag- prefix and .json suffix).
        """
        if not os.path.isdir(dag_dir):
            return []
        names = []
        for fname in os.listdir(dag_dir):
            if fname.startswith("dag-") and fname.endswith(".json"):
                names.append(fname[4:-5])
        return sorted(names)

    def delete(self) -> bool:
        """Delete the persisted DAG file.

        Returns:
            True if deleted, False if file didn't exist.
        """
        path = self._dag_path()
        if os.path.isfile(path):
            os.unlink(path)
            return True
        return False

    # ------------------------------------------------------------------ #
    # Formatting                                                           #
    # ------------------------------------------------------------------ #

    def format_status(self) -> str:
        """Return a human-readable status report.

        Example:
            implement-auth: 2/6 completed
              [completed]     research-auth
              [failed_final]  research-db
              [pending]       design-arch (blocked by: research-db)
              [pending]       impl-auth (blocked by: design-arch)
              [pending]       impl-db (blocked by: design-arch)
              [pending]       integration-test (blocked by: impl-auth, impl-db)
        """
        total = len(self._tasks)
        completed = self.completed_count()
        failed = self.failed_count()

        lines = [f"{self.name}: {completed}/{total} completed"]
        if failed > 0:
            lines[0] += f", {failed} failed"

        # Show in topological order
        for wave in self.get_execution_plan():
            for tid in wave:
                task = self._tasks[tid]
                status_str = task.status.value
                line = f"  [{status_str:14s}] {tid}"

                if task.status == TaskStatus.PENDING and task.depends_on:
                    # Find which deps are not completed
                    blockers = [
                        dep for dep in task.depends_on
                        if dep in self._tasks
                        and self._tasks[dep].status != TaskStatus.COMPLETED
                    ]
                    if blockers:
                        line += f" (blocked by: {', '.join(blockers)})"

                if task.status == TaskStatus.FAILED:
                    line += f" (retry {task.retries}/{task.max_retries})"

                if task.status == TaskStatus.RUNNING and task.agent_id:
                    line += f" (agent: {task.agent_id})"

                lines.append(line)

        if self.is_complete():
            lines.append("  STATUS: ALL COMPLETED")
        elif self.is_blocked():
            lines.append("  STATUS: BLOCKED (no tasks can make progress)")

        return "\n".join(lines)

    def format_execution_plan(self) -> str:
        """Return a human-readable execution plan showing waves."""
        waves = self.get_execution_plan()
        if not waves:
            return f"{self.name}: empty DAG (no tasks)"

        lines = [f"{self.name}: execution plan ({len(waves)} waves)"]
        for i, wave in enumerate(waves):
            task_descs = []
            for tid in wave:
                task = self._tasks[tid]
                task_descs.append(f"{tid} ({task.model})")
            parallel = " [parallel]" if len(wave) > 1 else ""
            lines.append(f"  Wave {i}: {', '.join(task_descs)}{parallel}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"TaskDAG(name={self.name!r}, tasks={self.task_count}, "
            f"completed={self.completed_count()}, failed={self.failed_count()})"
        )
