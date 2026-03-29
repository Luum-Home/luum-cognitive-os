---
name: repair-status
description: Report on auto-repair system health and statistics
trigger: repair status, repair report, auto-repair, circuit breaker status
model: haiku
audience: project
---

# Repair Status

Report on the auto-repair system's current state.

## Protocol

1. Read `metrics/repair-outcomes.jsonl` -- count recent repairs (last 24h, last 7d)
2. Read `metrics/remediation-registry.jsonl` -- count known fixes, top fixes by usage
3. Read `metrics/circuit-breaker/` -- list any OPEN breakers
4. Read `metrics/hook-health.jsonl` -- check for hook failures
5. Read `metrics/repair-queue.jsonl` -- check for pending repairs

## Output format

### Repair System Status
- **Registry**: N known fixes (M auto-applicable)
- **Last 24h**: X repairs attempted, Y succeeded, Z failed
- **Circuit breakers**: all CLOSED | N OPEN (list)
- **Queue**: N pending repairs
- **Hook health**: all OK | N errors, M stale

### Top 5 Most-Used Fixes
| Error Pattern | Service | Times Applied | Success Rate |
|...|...|...|...|

### Recent Failures
| Timestamp | Error Type | Service | Reason |
|...|...|...|...|
