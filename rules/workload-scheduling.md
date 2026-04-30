<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Workload Scheduling

> **REMOVED 2026-04-20**: `lib/workload_scheduler.py` was deleted (0 production callers, 16KB dead code).
> The scheduling concepts described here remain valid; re-implement if needed.

## Purpose

When the orchestrator has multiple tasks to dispatch (e.g., SDD batches, parallel agents, sprint tasks), the WorkloadScheduler plans which tasks to dispatch immediately and which to queue based on current rate limit availability, task priority, and cost headroom.

## When to Use

| Scenario | Use Scheduler? |
|----------|---------------|
| Single task | No -- dispatch directly |
| 2-3 concurrent tasks | Optional -- check available_slots() first |
| 4+ concurrent tasks | Yes -- call scheduler.plan() to optimize dispatch order |
| SDD batch apply | Yes -- schedule task batches respecting agent launch limits |
| Sprint task execution | Yes -- prioritize critical tasks, queue lower-priority ones |

## Algorithm

1. **Sort** tasks by priority (1=critical first, 10=low last), then by cost (cheaper first within same priority)
2. **Check** available agent launch slots from RateLimiter
3. **Check** cost headroom from hourly cost cap
4. **Fill** available slots with highest-priority tasks that fit within cost cap
5. **Queue** remaining tasks with estimated next dispatch time

## Integration

```python
from lib.workload_scheduler import WorkloadScheduler, TaskRequest

scheduler = WorkloadScheduler()

tasks = [
    TaskRequest(id="auth", description="Implement auth endpoint",
                priority=1, estimated_tokens=50000, model="sonnet"),
    TaskRequest(id="tests", description="Write unit tests",
                priority=5, estimated_tokens=20000, model="sonnet"),
    TaskRequest(id="docs", description="Update API docs",
                priority=10, estimated_tokens=10000, model="haiku"),
]

plan = scheduler.plan(tasks)

# Dispatch immediately
for task in plan.dispatch_now:
    launch_agent(task)

# Queue the rest
for task in plan.queued:
    enqueue_for_later(task)
```

## Priority Levels

| Priority | Name | Use Case |
|----------|------|----------|
| 1 | Critical | Security fixes, blocking bugs, auth changes |
| 2-3 | High | Core feature implementation, SDD apply phases |
| 5 | Normal | Standard tasks, tests, documentation |
| 7-8 | Low | Cleanup, formatting, non-urgent refactors |
| 10 | Background | Archiving, metrics collection, auto-skill generation |

## Cost Estimation

The scheduler auto-estimates cost from token count and model using published prices. Override with `estimated_cost_usd` for known costs.

| Model | ~10K tokens | ~50K tokens | ~100K tokens |
|-------|-------------|-------------|--------------|
| haiku | $0.01 | $0.05 | $0.10 |
| sonnet | $0.11 | $0.54 | $1.08 |
| opus | $0.54 | $2.70 | $5.40 |

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| Rate Limiting (`rate-limiting`) | Scheduler reads rate limit state to determine available slots |
| Resource Governance (`resource-governance`) | Cost estimates feed into budget tracking |
| Model Routing (`model-routing`) | Scheduler respects model assignment per task |
| Decomposition (`decomposition`) | Large tasks should be decomposed before scheduling |
| Responsiveness (`responsiveness`) | Report schedule plan to user before dispatching |

## Metrics

Schedule plans can be logged to `.cognitive-os/metrics/workload-schedule.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "total_tasks": 5,
  "dispatched": 3,
  "queued": 2,
  "slots_available": 3,
  "slots_total": 20,
  "estimated_cost_usd": 2.50,
  "phase": "reconstruction"
}
```

## Contextual Trigger

This rule is loaded when: workload scheduling, task batching, parallel dispatch, agent queue, batch planning.
