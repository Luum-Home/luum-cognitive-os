---
type: methodology-synthesis
source: docs/05-Methodology/guides/queue-classes-routing.md
provenance: "Reference table mapping each of the Cognitive OS's distinct queue implementations to its purpose, trigger condition, and storage location to prevent misuse."
---

## What it is
A disambiguation guide for the seven distinct queue implementations in the Cognitive OS, since picking the wrong queue class is a common source of confusion. Provides a purpose/trigger table, a decision tree, and a storage-location table.

## Key mechanics
- **`RateLimitQueue`** (`lib/rate_limiter.py`): holds agent-launch requests blocked by the token-bucket rate limiter; auto-retries as budget recovers. Triggered automatically by the dispatch-gate at >95% token budget. Storage: `.cognitive-os/rate-limit-queue.jsonl`.
- **`QueueDrainer`** (`lib/queue_drainer.py`): slot-based dispatch queue for launches blocked by `max_parallel_agents`, not token budget. Drained as slots open; used internally by the dispatch pipeline (`dispatch-gate.sh`), not called directly by orchestrators. Storage: in-memory, not persisted.
- **`QueueAdvisor`** (`lib/queue_advisor.py`): dynamic dispatch prioritizer reordering the queue by weighted heuristic (budget, context, staleness, task dependencies). Invoked before draining `QueueDrainer`, in the orchestrator's sprint-planning loop. Storage: reads from `QueueDrainer` state.
- **`DeadLetterQueue`** (`lib/dead_letter_queue.py`): holds tasks that exhausted all 3 retries, preventing silent work loss. Fed automatically by the auto-refine hook; operators inspect via `/queue-status`. Storage: `.cognitive-os/dead-letter-queue.jsonl`.
- **`FileMutationQueue`** (`lib/file_mutation_queue.py`): per-file serialization so concurrent agent writes to the same file aren't interleaved. Must be wired explicitly from file-writing code paths — not auto-wired. Storage: in-memory with per-file threading locks.
- **`RequestQueue`** (`lib/request_queue.py`): persists user messages arriving via `system-reminder` while the orchestrator is busy, surviving context compaction. Orchestrator calls `enqueue_request()` on every incoming system-reminder immediately; read back via `dequeue_request()`/`mark_done()`. Storage: `{session_dir}/user-requests.jsonl`.
- **`WorkQueue`** (`lib/work_queue.py`): persistent cross-session work-item backlog, surviving session boundaries; updated by `session-hygiene.sh` at session end, read by the orchestrator at session start, inspected via `/session-backlog`. Storage: `.cognitive-os/work-queue.json`.
- **Decision tree:** launch blocked by token budget → `RateLimitQueue` (automatic); blocked by slot limit → `QueueDrainer` (automatic via dispatch-gate); task failed 3x → `DeadLetterQueue` (automatic via auto-refine); two agents writing same file → `FileMutationQueue` (manual wiring); user message while busy → `RequestQueue` (orchestrator-invoked); need dispatch-queue reordering → `QueueAdvisor.reorder()`; task must survive session boundary → `WorkQueue`.

## Relations & where used
- `lib/rate_limiter.py`, `lib/queue_drainer.py`, `lib/queue_advisor.py`, `lib/dead_letter_queue.py`, `lib/file_mutation_queue.py`, `lib/request_queue.py`, `lib/work_queue.py` — the seven modules this guide indexes.
- `dispatch-gate.sh` — the hook that automatically feeds `RateLimitQueue` and `QueueDrainer`.
- `session-hygiene.sh` — updates `WorkQueue` at session end.
- Auto-refine hook — feeds `DeadLetterQueue` on retry exhaustion.
- `/queue-status`, `/session-backlog` — operator-facing inspection commands for `DeadLetterQueue` and `WorkQueue` respectively.
- Referenced directly by the global CLAUDE.md "User Request Persistence" rule (`RequestQueue`'s `enqueue_request`/`mark_done` contract).

## Status / caveats
- No explicit date; a stable reference/index table rather than a point-in-time report. Purely a routing/disambiguation guide — does not document internal queue algorithms beyond what's summarized in the "Purpose" column.
