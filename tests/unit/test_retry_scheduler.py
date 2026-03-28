"""Unit tests for lib/retry_scheduler.py -- Non-blocking deferred retry.

Run with: pytest tests/unit/test_retry_scheduler.py -v
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from lib.retry_scheduler import (
    RetryScheduler,
    MIN_DEFERRED_WAIT_S,
    MAX_DEFERRED_WAIT_S,
    _sanitize_task_id,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scheduler():
    return RetryScheduler()


@pytest.fixture
def fixed_now():
    """A fixed datetime for deterministic tests."""
    return datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# schedule_retry
# ---------------------------------------------------------------------------


class TestScheduleRetry:
    """Tests for RetryScheduler.schedule_retry()."""

    def test_returns_required_keys(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-123", 120, now=fixed_now)
        assert "task_id" in result
        assert "fire_at" in result
        assert "prompt" in result
        assert "description" in result
        assert "recurring" in result

    def test_recurring_is_always_false(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-123", 120, now=fixed_now)
        assert result["recurring"] is False

    def test_fire_at_is_iso8601(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-123", 120, now=fixed_now)
        # Should parse without error
        parsed = datetime.fromisoformat(result["fire_at"])
        assert parsed.tzinfo is not None

    def test_fire_at_offset_matches_wait(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-abc", 180, now=fixed_now)
        fire_at = datetime.fromisoformat(result["fire_at"])
        expected = fixed_now + timedelta(seconds=180)
        # Allow 1-second tolerance for rounding
        assert abs((fire_at - expected).total_seconds()) < 1

    def test_clamps_minimum_wait(self, scheduler, fixed_now):
        """Wait below MIN_DEFERRED_WAIT_S is clamped up."""
        result = scheduler.schedule_retry("q-short", 10, now=fixed_now)
        fire_at = datetime.fromisoformat(result["fire_at"])
        expected = fixed_now + timedelta(seconds=MIN_DEFERRED_WAIT_S)
        assert abs((fire_at - expected).total_seconds()) < 1

    def test_clamps_maximum_wait(self, scheduler, fixed_now):
        """Wait above MAX_DEFERRED_WAIT_S is clamped down."""
        result = scheduler.schedule_retry("q-long", 99999, now=fixed_now)
        fire_at = datetime.fromisoformat(result["fire_at"])
        expected = fixed_now + timedelta(seconds=MAX_DEFERRED_WAIT_S)
        assert abs((fire_at - expected).total_seconds()) < 1

    def test_task_id_contains_queue_id(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("my-queue-42", 120, now=fixed_now)
        assert "my-queue-42" in result["task_id"]

    def test_task_id_is_kebab_case(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("some_weird.id/here", 120, now=fixed_now)
        task_id = result["task_id"]
        # Only alphanumeric and hyphens
        assert all(c.isalnum() or c == "-" for c in task_id)

    def test_prompt_includes_queue_id(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-xyz-789", 120, now=fixed_now)
        assert "q-xyz-789" in result["prompt"]

    def test_prompt_includes_dequeue_instruction(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-1", 120, now=fixed_now)
        assert "dequeue_ready" in result["prompt"]

    def test_description_includes_wait_minutes(self, scheduler, fixed_now):
        result = scheduler.schedule_retry("q-1", 300, now=fixed_now)
        # 300s = 5min
        assert "5m" in result["description"]


# ---------------------------------------------------------------------------
# format_retry_instruction
# ---------------------------------------------------------------------------


class TestFormatRetryInstruction:
    """Tests for RetryScheduler.format_retry_instruction()."""

    def test_includes_queue_id(self, scheduler):
        text = scheduler.format_retry_instruction("q-abc-123", 120)
        assert "q-abc-123" in text

    def test_includes_rate_limit_marker(self, scheduler):
        text = scheduler.format_retry_instruction("q-1", 120)
        assert "RATE_LIMIT_RETRY_SCHEDULED" in text

    def test_includes_fire_at(self, scheduler):
        text = scheduler.format_retry_instruction("q-1", 180)
        assert "Fire at:" in text

    def test_includes_task_id(self, scheduler):
        text = scheduler.format_retry_instruction("q-1", 120)
        assert "Task ID:" in text

    def test_mentions_free_thread(self, scheduler):
        text = scheduler.format_retry_instruction("q-1", 120)
        assert "free to continue" in text


# ---------------------------------------------------------------------------
# should_defer
# ---------------------------------------------------------------------------


class TestShouldDefer:
    """Tests for RetryScheduler.should_defer()."""

    def test_short_wait_not_deferred(self, scheduler):
        assert scheduler.should_defer(30) is False

    def test_exact_minimum_is_deferred(self, scheduler):
        assert scheduler.should_defer(MIN_DEFERRED_WAIT_S) is True

    def test_long_wait_is_deferred(self, scheduler):
        assert scheduler.should_defer(600) is True


# ---------------------------------------------------------------------------
# _sanitize_task_id
# ---------------------------------------------------------------------------


class TestSanitizeTaskId:
    """Tests for _sanitize_task_id helper."""

    def test_simple_id(self):
        assert _sanitize_task_id("retry-q-123") == "retry-q-123"

    def test_underscores_replaced(self):
        assert "_" not in _sanitize_task_id("retry_q_123")

    def test_dots_replaced(self):
        assert "." not in _sanitize_task_id("retry.q.123")

    def test_slashes_replaced(self):
        assert "/" not in _sanitize_task_id("retry/q/123")

    def test_empty_string_returns_fallback(self):
        assert _sanitize_task_id("") == "retry-unknown"

    def test_truncated_to_64_chars(self):
        long_id = "a" * 100
        assert len(_sanitize_task_id(long_id)) <= 64


# ---------------------------------------------------------------------------
# Integration: WorkloadScheduler + RetryScheduler coherence
# ---------------------------------------------------------------------------


class TestWorkloadSchedulerIntegration:
    """Verify RetryScheduler produces schedules coherent with WorkloadScheduler."""

    def test_schedule_uses_positive_wait(self, scheduler, fixed_now):
        """WorkloadScheduler.next_slot_available_in() returns positive seconds;
        RetryScheduler must handle positive values correctly."""
        # Simulated wait from WorkloadScheduler
        wait_from_scheduler = 45.7  # seconds (float)
        result = scheduler.schedule_retry("wl-task-1", int(wait_from_scheduler), now=fixed_now)
        # Should clamp to minimum since 45 < 60
        fire_at = datetime.fromisoformat(result["fire_at"])
        expected = fixed_now + timedelta(seconds=MIN_DEFERRED_WAIT_S)
        assert abs((fire_at - expected).total_seconds()) < 1

    def test_schedule_handles_typical_cooldown(self, scheduler, fixed_now):
        """Typical rate limit cooldown of 60 seconds."""
        result = scheduler.schedule_retry("wl-task-2", 60, now=fixed_now)
        fire_at = datetime.fromisoformat(result["fire_at"])
        expected = fixed_now + timedelta(seconds=60)
        assert abs((fire_at - expected).total_seconds()) < 1
        assert result["recurring"] is False
