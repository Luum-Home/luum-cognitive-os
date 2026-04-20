# SCOPE: both
"""Retry Scheduler -- Non-blocking deferred retry via scheduled tasks.

When the rate limiter blocks an agent launch, the orchestrator should not
``sleep N`` (which blocks the conversation). Instead, this module creates
a CronCreate-compatible schedule so the retry fires asynchronously.

Usage:
    from lib.retry_scheduler import RetryScheduler

    scheduler = RetryScheduler()
    spec = scheduler.schedule_retry("queue-abc-123", wait_seconds=120)
    # spec = {"task_id": "retry-queue-abc-123",
    #         "fire_at": "2026-03-28T15:02:00-03:00",
    #         "prompt": "...",
    #         "description": "..."}

    instruction = scheduler.format_retry_instruction("queue-abc-123", 120)

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


# Minimum wait before scheduling a retry (seconds).
# Shorter waits are better handled inline.
MIN_DEFERRED_WAIT_S = 60

# Maximum wait for a single retry schedule (seconds).
MAX_DEFERRED_WAIT_S = 7200  # 2 hours


def _sanitize_task_id(raw: str) -> str:
    """Sanitize a string into a valid kebab-case task ID."""
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", raw)
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    return sanitized[:64] or "retry-unknown"


class RetryScheduler:
    """Creates CronCreate-compatible schedules for deferred agent retries.

    Integrates with the RateLimitQueue to produce non-blocking retry plans
    when the rate limiter blocks an agent launch.
    """

    def schedule_retry(
        self,
        queue_id: str,
        wait_seconds: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Create a CronCreate-compatible schedule for retrying a queued agent.

        Args:
            queue_id: Identifier of the entry in RateLimitQueue.
            wait_seconds: Seconds to wait before retrying. Clamped to
                [MIN_DEFERRED_WAIT_S, MAX_DEFERRED_WAIT_S].
            now: Override current time (for testing).

        Returns:
            Dict with keys:
                task_id:     Kebab-case identifier for the scheduled task.
                fire_at:     ISO 8601 timestamp with timezone offset.
                prompt:      The prompt text for the scheduled task.
                description: Short one-line description for the task.
                recurring:   Always False (one-shot retry).
        """
        clamped = max(MIN_DEFERRED_WAIT_S, min(wait_seconds, MAX_DEFERRED_WAIT_S))
        if now is None:
            now = datetime.now(timezone.utc).astimezone()

        fire_at = now + timedelta(seconds=clamped)
        fire_at_iso = fire_at.isoformat()

        task_id = _sanitize_task_id("retry-%s" % queue_id)
        wait_min = math.ceil(clamped / 60)

        prompt = (
            "Rate limit cooldown expired. Retry queued agent tasks:\n"
            "1. Import RateLimitQueue from lib.rate_limiter\n"
            "2. Call queue.dequeue_ready() to get tasks ready for dispatch\n"
            "3. For each ready task, launch the agent as originally intended\n"
            "4. If no tasks are ready (cooldown not yet expired), report and exit\n"
            "\n"
            "Queue entry ID: %s\n"
            "Original wait: %d seconds (~%d minutes)\n"
        ) % (queue_id, clamped, wait_min)

        description = "Retry rate-limited agent (queue: %s, ~%dm)" % (
            queue_id[:30],
            wait_min,
        )

        return {
            "task_id": task_id,
            "fire_at": fire_at_iso,
            "prompt": prompt,
            "description": description,
            "recurring": False,
        }

    def format_retry_instruction(
        self,
        queue_id: str,
        wait_seconds: int,
    ) -> str:
        """Format a human-readable instruction for the orchestrator.

        This is the message the orchestrator should present to the user
        when a rate limit blocks an agent launch and a deferred retry
        is scheduled.

        Args:
            queue_id: Identifier of the entry in RateLimitQueue.
            wait_seconds: Seconds until the retry fires.

        Returns:
            Multi-line instruction string.
        """
        wait_min = math.ceil(wait_seconds / 60)
        spec = self.schedule_retry(queue_id, wait_seconds)

        lines = [
            "RATE_LIMIT_RETRY_SCHEDULED:",
            "  Queue ID: %s" % queue_id,
            "  Retry in: ~%d minutes" % wait_min,
            "  Fire at:  %s" % spec["fire_at"],
            "  Task ID:  %s" % spec["task_id"],
            "",
            "Action: Create a scheduled task with:",
            '  task_id: "%s"' % spec["task_id"],
            '  fire_at: "%s"' % spec["fire_at"],
            '  prompt: "%s"' % spec["prompt"].split("\n")[0],
            '  description: "%s"' % spec["description"],
            "",
            "The main conversation thread is free to continue.",
        ]
        return "\n".join(lines)

    def should_defer(self, wait_seconds: int) -> bool:
        """Return True if the wait is long enough to justify a deferred retry.

        Short waits (< MIN_DEFERRED_WAIT_S) are better handled inline.

        Args:
            wait_seconds: Estimated cooldown time in seconds.
        """
        return wait_seconds >= MIN_DEFERRED_WAIT_S
