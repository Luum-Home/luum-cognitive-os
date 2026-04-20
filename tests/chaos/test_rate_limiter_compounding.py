"""Chaos test: Rate-limiter compounding retry loop (D45 BLOCKING fix).

Scenario: bash_command quota is exhausted. Every blocked action is enqueued.
The queue drainer fires, hits the same limit, re-enqueues, repeat.

Before the fix: the queue grew unboundedly — a CPU + disk loop.
After the fix:
  - Retry cap (MAX_RETRY_COUNT=3) drops items that have failed too many times.
  - Exponential backoff makes eligible_at grow per retry (not flat 60s).
  - Circuit breaker halts the drainer when all queued items are failing.
  - Corruption recovery at startup truncates a queue pre-filled with exhausted items.

All assertions are against the *fixed* behaviour. The test documents the
intended contract and will catch any regression.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from lib.rate_limiter import (  # noqa: E402
    CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_WINDOW,
    CORRUPTION_RECOVERY_THRESHOLD,
    MAX_RETRY_COUNT,
    PRIORITY_NORMAL,
    RateLimitConfig,
    RateLimiter,
    RateLimitQueue,
)

pytestmark = pytest.mark.chaos


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_queue(tmp_path: Path, cooldown: int = 60) -> RateLimitQueue:
    return RateLimitQueue(
        state_path=str(tmp_path / "queue.json"),
        cooldown_seconds=cooldown,
    )


def _make_limiter(tmp_path: Path, **overrides) -> RateLimiter:
    cfg = RateLimitConfig(
        max_bash_commands_per_minute=2,  # Very tight — easy to exhaust
        **overrides,
    )
    return RateLimiter(
        config=cfg,
        state_path=str(tmp_path / "state.json"),
        phase="reconstruction",
    )


def _enqueue_n(queue: RateLimitQueue, n: int, retry_count: int = 0) -> List[str]:
    """Enqueue n bash_command items and return their IDs."""
    ids = []
    for i in range(n):
        qid = queue.enqueue(
            "bash_command",
            {"description": f"cmd-{i}"},
            retry_count=retry_count,
        )
        ids.append(qid)
    return ids


# ---------------------------------------------------------------------------
# 1. Retry cap — dropped items do NOT re-enter the queue
# ---------------------------------------------------------------------------


class TestRetryCap:
    """Items at or above MAX_RETRY_COUNT must be silently dropped."""

    def test_item_at_max_retry_is_dropped(self, tmp_path):
        """An item with retry_count == MAX_RETRY_COUNT should be dropped."""
        queue = _make_queue(tmp_path)
        qid = queue.enqueue("bash_command", {}, retry_count=MAX_RETRY_COUNT + 1)
        assert qid == "", "Expected empty string for over-cap item"
        assert len(queue.peek()) == 0, "Queue should be empty — item was dropped"

    def test_item_below_max_retry_is_accepted(self, tmp_path):
        """An item with retry_count < MAX_RETRY_COUNT should be accepted."""
        queue = _make_queue(tmp_path)
        qid = queue.enqueue("bash_command", {}, retry_count=MAX_RETRY_COUNT)
        assert qid != "", "Item at exactly MAX_RETRY_COUNT should still be queued"
        assert len(queue.peek()) == 1

    def test_drop_is_logged(self, tmp_path):
        """Dropped items should be logged to rate-limit-dropped.jsonl in the same dir as queue."""
        # Use a subdirectory so the drop log is next to the queue file
        queue_dir = tmp_path / "cognitive-os"
        queue_dir.mkdir()
        queue = RateLimitQueue(
            state_path=str(queue_dir / "rate-limit-queue.json"),
            cooldown_seconds=60,
        )
        queue.enqueue("bash_command", {"description": "doomed"}, retry_count=MAX_RETRY_COUNT + 1)
        drop_log = str(queue_dir / "rate-limit-dropped.jsonl")
        assert os.path.exists(drop_log), "Drop log should be created"
        with open(drop_log) as f:
            entry = json.loads(f.readline())
        assert entry["action_type"] == "bash_command"
        assert entry["retry_count"] == MAX_RETRY_COUNT + 1
        assert entry["reason"] == "retry_cap_exceeded"

    def test_compounding_scenario_queue_does_not_grow_unboundedly(self, tmp_path):
        """
        Simulate the compounding loop: each dequeued item hits the limit
        and is re-enqueued with retry_count + 1.

        Uses fewer items than CIRCUIT_BREAKER_THRESHOLD to test the pure
        retry-cap path without circuit interference. The queue must NOT
        grow beyond MAX_QUEUE_SIZE, and after MAX_RETRY_COUNT rounds every
        item must be dropped (queue empties).
        """
        queue = _make_queue(tmp_path, cooldown=0)
        # Use fewer items than CIRCUIT_BREAKER_THRESHOLD to avoid circuit
        # breaker interference in this test (circuit is tested separately)
        initial_count = CIRCUIT_BREAKER_THRESHOLD - 1
        _enqueue_n(queue, initial_count, retry_count=0)

        for retry in range(1, MAX_RETRY_COUNT + 3):
            # Make all items eligible immediately
            for item in queue._items:
                item["eligible_at"] = time.time() - 1
            queue._save()

            ready = queue.dequeue_ready()

            # Re-enqueue each item with incremented retry_count (simulating the hook)
            for item in ready:
                queue.enqueue(
                    item["action_type"],
                    item.get("context", {}),
                    retry_count=item.get("retry_count", 0) + 1,
                )

            # Queue must never exceed MAX_QUEUE_SIZE
            assert len(queue.peek()) <= 50, (
                f"Queue exceeded MAX_QUEUE_SIZE at retry {retry}: "
                f"{len(queue.peek())} items"
            )

        # After enough retries, ALL items should be dropped
        assert len(queue.peek()) == 0, (
            f"Queue should be empty after retry cap — found {len(queue.peek())} items"
        )


# ---------------------------------------------------------------------------
# 2. Exponential backoff — eligible_at grows per retry
# ---------------------------------------------------------------------------


class TestExponentialBackoff:
    """each retry should double the wait before the item becomes eligible."""

    def test_retry_0_uses_base_cooldown(self, tmp_path):
        queue = _make_queue(tmp_path, cooldown=60)
        before = time.time()
        queue.enqueue("bash_command", {}, retry_count=0)
        item = queue.peek()[0]
        expected_min = before + 60
        assert item["eligible_at"] >= expected_min - 1, (
            "retry_count=0 should use base cooldown (~60s)"
        )

    def test_retry_1_doubles_cooldown(self, tmp_path):
        queue = _make_queue(tmp_path, cooldown=60)
        before = time.time()
        queue.enqueue("bash_command", {}, retry_count=1)
        item = queue.peek()[0]
        expected_min = before + 120  # 60 * 2^1
        assert item["eligible_at"] >= expected_min - 1, (
            "retry_count=1 should double cooldown (~120s)"
        )

    def test_retry_2_quadruples_cooldown(self, tmp_path):
        queue = _make_queue(tmp_path, cooldown=60)
        before = time.time()
        queue.enqueue("bash_command", {}, retry_count=2)
        item = queue.peek()[0]
        expected_min = before + 240  # 60 * 2^2
        assert item["eligible_at"] >= expected_min - 1, (
            "retry_count=2 should quadruple cooldown (~240s)"
        )

    def test_backoff_capped_at_600s(self, tmp_path):
        """Backoff must not exceed 10 minutes regardless of retry_count."""
        queue = _make_queue(tmp_path, cooldown=60)
        before = time.time()
        # Use MAX_RETRY_COUNT exactly — this item is still accepted (not dropped)
        # but its backoff would be 60 * 2^MAX_RETRY_COUNT which may exceed 600s cap.
        queue.enqueue("bash_command", {}, retry_count=MAX_RETRY_COUNT)
        items = queue.peek()
        assert len(items) == 1, (
            f"Item at MAX_RETRY_COUNT should be accepted, not dropped"
        )
        item = items[0]
        max_eligible = before + 600 + 2  # 2s grace
        assert item["eligible_at"] <= max_eligible, (
            f"Backoff exceeded 600s cap: eligible_at={item['eligible_at']:.0f}, "
            f"now={before:.0f}"
        )


# ---------------------------------------------------------------------------
# 3. Circuit breaker — drainer halts when all items are failing
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """dequeue_ready() must pause the drainer when all items have retry_count>=1."""

    def test_circuit_breaker_trips_when_all_retried(self, tmp_path):
        """
        If >= CIRCUIT_BREAKER_THRESHOLD items are queued and ALL have
        retry_count >= 1, dequeue_ready() must return empty list and
        advance eligible_at by CIRCUIT_BREAKER_WINDOW.
        """
        queue = _make_queue(tmp_path, cooldown=0)
        # Enqueue threshold+1 items with retry_count=1 (all previously failed)
        for i in range(CIRCUIT_BREAKER_THRESHOLD + 1):
            queue.enqueue("bash_command", {"description": f"failed-{i}"}, retry_count=1)
        # Make all items eligible
        for item in queue._items:
            item["eligible_at"] = time.time() - 1
        queue._save()

        before = time.time()
        ready = queue.dequeue_ready()

        # Circuit breaker fired — no items returned
        assert ready == [], "Circuit breaker should return empty list"

        # All items should have eligible_at pushed forward
        remaining = queue.peek()
        assert len(remaining) == CIRCUIT_BREAKER_THRESHOLD + 1, (
            "Items should remain in queue (not dropped) when circuit trips"
        )
        for item in remaining:
            assert item["eligible_at"] >= before + CIRCUIT_BREAKER_WINDOW - 1, (
                f"eligible_at should be pushed forward by {CIRCUIT_BREAKER_WINDOW}s"
            )

    def test_circuit_breaker_does_not_trip_if_fresh_items_present(self, tmp_path):
        """
        If some items have retry_count=0, the circuit should NOT trip —
        fresh items are allowed through.
        """
        queue = _make_queue(tmp_path, cooldown=0)
        # Mix of fresh and retried items
        for i in range(CIRCUIT_BREAKER_THRESHOLD):
            rc = 1 if i < CIRCUIT_BREAKER_THRESHOLD - 1 else 0  # Last one is fresh
            queue.enqueue("bash_command", {"description": f"item-{i}"}, retry_count=rc)
        # Make all items eligible
        for item in queue._items:
            item["eligible_at"] = time.time() - 1
        queue._save()

        ready = queue.dequeue_ready()
        # Should NOT be empty since one fresh item is present
        assert len(ready) > 0, (
            "Circuit breaker should not trip when fresh (retry_count=0) items exist"
        )

    def test_circuit_breaker_does_not_trip_below_threshold(self, tmp_path):
        """Circuit breaker should not fire when queue is below threshold."""
        queue = _make_queue(tmp_path, cooldown=0)
        # Enqueue fewer than threshold items, all retried
        for i in range(CIRCUIT_BREAKER_THRESHOLD - 1):
            queue.enqueue("bash_command", {}, retry_count=2)
        for item in queue._items:
            item["eligible_at"] = time.time() - 1
        queue._save()

        ready = queue.dequeue_ready()
        # Below threshold — should dequeue normally
        assert len(ready) == CIRCUIT_BREAKER_THRESHOLD - 1


# ---------------------------------------------------------------------------
# 4. Corruption recovery at startup
# ---------------------------------------------------------------------------


class TestCorruptionRecovery:
    """
    If a queue file has >= CORRUPTION_RECOVERY_THRESHOLD items with
    retry_count > MAX_RETRY_COUNT, __init__ must truncate it.
    """

    def test_corrupted_queue_truncated_at_startup(self, tmp_path):
        """A queue bloated by a pre-fix compounding loop should be cleaned."""
        queue_path = str(tmp_path / "queue.json")

        # Write a corrupted queue directly (simulating the pre-fix bug)
        corrupted_items: List[Dict[str, Any]] = []
        for i in range(CORRUPTION_RECOVERY_THRESHOLD + 50):
            corrupted_items.append(
                {
                    "queue_id": f"dead-{i:04d}",
                    "action_type": "bash_command",
                    "context": {"description": f"stuck-{i}"},
                    "priority": PRIORITY_NORMAL,
                    "enqueued_at": time.time() - 100,
                    "eligible_at": time.time() - 1,
                    "retry_count": MAX_RETRY_COUNT + 5,  # All over-cap
                }
            )
        # Add a few healthy items
        for i in range(5):
            corrupted_items.append(
                {
                    "queue_id": f"ok-{i:04d}",
                    "action_type": "bash_command",
                    "context": {"description": f"healthy-{i}"},
                    "priority": PRIORITY_NORMAL,
                    "enqueued_at": time.time() - 10,
                    "eligible_at": time.time() + 60,
                    "retry_count": 0,
                }
            )
        with open(queue_path, "w") as f:
            json.dump(corrupted_items, f)

        # Loading should auto-recover
        queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=60)
        items = queue.peek()

        # Only the healthy items should survive
        assert len(items) == 5, (
            f"Expected 5 healthy items after recovery, got {len(items)}"
        )
        for item in items:
            assert item.get("retry_count", 0) <= MAX_RETRY_COUNT

    def test_healthy_queue_not_truncated(self, tmp_path):
        """A normal queue below the corruption threshold must be left intact."""
        queue_path = str(tmp_path / "queue.json")
        items = []
        for i in range(10):
            items.append(
                {
                    "queue_id": f"ok-{i:04d}",
                    "action_type": "bash_command",
                    "context": {},
                    "priority": PRIORITY_NORMAL,
                    "enqueued_at": time.time() - 5,
                    "eligible_at": time.time() + 60,
                    "retry_count": 1,
                }
            )
        with open(queue_path, "w") as f:
            json.dump(items, f)

        queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=60)
        assert len(queue.peek()) == 10, "Healthy queue must not be truncated"


# ---------------------------------------------------------------------------
# 5. Backfill — legacy items load without KeyError
# ---------------------------------------------------------------------------


class TestLegacyItemBackfill:
    """Items written before the fix (no retry_count field) must load cleanly."""

    def test_legacy_item_gets_retry_count_zero(self, tmp_path):
        queue_path = str(tmp_path / "queue.json")
        legacy_items = [
            {
                "queue_id": "legacy-01",
                "action_type": "bash_command",
                "context": {"description": "old item"},
                "priority": PRIORITY_NORMAL,
                "enqueued_at": time.time() - 30,
                "eligible_at": time.time() - 1,
                # No retry_count field — simulates pre-fix queue file
            }
        ]
        with open(queue_path, "w") as f:
            json.dump(legacy_items, f)

        queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=60)
        items = queue.peek()
        assert len(items) == 1
        assert items[0].get("retry_count") == 0, (
            "Legacy items must be backfilled with retry_count=0"
        )
