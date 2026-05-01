"""Unit tests for RateLimitQueue and new RateLimiter methods.

Tests the queue-based graceful rate limit handling: enqueue, dequeue,
priority ordering, persistence, cancellation, batch reduction suggestions,
and the format_limit_status dashboard.
"""

import time

import pytest

from lib.rate_limiter import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    RateLimitConfig,
    RateLimiter,
    RateLimitQueue,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_queue(tmp_path, cooldown: int = 60) -> RateLimitQueue:
    """Create a RateLimitQueue with a temp state file."""
    return RateLimitQueue(
        state_path=str(tmp_path / "queue.json"),
        cooldown_seconds=cooldown,
    )


def _make_limiter(tmp_path, phase: str = "stabilization", **config_overrides):
    """Create a RateLimiter with a temp state file and optional config."""
    cfg = RateLimitConfig(**config_overrides)
    return RateLimiter(
        config=cfg,
        state_path=str(tmp_path / "state.json"),
        phase=phase,
    )


# ---------------------------------------------------------------------------
# enqueue
# ---------------------------------------------------------------------------


class TestEnqueue:
    """Enqueue should store actions and return a queue ID."""

    def test_enqueue_stores_action(self, tmp_path):
        """Enqueued action should be visible in peek."""
        queue = _make_queue(tmp_path)
        queue_id = queue.enqueue("agent_launch", {"description": "test task"})
        assert queue_id  # non-empty string
        items = queue.peek()
        assert len(items) == 1
        assert items[0]["action_type"] == "agent_launch"
        assert items[0]["context"]["description"] == "test task"
        assert items[0]["queue_id"] == queue_id

    def test_enqueue_multiple_items(self, tmp_path):
        """Multiple enqueues should all be stored."""
        queue = _make_queue(tmp_path)
        queue.enqueue("agent_launch", {"description": "task 1"})
        queue.enqueue("agent_launch", {"description": "task 2"})
        queue.enqueue("bash_command", {"description": "task 3"})
        items = queue.peek()
        assert len(items) == 3

    def test_enqueue_respects_max_size(self, tmp_path):
        """Queue should not exceed MAX_QUEUE_SIZE (50)."""
        queue = _make_queue(tmp_path)
        for i in range(55):
            queue.enqueue("agent_launch", {"description": f"task {i}"})
        items = queue.peek()
        assert len(items) <= 50

    def test_enqueue_returns_unique_ids(self, tmp_path):
        """Each enqueue should return a unique ID."""
        queue = _make_queue(tmp_path)
        ids = set()
        for _ in range(10):
            ids.add(queue.enqueue("agent_launch"))
        assert len(ids) == 10


# ---------------------------------------------------------------------------
# dequeue_ready
# ---------------------------------------------------------------------------


class TestDequeueReady:
    """Dequeue should return items whose cooldown has expired."""

    def test_dequeue_after_cooldown(self, tmp_path):
        """Items should be dequeued after cooldown expires."""
        queue = _make_queue(tmp_path, cooldown=1)
        queue.enqueue("agent_launch", {"description": "task A"})
        # Manually set eligible_at to past
        queue._items[0]["eligible_at"] = time.time() - 10
        queue._save()

        ready = queue.dequeue_ready()
        assert len(ready) == 1
        assert ready[0]["context"]["description"] == "task A"
        # Item should be removed from queue
        assert len(queue.peek()) == 0

    def test_dequeue_before_cooldown(self, tmp_path):
        """Items should stay queued before cooldown expires."""
        queue = _make_queue(tmp_path, cooldown=3600)
        queue.enqueue("agent_launch", {"description": "task B"})

        ready = queue.dequeue_ready()
        assert len(ready) == 0
        assert len(queue.peek()) == 1

    def test_dequeue_partial(self, tmp_path):
        """Only eligible items should be dequeued, others remain."""
        queue = _make_queue(tmp_path, cooldown=3600)
        queue.enqueue("agent_launch", {"description": "ready"})
        queue.enqueue("agent_launch", {"description": "not ready"})

        # Make first item eligible
        queue._items[0]["eligible_at"] = time.time() - 10
        queue._save()

        ready = queue.dequeue_ready()
        assert len(ready) == 1
        assert ready[0]["context"]["description"] == "ready"
        remaining = queue.peek()
        assert len(remaining) == 1
        assert remaining[0]["context"]["description"] == "not ready"

    def test_empty_queue(self, tmp_path):
        """Dequeue on empty queue should return empty list."""
        queue = _make_queue(tmp_path)
        ready = queue.dequeue_ready()
        assert ready == []


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


class TestCancel:
    """Cancel should remove the specified item."""

    def test_cancel_removes_item(self, tmp_path):
        """Cancelled items should not appear in peek or dequeue."""
        queue = _make_queue(tmp_path)
        qid = queue.enqueue("agent_launch", {"description": "to cancel"})
        queue.enqueue("agent_launch", {"description": "to keep"})

        result = queue.cancel(qid)
        assert result is True
        items = queue.peek()
        assert len(items) == 1
        assert items[0]["context"]["description"] == "to keep"

    def test_cancel_nonexistent_returns_false(self, tmp_path):
        """Cancelling a nonexistent ID should return False."""
        queue = _make_queue(tmp_path)
        queue.enqueue("agent_launch")
        result = queue.cancel("nonexistent-id")
        assert result is False
        assert len(queue.peek()) == 1


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


class TestOrdering:
    """Queue should respect priority and FIFO ordering."""

    def test_queue_fifo_ordering(self, tmp_path):
        """Items with same priority should dequeue in FIFO order."""
        queue = _make_queue(tmp_path, cooldown=0)
        queue.enqueue("agent_launch", {"description": "first"})
        # Ensure different enqueue times
        queue._items[-1]["enqueued_at"] = time.time() - 3
        queue._items[-1]["eligible_at"] = time.time() - 3
        queue.enqueue("agent_launch", {"description": "second"})
        queue._items[-1]["enqueued_at"] = time.time() - 2
        queue._items[-1]["eligible_at"] = time.time() - 2
        queue.enqueue("agent_launch", {"description": "third"})
        queue._items[-1]["enqueued_at"] = time.time() - 1
        queue._items[-1]["eligible_at"] = time.time() - 1
        queue._save()

        ready = queue.dequeue_ready()
        assert len(ready) == 3
        assert ready[0]["context"]["description"] == "first"
        assert ready[1]["context"]["description"] == "second"
        assert ready[2]["context"]["description"] == "third"

    def test_priority_ordering(self, tmp_path):
        """High priority items should dequeue before normal/low."""
        queue = _make_queue(tmp_path, cooldown=0)

        queue.enqueue("agent_launch", {"description": "low"}, priority=PRIORITY_LOW)
        queue._items[-1]["eligible_at"] = time.time() - 1
        queue.enqueue(
            "agent_launch", {"description": "high"}, priority=PRIORITY_HIGH
        )
        queue._items[-1]["eligible_at"] = time.time() - 1
        queue.enqueue(
            "agent_launch", {"description": "normal"}, priority=PRIORITY_NORMAL
        )
        queue._items[-1]["eligible_at"] = time.time() - 1
        queue._save()

        ready = queue.dequeue_ready()
        assert len(ready) == 3
        assert ready[0]["context"]["description"] == "high"
        assert ready[1]["context"]["description"] == "normal"
        assert ready[2]["context"]["description"] == "low"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    """Queue state should survive across instances."""

    def test_queue_persistence(self, tmp_path):
        """Queue should survive across RateLimitQueue instances."""
        path = str(tmp_path / "queue.json")
        q1 = RateLimitQueue(state_path=path, cooldown_seconds=60)
        q1.enqueue("agent_launch", {"description": "persisted task"})

        # New instance loading from same path
        q2 = RateLimitQueue(state_path=path, cooldown_seconds=60)
        items = q2.peek()
        assert len(items) == 1
        assert items[0]["context"]["description"] == "persisted task"

    def test_load_from_nonexistent_creates_empty(self, tmp_path):
        """Loading from nonexistent file should create empty queue."""
        queue = RateLimitQueue(
            state_path=str(tmp_path / "nope.json"),
            cooldown_seconds=60,
        )
        assert queue.peek() == []

    def test_load_from_corrupted_creates_empty(self, tmp_path):
        """Loading from corrupted file should create empty queue."""
        path = tmp_path / "queue.json"
        path.write_text("not valid json {{{")
        queue = RateLimitQueue(state_path=str(path), cooldown_seconds=60)
        assert queue.peek() == []


# ---------------------------------------------------------------------------
# format_queue_status
# ---------------------------------------------------------------------------


class TestFormatQueueStatus:
    """format_queue_status should produce readable output."""

    def test_format_status_empty(self, tmp_path):
        """Empty queue should report 'empty'."""
        queue = _make_queue(tmp_path)
        output = queue.format_queue_status()
        assert "empty" in output

    def test_format_status_with_items(self, tmp_path):
        """Status should show item count and descriptions."""
        queue = _make_queue(tmp_path, cooldown=120)
        queue.enqueue("agent_launch", {"description": "run tests"})
        queue.enqueue("agent_launch", {"description": "deploy service"})
        output = queue.format_queue_status()
        assert "2 item(s)" in output
        assert "run tests" in output
        assert "deploy service" in output
        assert "agent_launch" in output

    def test_format_status_shows_ready(self, tmp_path):
        """Items past cooldown should show READY."""
        queue = _make_queue(tmp_path, cooldown=0)
        queue.enqueue("agent_launch", {"description": "ready task"})
        queue._items[0]["eligible_at"] = time.time() - 10
        queue._save()
        output = queue.format_queue_status()
        assert "READY" in output


# ---------------------------------------------------------------------------
# suggest_reduction
# ---------------------------------------------------------------------------


class TestSuggestReduction:
    """suggest_reduction should provide batch advice."""

    def test_suggest_reduction_with_many_queued(self, tmp_path):
        """Should suggest batching when >3 items queued."""
        rl = _make_limiter(tmp_path)
        suggestion = rl.suggest_reduction(6)
        assert "batching" in suggestion.lower() or "batch" in suggestion.lower()
        assert "3" in suggestion  # suggests batching to ~half

    def test_suggest_reduction_with_few_queued(self, tmp_path):
        """Should return empty string when <=2 items queued."""
        rl = _make_limiter(tmp_path)
        suggestion = rl.suggest_reduction(2)
        assert suggestion == ""

    def test_suggest_reduction_zero(self, tmp_path):
        """Should return empty string for zero queued items."""
        rl = _make_limiter(tmp_path)
        assert rl.suggest_reduction(0) == ""

    def test_suggest_reduction_includes_rate_info(self, tmp_path):
        """Suggestion should include current rate info."""
        rl = _make_limiter(tmp_path)
        suggestion = rl.suggest_reduction(5)
        assert "rate" in suggestion.lower() or "/hr" in suggestion

    def test_suggest_reduction_cost_pressure(self, tmp_path):
        """Should suggest haiku when cost is nearly exhausted."""
        rl = _make_limiter(tmp_path, max_cost_per_hour_usd=1.0)
        rl.record("tool_call", cost_usd=0.5)
        suggestion = rl.suggest_reduction(5)
        assert "haiku" in suggestion.lower()


# ---------------------------------------------------------------------------
# format_limit_status
# ---------------------------------------------------------------------------


class TestFormatLimitStatus:
    """format_limit_status should produce a dashboard-style view."""

    def test_limit_status_shows_phase(self, tmp_path):
        """Status should include the current phase and modifier."""
        rl = _make_limiter(tmp_path, phase="reconstruction")
        output = rl.format_limit_status()
        assert "reconstruction" in output
        assert "1.5x" in output

    def test_limit_status_shows_percentages(self, tmp_path):
        """Status should show usage percentages."""
        rl = _make_limiter(
            tmp_path, phase="stabilization", max_agent_launches_per_hour=10
        )
        for _ in range(5):
            rl.record("agent_launch")
        output = rl.format_limit_status()
        assert "33%" in output

    def test_limit_status_shows_all_types(self, tmp_path):
        """Status should include all action types and cost."""
        rl = _make_limiter(tmp_path)
        output = rl.format_limit_status()
        assert "Agent launches" in output
        assert "Bash commands" in output
        assert "File writes" in output
        assert "Tool calls" in output
        assert "Cost" in output

    def test_limit_status_with_queue(self, tmp_path):
        """Status should include queue info when queue is provided."""
        rl = _make_limiter(tmp_path)
        queue = _make_queue(tmp_path, cooldown=120)
        queue.enqueue("agent_launch", {"description": "queued task"})

        output = rl.format_limit_status(queue=queue)
        assert "Queue:" in output
        assert "1 item" in output

    def test_limit_status_empty_queue(self, tmp_path):
        """Status should show 'empty' when queue has no items."""
        rl = _make_limiter(tmp_path)
        queue = _make_queue(tmp_path)
        output = rl.format_limit_status(queue=queue)
        assert "empty" in output

    def test_limit_status_without_queue(self, tmp_path):
        """Status should work fine without queue parameter."""
        rl = _make_limiter(tmp_path)
        output = rl.format_limit_status()
        assert "Queue" not in output


# ---------------------------------------------------------------------------
# Auto-prune old queue entries
# ---------------------------------------------------------------------------


class TestQueuePrune:
    """Old entries should be automatically pruned."""

    def test_prune_removes_old_entries(self, tmp_path):
        """Entries older than MAX_QUEUE_AGE_SECONDS should be pruned."""
        queue = _make_queue(tmp_path)
        queue.enqueue("agent_launch", {"description": "old task"})
        # Set enqueued_at to 3 hours ago (beyond 2hr max age)
        queue._items[0]["enqueued_at"] = time.time() - 10800
        queue._save()

        # Prune happens on peek/dequeue
        items = queue.peek()
        assert len(items) == 0

    def test_prune_keeps_recent_entries(self, tmp_path):
        """Recent entries should survive pruning."""
        queue = _make_queue(tmp_path)
        queue.enqueue("agent_launch", {"description": "recent task"})
        items = queue.peek()
        assert len(items) == 1
