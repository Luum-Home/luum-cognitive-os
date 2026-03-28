"""Unit tests for lib/workload_scheduler.py

Validates task scheduling logic: priority ordering, slot filling, cost
headroom checks, edge cases, and format output.
"""

import time

import pytest

from lib.rate_limiter import RateLimitConfig, RateLimiter
from lib.workload_scheduler import (
    DEFAULT_INPUT_RATIO,
    DEFAULT_OUTPUT_RATIO,
    MODEL_COSTS,
    SchedulePlan,
    TaskRequest,
    WorkloadScheduler,
    estimate_task_cost,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scheduler(tmp_path, phase="stabilization", **config_overrides):
    """Create a WorkloadScheduler with temp state and optional config."""
    cfg = RateLimitConfig(**config_overrides)
    rl = RateLimiter(
        config=cfg, state_path=str(tmp_path / "state.json"), phase=phase
    )
    return WorkloadScheduler(rate_limiter=rl)


def _task(id: str, priority: int = 5, tokens: int = 10000,
          model: str = "sonnet", cost: float = 0.0) -> TaskRequest:
    """Shorthand to create a TaskRequest."""
    return TaskRequest(
        id=id,
        description=f"Task {id}",
        priority=priority,
        estimated_tokens=tokens,
        model=model,
        estimated_cost_usd=cost,
    )


# ---------------------------------------------------------------------------
# TaskRequest
# ---------------------------------------------------------------------------


class TestTaskRequest:
    """TaskRequest dataclass behavior."""

    def test_auto_estimates_cost_from_tokens(self):
        """Cost should be auto-calculated when not provided."""
        task = TaskRequest(
            id="t1", description="test", estimated_tokens=100000, model="sonnet"
        )
        expected = estimate_task_cost(100000, "sonnet")
        assert task.estimated_cost_usd == expected
        assert task.estimated_cost_usd > 0

    def test_explicit_cost_overrides_auto(self):
        """When cost is explicitly provided, it should not be overridden."""
        task = TaskRequest(
            id="t1", description="test", estimated_tokens=100000,
            model="sonnet", estimated_cost_usd=5.0
        )
        assert task.estimated_cost_usd == 5.0

    def test_priority_clamped_to_valid_range(self):
        """Priority should be clamped between 1 and 10."""
        low = TaskRequest(id="t1", description="test", priority=0)
        high = TaskRequest(id="t2", description="test", priority=15)
        assert low.priority == 1
        assert high.priority == 10

    def test_zero_tokens_yields_zero_cost(self):
        """Zero tokens should yield zero estimated cost."""
        task = TaskRequest(id="t1", description="test", estimated_tokens=0)
        assert task.estimated_cost_usd == 0.0


# ---------------------------------------------------------------------------
# estimate_task_cost
# ---------------------------------------------------------------------------


class TestEstimateTaskCost:
    """Cost estimation from token count and model."""

    def test_sonnet_cost_calculation(self):
        """Sonnet cost should match published rates."""
        # 100K tokens, 40% input ($3/M), 60% output ($15/M)
        cost = estimate_task_cost(100000, "sonnet")
        input_cost = 100000 * 0.4 * 3.0 / 1_000_000
        output_cost = 100000 * 0.6 * 15.0 / 1_000_000
        expected = round(input_cost + output_cost, 4)
        assert cost == expected

    def test_opus_more_expensive_than_sonnet(self):
        """Opus should cost more than sonnet for the same tokens."""
        opus_cost = estimate_task_cost(50000, "opus")
        sonnet_cost = estimate_task_cost(50000, "sonnet")
        assert opus_cost > sonnet_cost

    def test_haiku_cheapest(self):
        """Haiku should be cheaper than sonnet."""
        haiku_cost = estimate_task_cost(50000, "haiku")
        sonnet_cost = estimate_task_cost(50000, "sonnet")
        assert haiku_cost < sonnet_cost

    def test_unknown_model_defaults_to_sonnet_pricing(self):
        """Unknown model should fall back to sonnet pricing."""
        unknown = estimate_task_cost(50000, "unknown-model")
        sonnet = estimate_task_cost(50000, "sonnet")
        assert unknown == sonnet

    def test_free_model_costs_zero(self):
        """Free model should cost zero."""
        cost = estimate_task_cost(100000, "openrouter/free")
        assert cost == 0.0


# ---------------------------------------------------------------------------
# WorkloadScheduler.plan — basic dispatch
# ---------------------------------------------------------------------------


class TestPlanBasicDispatch:
    """Tasks within available slots should all be dispatched."""

    def test_all_tasks_dispatched_when_slots_available(self, tmp_path):
        """All tasks fit when slots > task count."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=20)
        tasks = [_task("t1"), _task("t2"), _task("t3")]
        plan = scheduler.plan(tasks)
        assert len(plan.dispatch_now) == 3
        assert len(plan.queued) == 0

    def test_empty_task_list(self, tmp_path):
        """Empty task list should produce empty plan."""
        scheduler = _make_scheduler(tmp_path)
        plan = scheduler.plan([])
        assert len(plan.dispatch_now) == 0
        assert len(plan.queued) == 0
        assert "No tasks" in plan.summary

    def test_single_task_dispatched(self, tmp_path):
        """Single task should always be dispatched if slots available."""
        scheduler = _make_scheduler(tmp_path)
        plan = scheduler.plan([_task("t1")])
        assert len(plan.dispatch_now) == 1
        assert plan.dispatch_now[0].id == "t1"


# ---------------------------------------------------------------------------
# WorkloadScheduler.plan — priority ordering
# ---------------------------------------------------------------------------


class TestPlanPriorityOrdering:
    """Higher priority tasks should be dispatched first."""

    def test_critical_tasks_dispatched_first(self, tmp_path):
        """Priority 1 tasks should be dispatched before priority 10."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=2)
        tasks = [
            _task("low", priority=10),
            _task("critical", priority=1),
            _task("normal", priority=5),
        ]
        plan = scheduler.plan(tasks)
        assert len(plan.dispatch_now) == 2
        assert plan.dispatch_now[0].id == "critical"
        assert plan.dispatch_now[1].id == "normal"
        assert len(plan.queued) == 1
        assert plan.queued[0].id == "low"

    def test_same_priority_sorted_by_cost(self, tmp_path):
        """Tasks with same priority should prefer cheaper ones."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=1)
        tasks = [
            _task("expensive", priority=5, cost=2.0),
            _task("cheap", priority=5, cost=0.1),
        ]
        plan = scheduler.plan(tasks)
        assert plan.dispatch_now[0].id == "cheap"


# ---------------------------------------------------------------------------
# WorkloadScheduler.plan — slot exhaustion
# ---------------------------------------------------------------------------


class TestPlanSlotExhaustion:
    """Tasks exceeding available slots should be queued."""

    def test_excess_tasks_queued(self, tmp_path):
        """Tasks beyond available slots should go to queue."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=2)
        # Pre-fill 1 slot
        scheduler.rate_limiter.record("agent_launch")
        tasks = [_task("t1"), _task("t2"), _task("t3")]
        plan = scheduler.plan(tasks)
        # Only 1 slot remaining (2 - 1 used)
        assert len(plan.dispatch_now) == 1
        assert len(plan.queued) == 2

    def test_no_slots_available_all_queued(self, tmp_path):
        """When no slots available, all tasks should be queued."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=2)
        scheduler.rate_limiter.record("agent_launch")
        scheduler.rate_limiter.record("agent_launch")
        tasks = [_task("t1"), _task("t2")]
        plan = scheduler.plan(tasks)
        assert len(plan.dispatch_now) == 0
        assert len(plan.queued) == 2


# ---------------------------------------------------------------------------
# WorkloadScheduler.plan — cost headroom
# ---------------------------------------------------------------------------


class TestPlanCostHeadroom:
    """Tasks exceeding cost headroom should be queued."""

    def test_expensive_task_queued_when_cost_exceeded(self, tmp_path):
        """Task exceeding remaining cost cap should be queued."""
        scheduler = _make_scheduler(
            tmp_path, max_cost_per_hour_usd=1.0, max_agent_launches_per_hour=10
        )
        tasks = [
            _task("cheap", priority=1, cost=0.5),
            _task("expensive", priority=1, cost=0.8),
        ]
        plan = scheduler.plan(tasks)
        assert len(plan.dispatch_now) == 1
        assert plan.dispatch_now[0].id == "cheap"
        assert len(plan.queued) == 1
        assert plan.queued[0].id == "expensive"


# ---------------------------------------------------------------------------
# WorkloadScheduler — available_slots and next_slot_available_in
# ---------------------------------------------------------------------------


class TestSlotIntrospection:
    """Slot availability and timing queries."""

    def test_available_slots_initially_full(self, tmp_path):
        """Available slots should equal effective limit initially."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=20)
        assert scheduler.available_slots() == 20

    def test_available_slots_decreases_after_record(self, tmp_path):
        """Recording an agent launch should decrease available slots."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=5)
        scheduler.rate_limiter.record("agent_launch")
        assert scheduler.available_slots() == 4

    def test_next_slot_none_when_available(self, tmp_path):
        """next_slot_available_in should return None when slots are free."""
        scheduler = _make_scheduler(tmp_path)
        assert scheduler.next_slot_available_in() is None

    def test_next_slot_returns_seconds_when_exhausted(self, tmp_path):
        """When slots are exhausted, should return seconds until next free."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=1)
        scheduler.rate_limiter.record("agent_launch")
        wait = scheduler.next_slot_available_in()
        assert wait is not None
        # Should be close to 3600 seconds (1 hour window)
        assert 3500 < wait <= 3600


# ---------------------------------------------------------------------------
# WorkloadScheduler — phase awareness
# ---------------------------------------------------------------------------


class TestPhaseAwareness:
    """Scheduler should respect phase-adjusted rate limits."""

    def test_reconstruction_has_more_slots(self, tmp_path):
        """Reconstruction phase (1.5x) should have more agent slots."""
        scheduler = _make_scheduler(
            tmp_path, phase="reconstruction", max_agent_launches_per_hour=20
        )
        # 20 * 1.5 = 30
        assert scheduler.available_slots() == 30

    def test_production_has_fewer_slots(self, tmp_path):
        """Production phase (0.75x) should have fewer agent slots."""
        scheduler = _make_scheduler(
            tmp_path, phase="production", max_agent_launches_per_hour=20
        )
        # floor(20 * 0.75) = 15
        assert scheduler.available_slots() == 15


# ---------------------------------------------------------------------------
# WorkloadScheduler.format_plan
# ---------------------------------------------------------------------------


class TestFormatPlan:
    """format_plan should produce readable output."""

    def test_format_includes_dispatched_tasks(self, tmp_path):
        """Formatted plan should show dispatched task details."""
        scheduler = _make_scheduler(tmp_path)
        tasks = [_task("t1", priority=1, model="opus", cost=1.50)]
        plan = scheduler.plan(tasks)
        output = scheduler.format_plan(plan)
        assert "DISPATCH NOW" in output
        assert "t1" in output
        assert "opus" in output

    def test_format_includes_queued_tasks(self, tmp_path):
        """Formatted plan should show queued tasks when present."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=1)
        tasks = [_task("t1"), _task("t2")]
        plan = scheduler.plan(tasks)
        output = scheduler.format_plan(plan)
        assert "QUEUED" in output

    def test_format_shows_phase(self, tmp_path):
        """Formatted plan should include phase information."""
        scheduler = _make_scheduler(tmp_path, phase="production")
        plan = scheduler.plan([_task("t1")])
        output = scheduler.format_plan(plan)
        assert "production" in output

    def test_format_empty_plan(self, tmp_path):
        """Formatted empty plan should show 'No tasks'."""
        scheduler = _make_scheduler(tmp_path)
        plan = scheduler.plan([])
        output = scheduler.format_plan(plan)
        assert "No tasks" in output


# ---------------------------------------------------------------------------
# SchedulePlan — next_dispatch_at
# ---------------------------------------------------------------------------


class TestNextDispatchAt:
    """next_dispatch_at should be set correctly."""

    def test_no_queued_means_no_next_dispatch(self, tmp_path):
        """When all tasks dispatched, next_dispatch_at should be None."""
        scheduler = _make_scheduler(tmp_path)
        plan = scheduler.plan([_task("t1")])
        assert plan.next_dispatch_at is None

    def test_queued_tasks_have_next_dispatch(self, tmp_path):
        """When tasks are queued, next_dispatch_at should be set."""
        scheduler = _make_scheduler(tmp_path, max_agent_launches_per_hour=1)
        scheduler.rate_limiter.record("agent_launch")
        plan = scheduler.plan([_task("t1")])
        assert len(plan.queued) == 1
        assert plan.next_dispatch_at is not None
        assert plan.next_dispatch_at > time.time()


# ---------------------------------------------------------------------------
# WorkloadScheduler — constructor variants
# ---------------------------------------------------------------------------


class TestConstructorVariants:
    """Different constructor options should work correctly."""

    def test_default_constructor(self, tmp_path):
        """Default constructor should create a working scheduler."""
        scheduler = WorkloadScheduler(
            state_path=str(tmp_path / "state.json"),
            phase="stabilization",
        )
        assert scheduler.available_slots() == 20

    def test_custom_rate_limiter(self, tmp_path):
        """Passing a custom rate limiter should be used directly."""
        rl = RateLimiter(
            config=RateLimitConfig(max_agent_launches_per_hour=5),
            state_path=str(tmp_path / "state.json"),
            phase="stabilization",
        )
        scheduler = WorkloadScheduler(rate_limiter=rl)
        assert scheduler.available_slots() == 5
        assert scheduler.rate_limiter is rl
