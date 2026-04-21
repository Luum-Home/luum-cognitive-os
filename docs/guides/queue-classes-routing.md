# Queue Classes Routing Guide

The Cognitive OS uses several distinct queue implementations. Choosing the wrong one is a common source of confusion. This table maps each class to its purpose and the situations where it applies.

## Queue Class Reference

| Class | Module | Purpose | When to use |
|-------|--------|---------|-------------|
| `RateLimitQueue` | `lib/rate_limiter.py` | Holds agent-launch requests that were blocked by the rate limiter. Auto-retries them when the token budget recovers. Uses `rate-limit-queue.jsonl` on disk. | When an agent launch is blocked at 95% token budget; the dispatch-gate feeds blocked requests here automatically. |
| `QueueDrainer` | `lib/queue_drainer.py` | Slot-based dispatch queue for agent launches blocked because all parallel slots are full (not due to token budget). Drained as slots open. | When `dispatch-gate.sh` blocks a launch due to `max_parallel_agents` being reached. Used by the dispatch pipeline, not directly by orchestrators. |
| `QueueAdvisor` | `lib/queue_advisor.py` | Dynamic dispatch prioritizer. Reorders the dispatch queue by weighted heuristic scoring (budget, context, staleness, task dependencies). | Invoke before draining `QueueDrainer` to get an optimally-ordered task list. Use in the orchestrator's sprint-planning loop. |
| `DeadLetterQueue` | `lib/dead_letter_queue.py` | Holds agent tasks that exhausted all retries (3 attempts, all failed). Prevents silent loss of work. Stored in `.cognitive-os/dead-letter-queue.jsonl`. | After an agent's retry budget is exhausted, the auto-refine hook feeds the task here. Operators inspect it with `/queue-status`. |
| `FileMutationQueue` | `lib/file_mutation_queue.py` | Per-file serialization for concurrent write access. Ensures that concurrent agent edits to the same file are serialized (not interleaved). | Wire when two or more agents may write the same file simultaneously. Not auto-wired; must be called explicitly from file-writing code paths. |
| `RequestQueue` | `lib/request_queue.py` | Persists user messages that arrive via `system-reminder` while the orchestrator is busy running agents. Survives context compaction. Stored in the session directory as `user-requests.jsonl`. | The orchestrator calls `enqueue_request()` immediately on every incoming system-reminder message. Read back with `dequeue_request()` / `mark_done()`. |
| `WorkQueue` | `lib/work_queue.py` | Persistent cross-session work queue. Survives session boundaries via `.cognitive-os/work-queue.json`. Updated by `session-hygiene.sh` at session end. | For tracking multi-session task backlogs. The orchestrator reads this at session start to restore pending work. Use `/session-backlog` to inspect. |

## Decision tree

```
Agent launch blocked?
  ├── Blocked by token budget (>95%)?  → RateLimitQueue (automatic)
  └── Blocked by slot limit?           → QueueDrainer (automatic via dispatch-gate.sh)

Task failed after 3 retries?          → DeadLetterQueue (automatic via auto-refine hook)

Two agents writing the same file?     → FileMutationQueue (manual wiring required)

User message arrived while busy?      → RequestQueue (orchestrator calls enqueue_request)

Need to reorder the dispatch queue?   → QueueAdvisor.reorder()

Task must survive session boundary?   → WorkQueue
```

## Storage locations

| Class | Storage |
|-------|---------|
| `RateLimitQueue` | `.cognitive-os/rate-limit-queue.jsonl` |
| `QueueDrainer` | in-memory (not persisted) |
| `QueueAdvisor` | reads from QueueDrainer state |
| `DeadLetterQueue` | `.cognitive-os/dead-letter-queue.jsonl` |
| `FileMutationQueue` | in-memory with per-file threading locks |
| `RequestQueue` | `{session_dir}/user-requests.jsonl` |
| `WorkQueue` | `.cognitive-os/work-queue.json` |
