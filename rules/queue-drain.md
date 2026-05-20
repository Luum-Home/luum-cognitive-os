<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Queue Drain Protocol

## Purpose

When dispatch-gate.sh blocks an agent launch (all slots full), the agent prompt
is automatically enqueued in `.cognitive-os/tasks/dispatch-queue.json`.
On each task completion, the orchestrator MUST drain the queue.

Queue integrity invariant: a queued Agent item is valid only when `prompt` is a
non-empty string. A missing or whitespace-only prompt is not a recoverable queued
launch; it is corrupt state and MUST NOT be dispatched.

## When to Drain

**Trigger**: Every time a sub-agent or task completes (task-notification arrives).

## Action Protocol

```
1. Import and check the queue:
   from lib.queue_drainer import QueueDrainer
   drainer = QueueDrainer()
   ready = drainer.get_ready_agents()

2. If ready is non-empty:
   - For each agent in ready:
     a. drainer.mark_dispatched(agent["id"])
     b. Launch the agent using the agent["prompt"] and agent["model"]
     c. On completion: drainer.remove_completed(agent["id"])

3. If ready is empty:
   - Continue normally (queue empty or no slots available yet)
```

## Shell One-Liner (for hooks)

```bash
python3 -c "
from lib.queue_drainer import QueueDrainer
d = QueueDrainer()
print(d.format_drain_instruction())
"
```

## Queue File

Location: `.cognitive-os/tasks/dispatch-queue.json`

Schema per item:
```json
{
  "id": "uuid",
  "prompt": "the full agent prompt",
  "description": "short description",
  "model": "sonnet",
  "priority": 5,
  "enqueued_at": "ISO-8601",
  "status": "queued | dispatching | corrupt"
}
```

`status: corrupt` is reserved for rows that cannot safely relaunch user intent,
including empty Agent prompts. Drainers must skip corrupt rows. Operators should
inspect the original session transcript and relaunch manually if the lost prompt
is recoverable.

## Priority Rules

- Items are launched in priority order (1=critical, 5=normal, 10=low)
- Within the same priority, FIFO ordering applies
- Items older than 4 hours are auto-pruned

## Idempotency

The same prompt is never enqueued twice. Re-submitting an identical prompt
returns the existing queue item ID without adding a duplicate.

Empty prompts are rejected before fingerprinting. This prevents the SHA-256
empty-string fingerprint (`e3b0c44298fc1c14`) from collapsing unrelated blocked
launches into one queue row.

## CronCreate Scheduling (Periodic Fallback)

When agents are queued but no completion event is expected soon (e.g., all active
agents finish simultaneously and no `completion-gate` fires), a CronCreate scheduled
task prevents stuck queue items.

### When to create the scheduled task

Create the CronCreate task when:
- `dispatch-gate.sh` blocks a launch and enqueues an agent
- The orchestrator detects items in `.cognitive-os/tasks/dispatch-queue.json`

```python
from lib.scheduled_drain import should_schedule_drain, get_cron_create_spec

if should_schedule_drain():
    spec = get_cron_create_spec()
    # Use CronCreate tool with spec["prompt"], runs every 5 minutes
```

### CronCreate prompt (what the scheduled session runs)

```
Check the agent dispatch queue and launch any ready agents.

1. Run: python3 -c "from lib.scheduled_drain import drain_and_report; print(drain_and_report())"
2. If agents are ready, launch them using the Agent tool with the queued prompt and model
3. For each agent: mark_dispatched(id) before, remove_completed(id) after
4. If dead agents found, escalate to user
5. If queue is empty: report "Queue empty — no action needed" and do NOT reschedule
```

### Cost management

Each CronCreate session costs ~$0.03–0.10. To avoid polling an empty queue:
- Cancel or stop re-scheduling when `should_schedule_drain()` returns `False`
- The scheduled task itself checks `format_drain_instruction()` and exits early if empty

### Skill

Use `/queue-drain` skill (`skills/queue-drain/SKILL.md`) inside the CronCreate session
for full step-by-step instructions.

## Integration

| Primitive | Role |
|-----------|------|
| `hooks/dispatch-gate.sh` | Enqueues blocked launches (PreToolUse) |
| `lib/queue_drainer.py` | Queue management: enqueue, get_ready, mark_dispatched, remove_completed |
| `lib/scheduled_drain.py` | Combined drain + health report; CronCreate spec helper |
| `lib/dispatch_helper.py` | Slot availability check (active task count vs max_parallel_agents) |
| `skills/queue-drain/SKILL.md` | Instructions for the CronCreate session |
| `.cognitive-os/tasks/dispatch-queue.json` | Persistent queue file |

## Contextual Trigger

This rule is loaded when: dispatch queue, agent queued, queue drain, blocked agent launch,
slot available, task completion, cron drain, scheduled drain.
