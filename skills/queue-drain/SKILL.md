---
name: queue-drain
description: Periodic agent queue drain and health check
trigger: Scheduled via CronCreate every 5 minutes, or invoked manually when agents may be stuck
version: 1.0.0
---

# Queue Drain

Checks the agent dispatch queue for ready agents, launches them, and reports
on agent health. Designed to be invoked by a CronCreate scheduled task or manually
when the queue may have stuck items.

## Steps

### 1. Run the combined drain + health report

```bash
python3 -c "
from lib.scheduled_drain import drain_and_report
print(drain_and_report())
"
```

### 2. Interpret the output

The output contains two sections separated by a blank line:

- **QUEUE DRAIN** line: indicates how many agents are ready to launch, or that
  the queue is empty.
- **AGENT HEALTH** section: reports on tasks currently in progress and whether
  any are overdue.

### 3. Act on the output

**If agents are ready to launch** (output starts with "QUEUE DRAIN: N agent(s) ready"):

For each ready agent, call the Agent tool with the queued prompt and model:

```python
from lib.queue_drainer import QueueDrainer
drainer = QueueDrainer()
ready = drainer.get_ready_agents()
for agent in ready:
    drainer.mark_dispatched(agent["id"])
    # Launch: Agent tool with agent["prompt"], model=agent["model"]
    # After completion: drainer.remove_completed(agent["id"])
```

**If queue is empty**:

Report "Queue empty, all clear." and cancel the scheduled drain task if one exists,
since polling an empty queue wastes tokens.

**If dead agents found** (AGENT HEALTH reports TIMEOUT or DEAD tasks):

- For TIMEOUT tasks (running too long): report to user with task details
- For DEAD tasks (PID no longer alive): update task status to failed and
  re-enqueue if retries remain

### 4. Cancel periodic drain when queue is empty

To stop wasting tokens polling an empty queue:

```python
from lib.scheduled_drain import should_schedule_drain
if not should_schedule_drain():
    # Cancel or skip re-creating the CronCreate task
    print("Queue empty — periodic drain no longer needed")
```

## When to Create the CronCreate Task

The orchestrator should create the scheduled drain task when:
- An agent launch is blocked (dispatch-gate outputs QUEUED_AGENTS)
- The queue has items but no completion is expected soon

```python
from lib.scheduled_drain import get_cron_create_spec
spec = get_cron_create_spec()
# Use CronCreate tool with spec["prompt"], recurring every 5 minutes
```

## Success Criteria

- [ ] All ready agents in the queue are launched
- [ ] Health report is generated and checked
- [ ] Dead/stuck agents are reported or re-queued
- [ ] If queue is empty, periodic polling is cancelled
