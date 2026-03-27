# Rate Limiting Protocol

## Purpose

Prevents token flooding, excessive tool usage, and runaway costs by enforcing per-minute and per-hour limits on all tool invocations. The rate limiter is ALWAYS active and applies to every tool call.

## Default Limits

| Action Type | Limit | Window | Rationale |
|-------------|-------|--------|-----------|
| `tool_call` | 30 per minute | 60s | General tool flood prevention |
| `agent_launch` | 20 per hour | 3600s | Prevents context exhaustion from agent spawning |
| `bash_command` | 15 per minute | 60s | Prevents runaway shell execution loops |
| `file_write` | 10 per minute | 60s | Prevents rapid file thrashing |
| Cost | $5.00 per hour | 3600s | Budget safety net independent of resource-governance |

## Behavior

- **PreToolUse hook** (`hooks/rate-limiter.sh`) checks limits before every tool call
- When a limit is exceeded: **BLOCK** (exit 2) with a cooldown message
- The cooldown is 60 seconds by default
- State is persisted to `.cognitive-os/rate-limit-state.json`
- Old entries are automatically cleaned up outside their window

## Phase-Aware Limits

| Phase | Modifier |
|-------|----------|
| `reconstruction` | 1.5x limits (higher throughput during rebuild) |
| `stabilization` | 1.0x limits (default) |
| `production` | 0.75x limits (stricter to protect stability) |
| `maintenance` | 0.5x limits (minimal activity expected) |

Phase modifiers are applied by overriding the config values in `cognitive-os.yaml`.

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
```

## Integration

- **Hook**: `hooks/rate-limiter.sh` (PreToolUse on Bash, Agent, Edit, Write)
- **Library**: `lib/rate_limiter.py` — Python module with check/record/status/reset API
- **State**: `.cognitive-os/rate-limit-state.json` — persisted counters
- **Safety Mesh**: Layer 10 in the safety mesh (see `docs/safety-mesh.md`)

## Manual Override

To reset rate limits (e.g., after a legitimate burst):

```python
from lib.rate_limiter import RateLimiter
RateLimiter().reset()
```

## Contextual Trigger

This rule is always active. It applies to every tool call via the PreToolUse hook.
