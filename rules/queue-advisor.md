<!-- SCOPE: both -->
# Queue Advisor — Dynamic Dispatch Prioritization

## Purpose

Dynamically reorders the dispatch queue based on runtime state instead of
relying solely on static priority levels and FIFO ordering within those levels.

When the dispatch queue has multiple agents waiting for a slot, the advisor
ensures that the most valuable agent launches next — not just the one that
arrived first at the same priority level.

## Scoring Factors

Each queued item is scored 0–100 by five weighted dimensions:

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| `dependency_score` | 0.30 | Tasks that unblock N other queued tasks score `N * 25` (capped at 100). Tasks with unmet dependencies score 0. |
| `budget_score` | 0.25 | When daily spend > 80% of `daily_alert_usd`, haiku tasks score 100, sonnet 50, opus 0. Under 80% all score 50 (neutral). |
| `context_score` | 0.20 | When context usage > 70%, tasks with shorter descriptions (fewer estimated tokens) score higher. Neutral (50) otherwise. |
| `staleness_score` | 0.15 | `min(minutes_waiting * 5, 100)`. A task waiting 10 minutes earns 50 points. 20 minutes = 100. |
| `model_efficiency_score` | 0.10 | haiku = 100, sonnet = 60, opus = 30. Always a slight preference for cheaper models. |

**Final score** = weighted sum, range 0–100. Ties are broken by original priority level, then FIFO.

## Integration with QueueDrainer

`QueueDrainer.get_ready_agents()` accepts an optional `use_advisor` parameter (default `True`):

```python
from lib.queue_drainer import QueueDrainer

drainer = QueueDrainer()

# Default: advisor reorders candidates before slot limit is applied
ready = drainer.get_ready_agents()

# Explicit: same as above
ready = drainer.get_ready_agents(use_advisor=True)

# Original behaviour: pure priority + FIFO, no advisor
ready = drainer.get_ready_agents(use_advisor=False)
```

When `use_advisor=True` each returned item includes two extra fields:

| Field | Type | Example |
|-------|------|---------|
| `advisor_score` | float | `87.5` |
| `advisor_reason` | str | `"unblocks dependents; waited 12m"` |

### Graceful Fallback

If the advisor fails (import error, corrupt state files, any exception) the
drainer falls back to the original priority-FIFO order silently. Existing
behaviour is never broken.

## Direct Usage

```python
from lib.queue_advisor import QueueAdvisor

advisor = QueueAdvisor(project_dir=".")

# Collect current state (budget, context, dependencies)
state = advisor.get_runtime_state()

# Reorder a list of queue items (auto mode: LLM for 5+ items, algorithmic otherwise)
reordered = advisor.advise(queue_items)

# Force algorithmic (v1) — zero API cost
reordered = advisor.advise(queue_items, mode="algorithmic")

# Force LLM (v2) — always uses haiku, falls back to v1 on failure
reordered = advisor.advise(queue_items, mode="llm")

# Human-readable summary
print(advisor.format_advice(reordered))
# → "Launching 'Implement auth' next (score: 87 — unblocks dependents; waited 12m)."
# → "Queue order: [Implement auth (87), Write tests (62), Update docs (41)]"
```

## Runtime State Sources

| State | Source |
|-------|--------|
| Daily spend | `.cognitive-os/metrics/cost-events.jsonl` (today's entries) |
| Daily budget limit | `cognitive-os.yaml` → `resources.budget.daily_alert_usd` |
| Context usage | `.cognitive-os/metrics/context-usage.jsonl` (last entry) |
| Task dependencies | `.cognitive-os/tasks/active-tasks.json` (`depends_on` field) |
| Completed tasks | `.cognitive-os/tasks/active-tasks.json` (status `completed`/`done`) |

All sources are read-only and best-effort — missing files are treated as
zeroed state rather than errors.

## LLM-Powered v2 Mode

`QueueAdvisor.advise()` supports three modes via the `mode` parameter:

| Mode | When LLM is used | Cost |
|------|-----------------|------|
| `"algorithmic"` | Never | $0 |
| `"auto"` (default) | Queue has ≥ 5 items | ~$0.003/call |
| `"llm"` | Always | ~$0.003/call |

### How v2 Works

When the LLM path activates:

1. **v1 scores first** — algorithmic scoring runs unconditionally to produce a baseline. These scores are embedded in the LLM prompt.
2. **Haiku prompt sent** — a structured prompt is sent via `claude -m haiku -p ...` (subprocess, 30 s timeout). The prompt contains:
   - Task list (id, description, model, priority, v1 score)
   - Runtime state (budget %, context %, completed tasks, active agents)
3. **LLM reorders** — haiku returns a JSON array `[{"id": "...", "reason": "..."}]`. Items are reordered accordingly.
4. **Graceful fallback** — any failure (claude CLI not found, timeout, invalid JSON, unknown task IDs) silently falls back to v1 algorithmic ordering.

### What the LLM Can Detect

- **Semantic dependencies**: "write tests for X" logically depends on "implement X" even without an explicit `depends_on` link
- **Task conflicts**: tasks that write to the same files should not run in parallel
- **Batching opportunities**: related tasks that benefit from sequential execution
- **Description-based cost estimation**: more accurate token forecasts than character-length heuristics

### v1 vs v2 Comparison

| Property | v1 algorithmic | v2 LLM |
|----------|---------------|--------|
| API cost | $0 | ~$0.003/call |
| Dependency inference | Explicit `depends_on` only | Semantic (implicit deps) |
| Conflict detection | None | File-edit conflict detection |
| Reason field | e.g. `"waited 12m"` | e.g. `"[llm] unblocks 3 others"` |
| Failure mode | Never fails | Falls back to v1 |

### Auto-Threshold Rationale

$0.003 per haiku call is worth the cost only when the queue is large enough that ordering matters. Below 5 items the difference in execution order has minimal impact on throughput — v1 algorithmic is used instead.

## Metrics

The advisor adds `advisor_score` and `advisor_reason` to every dispatched
item. These fields are visible in the orchestrator's queue drain output and
can be logged to `.cognitive-os/metrics/dispatch-queue.json` for trend
analysis.

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| `queue-drain.md` | Queue drain drives when to call `get_ready_agents`. Advisor controls which item is selected. |
| `resource-governance.md` | Advisor reads daily budget from the same config that resource governance enforces. |
| `task-dag.md` | Dependency scoring uses the same `depends_on` fields that the TaskDAG system populates. |
| `context-management.md` | Context score uses the same 70% threshold that triggers context-management warnings. |
| `model-routing.md` | Model efficiency scoring reinforces the preference for cheaper models under budget pressure. |
