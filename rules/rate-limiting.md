<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Rate Limiting Protocol

## Purpose

Prevents token flooding, excessive tool usage, runaway shell loops, and operator starvation by enforcing token-bucket flow control on hook actions.

The rate limiter is active by default for Bash, Agent, Edit, and Write tool activity through `hooks/rate-limiter.sh`.

## Default Refill Limits

| Action Type | Refill Limit | Window | Rationale |
|-------------|--------------|--------|-----------|
| `tool_call` | 30 per minute | 60s | General tool flood prevention |
| `agent_launch` | 20 per hour | 3600s | Prevents context exhaustion from agent spawning |
| `bash_command` | 15 per minute | 60s | Prevents runaway shell execution loops |
| `file_write` | 10 per minute | 60s | Prevents rapid file thrashing |
| Cost | $5.00 per hour | 3600s | Budget safety net independent of resource-governance |

## Token Bucket Behavior

- Each action type has a persisted token bucket.
- Phase modifiers apply to the refill limit.
- Bucket capacity defaults to `ceil(effective_limit * burst_multiplier)`.
- `burst_multiplier` defaults to `1.5` so short legitimate bursts are allowed.
- Sustained pressure drains the bucket and then blocks.
- Blocked work is queued for retry instead of being dropped.

## Soft Warning

When an action bucket or cost cap crosses `warning_threshold` (`0.80` by default), the hook emits:

```text
RATE_LIMIT_WARNING: <action> bucket at <pct>% (...)
```

Warnings do not block; they are an early signal to batch, pause, or reduce fan-out.

## Priority Reserve

`operator_reserve_ratio` defaults to `0.20`. Normal and orchestrator lanes cannot consume that bottom 20% of the bucket. The `operator` lane can.

Lane derivation in `hooks/rate-limiter.sh`:

1. `COS_RATE_LIMIT_PRIORITY_LANE` if explicitly set.
2. `orchestrator` when `RATE_LIMIT_RETRY_COUNT > 0`.
3. `operator` for fresh invocations.

## Diversity Penalty

The limiter stores recent action signatures. For Bash, the signature is a hash of `.tool_input.command`.

If one signature dominates at least 80% of a window after 5 events, future matching calls cost 2 tokens instead of 1. This throttles likely loops without banning repeated legitimate commands.

## Phase-Aware Limits

| Phase | Modifier |
|-------|----------|
| `reconstruction` | 1.5x refill limits |
| `stabilization` | 1.0x refill limits |
| `production` | 0.75x refill limits |
| `maintenance` | 0.5x refill limits |

## Configuration

In `cognitive-os.yaml` under `security.rate_limits`:

```yaml
security:
  rate_limits:
    max_tool_calls_per_minute: 30
    max_agent_launches_per_hour: 20
    max_bash_commands_per_minute: 15
    max_file_writes_per_minute: 10
    max_cost_per_hour_usd: 5.0
    cooldown_seconds: 60
    burst_multiplier: 1.5
    warning_threshold: 0.80
    operator_reserve_ratio: 0.20
    diversity_penalty_threshold: 0.80
    diversity_penalty_min_events: 5
    diversity_penalty_cost: 2.0
```

## Integration

- **Hook**: `hooks/rate-limiter.sh` (PreToolUse on Bash, Agent, Edit, Write)
- **Library**: `lib/rate_limiter.py` — token bucket, warnings, priority lane, diversity penalty, queue API
- **State**: `.cognitive-os/rate-limit-state.json` — counters, buckets, signatures, cost
- **Queue**: `.cognitive-os/rate-limit-queue.jsonl` — queued retries
- **Architecture**: `docs/04-Concepts/architecture/rate-limiter-flow-control.md`
- **Decision**: `docs/02-Decisions/adrs/ADR-101-intent-aware-rate-limiter.md`

## Manual Override

Prefer reset over disabling:

```python
from lib.rate_limiter import RateLimiter
RateLimiter().reset()
```

For emergency session suppression:

```bash
DISABLE_HOOK_RATE_LIMITER=true claude
```

## Contextual Trigger

This rule is always active. It applies to rate limiting, token buckets, cooldowns, retry queues, operator priority, and repeated tool-call loops.
