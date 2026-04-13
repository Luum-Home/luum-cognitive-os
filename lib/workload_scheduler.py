# scope: both
"""Workload Scheduler -- Intelligent task dispatch within rate limits.

Plans the dispatch order and timing for multiple concurrent tasks based on
current rate limit availability, task priority, estimated cost, and model
requirements. Integrates with RateLimiter to respect phase-aware limits.

Usage:
    from lib.workload_scheduler import WorkloadScheduler, TaskRequest

    scheduler = WorkloadScheduler()
    tasks = [
        TaskRequest(id="t1", description="Implement auth", priority=1,
                    estimated_tokens=50000, model="opus", estimated_cost_usd=1.50),
        TaskRequest(id="t2", description="Write tests", priority=5,
                    estimated_tokens=20000, model="sonnet", estimated_cost_usd=0.30),
    ]
    plan = scheduler.plan(tasks)
    print(plan.summary)

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from lib.model_catalog import ModelCatalog
from lib.rate_limiter import (
    VALID_ACTIONS,
    RateLimitConfig,
    RateLimiter,
)

# Model cost reference (per 1M tokens) — derived from ModelCatalog.
# Kept as a module-level dict for backward compatibility with external importers.
MODEL_COSTS: Dict[str, Tuple[float, float]] = {
    alias: (ModelCatalog.get(alias).input_price_per_m,
            ModelCatalog.get(alias).output_price_per_m)
    for alias in ModelCatalog.all_aliases()
}

# Default token split assumption: 40% input, 60% output
DEFAULT_INPUT_RATIO = 0.4
DEFAULT_OUTPUT_RATIO = 0.6


@dataclass
class TaskRequest:
    """A task to be scheduled for agent dispatch.

    Attributes:
        id: Unique task identifier.
        description: Human-readable task description.
        priority: Priority level (1=critical, 5=normal, 10=low). Lower
            numbers are dispatched first.
        estimated_tokens: Estimated total token usage (input + output).
        model: Model to use (e.g. "opus", "sonnet", "haiku").
        estimated_cost_usd: Estimated cost in USD. If 0.0, auto-calculated
            from estimated_tokens and model.
    """

    id: str
    description: str
    priority: int = 5
    estimated_tokens: int = 0
    model: str = "sonnet"
    estimated_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.priority < 1:
            self.priority = 1
        if self.priority > 10:
            self.priority = 10
        if self.estimated_cost_usd <= 0.0 and self.estimated_tokens > 0:
            self.estimated_cost_usd = estimate_task_cost(
                self.estimated_tokens, self.model
            )


@dataclass
class SchedulePlan:
    """Result of scheduling a batch of tasks.

    Attributes:
        dispatch_now: Tasks that can be dispatched immediately within
            current rate limits.
        queued: Tasks that must wait because rate limits are saturated.
        next_dispatch_at: Epoch timestamp when the next queued task
            becomes eligible. None if no tasks are queued.
        slots_available: Number of agent launch slots currently available.
        slots_total: Total agent launch slots (effective limit).
        summary: Human-readable plan summary.
    """

    dispatch_now: List[TaskRequest] = field(default_factory=list)
    queued: List[TaskRequest] = field(default_factory=list)
    next_dispatch_at: Optional[float] = None
    slots_available: int = 0
    slots_total: int = 0
    summary: str = ""


def estimate_task_cost(estimated_tokens: int, model: str = "sonnet") -> float:
    """Estimate the USD cost of a task from token count and model.

    Uses the default input/output ratio (40/60) and ModelCatalog pricing.

    Args:
        estimated_tokens: Total tokens (input + output).
        model: Model name (e.g. "opus", "sonnet", "haiku").

    Returns:
        Estimated cost in USD.
    """
    input_tokens = int(estimated_tokens * DEFAULT_INPUT_RATIO)
    output_tokens = int(estimated_tokens * DEFAULT_OUTPUT_RATIO)
    try:
        cost = ModelCatalog.estimate_cost(model, input_tokens, output_tokens)
    except KeyError:
        cost = ModelCatalog.estimate_cost("sonnet", input_tokens, output_tokens)
    return round(cost, 4)


class WorkloadScheduler:
    """Plans task dispatch order respecting rate limits and priorities.

    The scheduler reads current rate limit state to determine how many
    agent launch slots are available, then fills them with the highest-
    priority tasks. Remaining tasks are queued for later dispatch.

    Args:
        rate_limiter: An existing RateLimiter instance. If None, creates
            one with default settings.
        config: Rate limit config. Ignored if rate_limiter is provided.
        phase: Project phase. Ignored if rate_limiter is provided.
        state_path: State file path. Ignored if rate_limiter is provided.
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        config: Optional[RateLimitConfig] = None,
        phase: Optional[str] = None,
        state_path: str = ".cognitive-os/rate-limit-state.json",
    ):
        if rate_limiter is not None:
            self._rl = rate_limiter
        else:
            self._rl = RateLimiter(
                config=config,
                state_path=state_path,
                phase=phase or "stabilization",
            )

    @property
    def rate_limiter(self) -> RateLimiter:
        """The underlying rate limiter instance."""
        return self._rl

    def available_slots(self) -> int:
        """Return the number of agent launch slots currently available.

        This is the effective limit minus the number of recent launches
        within the rate limit window.
        """
        status = self._rl.get_status()
        return status["agent_launch"]["remaining"]

    def next_slot_available_in(self) -> Optional[float]:
        """Return seconds until the next agent launch slot opens.

        Examines the oldest timestamp within the rate limit window and
        computes when it will age out. Returns None if slots are already
        available.
        """
        if self.available_slots() > 0:
            return None

        # Find the oldest agent_launch timestamp within the window
        now = time.time()
        window = 3600  # agent_launch window is 1 hour
        timestamps = self._rl.state.agent_launches
        recent = sorted(t for t in timestamps if now - t < window)

        if not recent:
            return None

        # The oldest recent timestamp will expire first
        oldest = recent[0]
        seconds_until_free = (oldest + window) - now
        return max(0.0, seconds_until_free)

    def plan(self, tasks: List[TaskRequest]) -> SchedulePlan:
        """Create a dispatch plan for the given tasks.

        Algorithm:
        1. Sort tasks by priority (ascending -- lower number = higher priority).
        2. Determine available agent launch slots.
        3. Fill available slots with highest-priority tasks.
        4. Remaining tasks go to the queue.

        Also checks the cost cap: if dispatching a task would exceed the
        hourly cost cap, it is queued instead.

        Args:
            tasks: List of TaskRequest objects to schedule.

        Returns:
            A SchedulePlan with dispatch_now and queued lists.
        """
        if not tasks:
            return SchedulePlan(
                slots_available=self.available_slots(),
                slots_total=self._rl.effective_limit("agent_launch"),
                summary="No tasks to schedule.",
            )

        # Sort by priority (lower = more urgent), then by cost (cheaper first
        # for same priority, to maximize throughput)
        sorted_tasks = sorted(tasks, key=lambda t: (t.priority, t.estimated_cost_usd))

        slots = self.available_slots()
        total_slots = self._rl.effective_limit("agent_launch")

        # Check cost headroom
        status = self._rl.get_status()
        cost_remaining = status["cost"]["remaining_usd"]

        dispatch_now: List[TaskRequest] = []
        queued: List[TaskRequest] = []

        for task in sorted_tasks:
            if len(dispatch_now) < slots and task.estimated_cost_usd <= cost_remaining:
                dispatch_now.append(task)
                cost_remaining -= task.estimated_cost_usd
            else:
                queued.append(task)

        # Compute next dispatch time
        next_at: Optional[float] = None
        if queued:
            wait = self.next_slot_available_in()
            if wait is not None:
                next_at = time.time() + wait
            else:
                # Slots are available but cost is the bottleneck -- next cost
                # reset time
                if self._rl.state.cost_reset_at is not None:
                    next_at = self._rl.state.cost_reset_at
                else:
                    next_at = time.time() + self._rl.config.cooldown_seconds

        summary = self._format_summary(dispatch_now, queued, slots, total_slots)

        return SchedulePlan(
            dispatch_now=dispatch_now,
            queued=queued,
            next_dispatch_at=next_at,
            slots_available=slots,
            slots_total=total_slots,
            summary=summary,
        )

    def format_plan(self, plan: SchedulePlan) -> str:
        """Format a SchedulePlan as a human-readable string.

        Args:
            plan: The schedule plan to format.

        Returns:
            Multi-line string with dispatch and queue details.
        """
        lines: List[str] = [
            f"Workload Schedule (phase: {self._rl.phase}, "
            f"slots: {plan.slots_available}/{plan.slots_total}):",
        ]

        if plan.dispatch_now:
            lines.append(f"\n  DISPATCH NOW ({len(plan.dispatch_now)} tasks):")
            for i, task in enumerate(plan.dispatch_now, 1):
                lines.append(
                    f"    {i}. [P{task.priority}] {task.id}: {task.description[:60]} "
                    f"({task.model}, ~${task.estimated_cost_usd:.2f})"
                )

        if plan.queued:
            lines.append(f"\n  QUEUED ({len(plan.queued)} tasks):")
            for i, task in enumerate(plan.queued, 1):
                lines.append(
                    f"    {i}. [P{task.priority}] {task.id}: {task.description[:60]} "
                    f"({task.model}, ~${task.estimated_cost_usd:.2f})"
                )

            if plan.next_dispatch_at is not None:
                wait = max(0, int(plan.next_dispatch_at - time.time()))
                lines.append(f"\n  Next dispatch eligible in: {wait}s")

        # Show next N slot expiration times when queued
        if plan.queued:
            now = time.time()
            window = 3600
            recent = sorted(
                t for t in self._rl.state.agent_launches if now - t < window
            )
            if recent:
                expirations = [int(t + window - now) for t in recent[:5]]
                lines.append(f"  Next slots free in: {', '.join(f'{s}s' for s in expirations)}")

        if not plan.dispatch_now and not plan.queued:
            lines.append("  No tasks to schedule.")

        lines.append(f"\n  Total estimated cost: "
                     f"${sum(t.estimated_cost_usd for t in plan.dispatch_now + plan.queued):.2f}")

        return "\n".join(lines)

    @staticmethod
    def _format_summary(
        dispatch_now: List[TaskRequest],
        queued: List[TaskRequest],
        slots: int,
        total_slots: int,
    ) -> str:
        """Build a concise one-line summary."""
        total = len(dispatch_now) + len(queued)
        dispatch_cost = sum(t.estimated_cost_usd for t in dispatch_now)
        total_cost = dispatch_cost + sum(t.estimated_cost_usd for t in queued)

        if not queued:
            return (
                f"All {total} tasks dispatched immediately "
                f"({slots - len(dispatch_now)}/{total_slots} slots remaining, "
                f"~${dispatch_cost:.2f})."
            )
        return (
            f"{len(dispatch_now)}/{total} tasks dispatched now, "
            f"{len(queued)} queued "
            f"({slots - len(dispatch_now)}/{total_slots} slots remaining, "
            f"~${total_cost:.2f} total)."
        )
