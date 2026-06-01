# SCOPE: both
"""Queue Drainer — slot-based dispatch queue for blocked agent launches.

When dispatch-gate.sh blocks an agent launch because all slots are full,
the agent prompt/description is enqueued here instead of being dropped.
When a task completes and a slot frees up, the orchestrator calls
get_ready_agents() to retrieve the next agents to launch.

Key differences from dispatch_helper / RateLimitQueue:
- RateLimitQueue: cooldown-based (time gates, rate limits)
- QueueDrainer:   slot-based (capacity gates, concurrency limits)

The queue persists to .cognitive-os/tasks/dispatch-queue.json.

Public API:
    from lib.queue_drainer import QueueDrainer

    drainer = QueueDrainer()
    drainer.enqueue(prompt="...", description="...", model="sonnet", priority=5)
    ready = drainer.get_ready_agents(max_count=3)
    for agent in ready:
        drainer.mark_dispatched(agent["id"])
    drainer.remove_completed(agent_id)
    print(drainer.format_drain_instruction())

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

from __future__ import annotations
from lib.time_utils import now_iso as _now_iso

import fcntl
import hashlib
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from lib.paths import project_root

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COGNITIVE_OS_DIR = ".cognitive-os"
_DEFAULT_QUEUE_PATH = os.path.join(_COGNITIVE_OS_DIR, "tasks", "dispatch-queue.json")
_DEFAULT_TASKS_PATH = os.path.join(_COGNITIVE_OS_DIR, "tasks", "active-tasks.json")
_DEFAULT_CONFIG_PATH = "cognitive-os.yaml"
_DEFAULT_MAX_PARALLEL = 5
_MAX_QUEUE_SIZE = 100
_MAX_AGE_SECONDS = 4 * 3600  # auto-prune items older than 4 hours
_CORRUPT_STATUS = "corrupt"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------




def _read_max_parallel_agents() -> int:
    """Parse max_parallel_agents from cognitive-os.yaml without yaml dep."""
    import re

    candidates: List[str] = []
    project_dir = project_root()
    if project_dir:
        candidates.append(os.path.join(project_dir, "cognitive-os.yaml"))
    candidates.append(_DEFAULT_CONFIG_PATH)

    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as fh:
                for line in fh:
                    m = re.match(r"^\s*max_parallel_agents:\s*(\d+)", line)
                    if m:
                        return int(m.group(1))
        except OSError:
            pass

    return _DEFAULT_MAX_PARALLEL


def _count_active_tasks(tasks_path: Optional[str] = None) -> int:
    """Count tasks with status == 'in_progress'."""
    path = tasks_path or _DEFAULT_TASKS_PATH
    if not os.path.isfile(path):
        return 0
    try:
        with open(path) as fh:
            data = json.load(fh)
        return sum(1 for t in data.get("tasks", []) if t.get("status") == "in_progress")
    except (json.JSONDecodeError, TypeError, OSError):
        return 0


def _prompt_fingerprint(prompt: str) -> str:
    """Return a short hash to detect duplicate prompts."""
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def _valid_prompt(prompt: Any) -> bool:
    """Return True when a queue item has relaunchable Agent intent."""
    return isinstance(prompt, str) and bool(prompt.strip())


# ---------------------------------------------------------------------------
# QueueDrainer
# ---------------------------------------------------------------------------


class QueueDrainer:
    """Manages a slot-based dispatch queue for blocked agent launches.

    When all agent slots are full, blocked launches are stored in the queue
    with their full prompt. When slots free up, get_ready_agents() returns
    the next batch to dispatch.

    The queue file is locked with fcntl for thread-safety between concurrent
    hook invocations.
    """

    def __init__(
        self,
        queue_path: Optional[str] = None,
        tasks_path: Optional[str] = None,
        max_parallel: Optional[int] = None,
    ) -> None:
        self.queue_path = queue_path or _DEFAULT_QUEUE_PATH
        self.tasks_path = tasks_path or _DEFAULT_TASKS_PATH
        self._max_parallel = max_parallel  # None = read from config on demand

    # ------------------------------------------------------------------ #
    # File I/O with locking                                               #
    # ------------------------------------------------------------------ #

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)

    def _load_queue(self) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.queue_path):
            return []
        try:
            with open(self.queue_path) as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _save_queue(self, items: List[Dict[str, Any]]) -> None:
        self._ensure_dir()
        tmp_path = self.queue_path + ".tmp"
        try:
            with open(tmp_path, "w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                json.dump(items, fh, indent=2)
                fh.flush()
                fcntl.flock(fh, fcntl.LOCK_UN)
            os.replace(tmp_path, self.queue_path)
        except OSError:
            # Best-effort: if we can't write, don't crash the hook
            pass

    def _load_locked(self) -> List[Dict[str, Any]]:
        """Load queue with shared lock (read-safe)."""
        if not os.path.isfile(self.queue_path):
            return []
        try:
            with open(self.queue_path) as fh:
                fcntl.flock(fh, fcntl.LOCK_SH)
                try:
                    data = json.load(fh)
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _prune_old(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove items older than _MAX_AGE_SECONDS or beyond max size."""
        cutoff = time.time() - _MAX_AGE_SECONDS
        fresh = [
            i for i in items
            if i.get("_enqueued_epoch", time.time()) > cutoff
        ]
        # Keep newest max-size items if overflow
        if len(fresh) > _MAX_QUEUE_SIZE:
            fresh.sort(key=lambda x: x.get("_enqueued_epoch", 0))
            fresh = fresh[-_MAX_QUEUE_SIZE:]
        return fresh

    def _quarantine_corrupt(self, items: List[Dict[str, Any]]) -> bool:
        """Mark invalid queued rows corrupt so they are never relaunched."""
        changed = False
        for item in items:
            if item.get("status") != "queued":
                continue
            if _valid_prompt(item.get("prompt", "")):
                continue
            item["status"] = _CORRUPT_STATUS
            item["corruption_reason"] = "empty Agent prompt"
            item["corrupted_at"] = _now_iso()
            changed = True
        return changed

    def _available_slots(self) -> int:
        """How many slots are currently free."""
        max_parallel = self._max_parallel
        if max_parallel is None:
            max_parallel = _read_max_parallel_agents()
        active = _count_active_tasks(self.tasks_path)
        return max(0, max_parallel - active)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def enqueue(
        self,
        prompt: str,
        description: str = "",
        model: str = "sonnet",
        priority: int = 5,
    ) -> str:
        """Add a blocked agent launch to the dispatch queue.

        Idempotent: if the same prompt fingerprint is already queued with
        status 'queued', it will not be added again.

        Args:
            prompt:      The full agent prompt text.
            description: Short human-readable description (100 chars max).
            model:       Model alias (e.g. "sonnet", "opus", "haiku").
            priority:    1=critical, 5=normal, 10=low. Lower dispatches first.

        Returns:
            The item id (UUID). If deduplicated, returns the existing id.
        """
        if not _valid_prompt(prompt):
            raise ValueError("dispatch queue prompt is empty; refusing to enqueue corrupt Agent launch")

        prompt = prompt.strip()
        priority = max(1, min(10, priority))
        fingerprint = _prompt_fingerprint(prompt)

        items = self._load_locked()
        items = self._prune_old(items)
        quarantined = self._quarantine_corrupt(items)

        # Idempotency check
        for item in items:
            if (
                item.get("_fingerprint") == fingerprint
                and item.get("status") == "queued"
            ):
                if quarantined:
                    self._save_queue(items)
                return item["id"]

        item_id = str(uuid.uuid4())
        now_epoch = time.time()
        new_item: Dict[str, Any] = {
            "id": item_id,
            "prompt": prompt,
            "description": description[:200] if description else prompt[:200],
            "model": model,
            "priority": priority,
            "enqueued_at": _now_iso(),
            "status": "queued",
            "_enqueued_epoch": now_epoch,
            "_fingerprint": fingerprint,
        }
        items.append(new_item)
        self._save_queue(items)
        return item_id

    def get_ready_agents(
        self,
        max_count: Optional[int] = None,
        use_advisor: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return queued agents that can launch given current slot availability.

        Agents are selected by priority (1=highest), then FIFO within
        the same priority. Only items with status='queued' are considered.

        When use_advisor=True (default), the QueueAdvisor dynamically reorders
        the candidates based on budget pressure, context usage, staleness, and
        dependency unblocking before the slot limit is applied. If the advisor
        raises any exception the original priority-FIFO order is used as a
        fallback so existing behaviour is never broken.

        Args:
            max_count:   Max agents to return. Defaults to available_slots.
            use_advisor: Reorder via QueueAdvisor heuristics (default True).

        Returns:
            List of dicts: {id, prompt, description, model, priority, enqueued_at}
            When use_advisor=True each dict also contains advisor_score and
            advisor_reason fields.
        """
        available = self._available_slots()
        if available <= 0:
            return []

        limit = min(available, max_count) if max_count is not None else available

        items = self._load_locked()
        items = self._prune_old(items)
        if self._quarantine_corrupt(items):
            self._save_queue(items)

        queued = [
            i for i in items
            if i.get("status") == "queued" and _valid_prompt(i.get("prompt", ""))
        ]
        queued.sort(key=lambda x: (x.get("priority", 5), x.get("_enqueued_epoch", 0)))

        # Build the canonical return structure first (all candidates)
        candidates = [
            {
                "id": item["id"],
                "prompt": item.get("prompt", ""),
                "description": item.get("description", ""),
                "model": item.get("model", "sonnet"),
                "priority": item.get("priority", 5),
                "enqueued_at": item.get("enqueued_at", ""),
            }
            for item in queued
        ]

        # Optionally reorder via advisor (additive — fallback preserves original order)
        if use_advisor and candidates:
            try:
                from lib.queue_advisor import QueueAdvisor  # noqa: PLC0415

                # NOTE: custom resolution — differs from lib.paths.project_root() (Pattern C).
                # See tests/unit/test_project_dir_resolution.py for rationale.
                project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
                advisor = QueueAdvisor(project_dir=project_dir)
                candidates = advisor.advise(candidates)
            except Exception:
                # Advisor failure: fall back to priority-FIFO silently
                pass

        return candidates[:limit]

    # ------------------------------------------------------------------ #
    # Fix 4 (ADR-097): Queue ↔ active-tasks.json sync helpers            #
    # ------------------------------------------------------------------ #

    def _sync_active_tasks(
        self,
        tool_use_id: Optional[str],
        new_status: str,
        note: str = "",
    ) -> bool:
        """Update the active-tasks.json record matching tool_use_id.

        If tool_use_id is None or not found, searches for the most-recent
        'pending' record (best-effort fallback).

        new_status values used by this module:
          - "cancelled-dequeued": queue item cancelled before dispatch
          - "in_progress": queue item was dispatched

        Uses the same flock + atomic-rename pattern as agent-prelaunch.sh.
        Returns True if a record was updated, False otherwise.
        Never raises.
        """
        if not os.path.isfile(self.tasks_path):
            return False

        lock_path = os.path.join(os.path.dirname(self.tasks_path), ".active-tasks.lock")
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        try:
            with open(lock_path, "w") as lock_fh:
                fcntl.flock(lock_fh, fcntl.LOCK_EX)
                try:
                    with open(self.tasks_path) as fh:
                        data = json.load(fh)
                    tasks: List[Dict[str, Any]] = data.get("tasks", [])
                    now = _now_iso()

                    matched_idx: Optional[int] = None

                    if tool_use_id:
                        for idx, t in enumerate(tasks):
                            if (
                                t.get("toolUseId") == tool_use_id
                                and t.get("status") == "pending"
                            ):
                                matched_idx = idx
                                break

                    if matched_idx is None:
                        # Fallback: most recently created pending record
                        pending = [
                            (idx, t)
                            for idx, t in enumerate(tasks)
                            if t.get("status") == "pending"
                        ]
                        if pending:
                            pending.sort(
                                key=lambda x: x[1].get("launchedAt", ""),
                                reverse=True,
                            )
                            matched_idx = pending[0][0]

                    if matched_idx is None:
                        return False

                    tasks[matched_idx]["status"] = new_status
                    tasks[matched_idx]["lastUpdated"] = now
                    if new_status in ("cancelled-dequeued",):
                        tasks[matched_idx]["completedAt"] = now
                    if note:
                        tasks[matched_idx]["outputSummary"] = note

                    data["lastUpdated"] = now

                    tmp_path = self.tasks_path + ".tmp"
                    with open(tmp_path, "w") as fh:
                        json.dump(data, fh, indent=2)
                    os.replace(tmp_path, self.tasks_path)
                    return True
                finally:
                    fcntl.flock(lock_fh, fcntl.LOCK_UN)
        except Exception:
            return False

    def cancel_queued(self, agent_id: str, tool_use_id: Optional[str] = None) -> bool:
        """Remove an agent from the dispatch queue and mark its active-tasks record.

        When a queued item is cancelled (e.g., user interrupt or explicit cancel):
          - dispatch-queue.json: item is removed
          - active-tasks.json: matching 'pending' record → 'cancelled-dequeued'

        Args:
            agent_id:    The id returned by enqueue().
            tool_use_id: Optional Claude Code tool_use_id for precise matching.

        Returns:
            True if the queue item was found and removed, False otherwise.
        """
        items = self._load_locked()
        target: Optional[Dict[str, Any]] = None
        remaining = []
        for item in items:
            if item.get("id") == agent_id:
                target = item
            else:
                remaining.append(item)

        if target is None:
            return False

        self._save_queue(remaining)

        # Sync active-tasks.json — use provided tool_use_id or fall back
        tui = tool_use_id or target.get("tool_use_id")
        self._sync_active_tasks(
            tui,
            "cancelled-dequeued",
            note=f"queue item {agent_id} cancelled before dispatch",
        )
        return True

    def mark_dispatched(self, agent_id: str, tool_use_id: Optional[str] = None) -> bool:
        """Mark a queued agent as 'dispatching' and sync active-tasks.

        When the agent is about to be launched from the queue:
          - dispatch-queue.json: status → 'dispatching'
          - active-tasks.json:   matching 'pending' record → 'in_progress'

        Args:
            agent_id:    The id returned by enqueue().
            tool_use_id: Optional Claude Code tool_use_id for precise matching.

        Returns:
            True if the item was found and updated, False otherwise.
        """
        items = self._load_locked()
        updated = False
        target: Optional[Dict[str, Any]] = None
        for item in items:
            if item.get("id") == agent_id and item.get("status") == "queued":
                item["status"] = "dispatching"
                item["dispatched_at"] = _now_iso()
                target = item
                updated = True
                break
        if updated:
            self._save_queue(items)
            # Sync active-tasks.json
            tui = tool_use_id or (target.get("tool_use_id") if target else None)
            self._sync_active_tasks(tui, "in_progress", note="dispatched from queue")
        return updated

    def remove_completed(self, agent_id: str) -> bool:
        """Remove an agent from the queue after it has completed.

        Args:
            agent_id: The id returned by enqueue().

        Returns:
            True if the item was found and removed, False otherwise.
        """
        items = self._load_locked()
        original_len = len(items)
        items = [i for i in items if i.get("id") != agent_id]
        if len(items) < original_len:
            self._save_queue(items)
            return True
        return False

    def queue_length(self, status: Optional[str] = None) -> int:
        """Return the number of items in the queue, optionally filtered by status."""
        items = self._load_locked()
        if status is None:
            return len(items)
        return sum(1 for i in items if i.get("status") == status)

    def position_in_queue(self, agent_id: str) -> int:
        """Return the 1-based queue position for an agent (priority-sorted).

        Returns -1 if not found.
        """
        items = self._load_locked()
        queued = [i for i in items if i.get("status") == "queued"]
        queued.sort(key=lambda x: (x.get("priority", 5), x.get("_enqueued_epoch", 0)))
        for idx, item in enumerate(queued, start=1):
            if item.get("id") == agent_id:
                return idx
        return -1

    def format_drain_instruction(self) -> str:
        """Return a human-readable message for the orchestrator to act on.

        Example output:
            "QUEUE DRAIN: 2 agents ready to launch (3 slots available, 5 queued total)"
        """
        available = self._available_slots()
        total_queued = self.queue_length(status="queued")

        if total_queued == 0:
            return "QUEUE DRAIN: dispatch queue is empty — nothing to launch"

        if available <= 0:
            return (
                f"QUEUE DRAIN: no slots available — "
                f"{total_queued} agent(s) remain queued"
            )

        ready_count = min(available, total_queued)
        return (
            f"QUEUE DRAIN: {ready_count} agent(s) ready to launch "
            f"({available} slot(s) available, {total_queued} queued total)"
        )
