<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Non-Blocking Retry Protocol

## Purpose

When the rate limiter blocks an agent launch, the orchestrator must not use `sleep N` which blocks the conversation. Instead, it schedules a deferred retry using CronCreate (scheduled tasks) so the main thread remains free.

## Problem

The current rate limiter blocks agent launches with exit code 2 and a cooldown message. The orchestrator's natural response is `sleep N && retry`, which:
1. Blocks the conversation for N seconds (user cannot interact)
2. Wastes a tool call on a sleep
3. Prevents the orchestrator from doing other useful work

## Solution: CronCreate-Based Deferred Retry

```
Rate limit BLOCKS agent launch
    |
    v
Orchestrator enqueues task in RateLimitQueue
    |
    v
RetryScheduler.schedule_retry(queue_id, wait_seconds)
    |
    v
CronCreate fires N minutes later with prompt:
  "Retry queued agents: dequeue from RateLimitQueue and launch"
    |
    v
Main conversation thread is FREE
    |
    v
CronCreate fires -> orchestrator dequeues and launches
```

## When to Use

| Condition | Action |
|-----------|--------|
| Rate limit blocks with cooldown < 60s | Wait inline (short enough) |
| Rate limit blocks with cooldown 60s-300s | Schedule retry via CronCreate |
| Rate limit blocks with cooldown > 300s | Schedule retry + inform user |
| Cost limit blocks | Inform user, do NOT auto-retry |

## Orchestrator Behavior

When the rate limiter returns `RATE_LIMIT_QUEUED`:

1. Read the `queue_id` and `wait_seconds` from the block message
2. Call `RetryScheduler.schedule_retry(queue_id, wait_seconds)`
3. Use the returned cron/fireAt to create a scheduled task via CronCreate
4. Inform the user: "Agent launch rate-limited. Retry scheduled in N minutes."
5. Continue with other work or ask the user for next steps

## Integration

| Primitive | Role |
|-----------|------|
| `lib/rate_limiter.py` | RateLimitQueue enqueues blocked actions |
| `lib/retry_scheduler.py` | Formats CronCreate-compatible retry schedule |
| `lib/workload_scheduler.py` | `next_slot_available_in()` estimates wait time |
| CronCreate (scheduled tasks) | Fires the deferred retry |

## Library

`lib/retry_scheduler.py` provides:

| Function | Description |
|----------|-------------|
| `RetryScheduler.schedule_retry(queue_id, wait_seconds)` | Returns CronCreate-compatible dict with fireAt and prompt |
| `RetryScheduler.format_retry_instruction(queue_id, wait_seconds)` | Human-readable instruction for the orchestrator |

## Configuration

No additional configuration needed. The retry scheduler reads rate limit config from `cognitive-os.yaml` via the existing `RateLimiter`.

## Contextual Trigger

This rule is loaded when: rate limit, blocked, retry, cooldown, non-blocking, deferred retry.
