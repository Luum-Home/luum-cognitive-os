# Rate Limit Protection

## Always Active

Rate limits are monitored on every agent launch via `hooks/rate-limit-protection.sh` (PreToolUse on Agent).

### Thresholds

| Usage | Action |
|-------|--------|
| < 50% | Silent pass |
| 50-79% | INFO (logged only) |
| 80-94% | WARN with status |
| >= 95% | BLOCK (exit 2) with resume instructions |

### Auto-Pause Behavior

At 95%, agent launches are blocked. Session state is auto-saved to `.cognitive-os/rate-limit-pause.json` for resume after the rate limit window resets (~60 min rolling).

### Override

Set `RATE_LIMIT_OVERRIDE=true` for emergencies. This bypasses the block but does NOT increase actual API limits.

### Limits (Defaults)

| Limit | Default | Config Key |
|-------|---------|------------|
| Hourly tokens | 5M | `resources.rate_limit.hourly_token_limit` |
| Daily tokens | 50M | `resources.rate_limit.daily_token_limit` |
| Agents/hour | 30 | `resources.rate_limit.max_agents_per_hour` |

### Lib Module

`lib/rate_limit_protection.py` provides `RateLimitProtection` class with `check()`, `should_launch_agent()`, `record_usage()`, and formatting helpers.

### Metrics

Checks logged to `.cognitive-os/metrics/rate-limit-checks.jsonl`. Cost events in `.cognitive-os/metrics/cost-events.jsonl`.
