# Post-Mortem — Dispatch Queue Empty Prompt and Ghost Validation Lock — 2026-05-20

## Summary

Two blocked Agent launches were reported as queued, but the persisted dispatch queue contained one corrupt entry with an empty prompt. At the same time, a stale validation-capsule lock was reported as an active capsule even though it had no live process evidence and pointed at a non-existent capsule directory.

This was not a single implementation typo. It was a systemic contract failure across three agentic primitives:

1. validation lock liveness could report metadata as active without proving the capsule existed;
2. dispatch-gate enqueueing could persist missing Agent intent as a successful queue item;
3. queue draining treated corrupt empty-prompt items as ready work.

## Impact

- User intent could be silently lost when a blocked Agent launch entered the dispatch queue without its payload.
- Multiple blocked launches with missing payload collapsed to one queue row because the empty string has a stable SHA-256 fingerprint prefix: `e3b0c44298fc1c14`.
- Operators saw a misleading recovery message: “Agent enqueued — Will launch when the gate clears.”
- Ghost validation locks could block real dispatch while pointing at a non-existent capsule directory.

## Detection

The incident was detected manually when the operator inspected the runtime state after dispatch-gate blocks. The observable symptoms were:

- `.cognitive-os/tasks/dispatch-queue.json` contained `"prompt": ""`.
- The queue item had `_fingerprint: "e3b0c44298fc1c14"`.
- Repeated blocked Agent calls reused the same queue ID.
- A validation lock message referenced a stale capsule path rather than a live process/capsule pair.

## Root Cause

The root cause was missing structural invariants at state boundaries.

### Boundary 1 — validation lock state

`cos_validation_lock_active()` trusted a lock with a future TTL unless a stale signal fired. It did not require a positive owner PID or an existing `capsule_dir` for validation-capsule-shaped locks.

`cos_validation_lock_message()` separately read `message`/`command` from the lock file, so user-facing output could describe a capsule as running even when the liveness decision was stale or incomplete.

### Boundary 2 — dispatch-gate enqueue state

`hooks/dispatch-gate.sh` extracted the Agent prompt from `tool_input.prompt`, `tool_input.description`, or `tool_input.task`. When stdin or tool payload was unavailable, this resolved to an empty string. The hook still called `QueueDrainer.enqueue()` and printed success.

The audit also found a concrete Bash expansion bug: `${_STDIN_JSON:-{}}` appended
an extra `}` when `_STDIN_JSON` was non-empty, corrupting the JSON handed to the
Python enqueue helper. That made a real Agent payload parse as invalid and fall
back to empty prompt behavior.

### Boundary 3 — queue persistence state

`QueueDrainer.enqueue()` accepted any string, including `""`, and computed the duplicate-detection fingerprint from that string. `QueueDrainer.get_ready_agents()` returned queued items without validating the prompt, making corrupt rows launchable.

## Why Earlier Fixes Did Not Resolve It

Prior fixes optimized for individual failure modes rather than end-to-end intent preservation:

- ADR-113 hardened liveness around TTL, PID, heartbeat, and activity, but did not state that user-facing “running” output must be derived from the same validated active decision.
- Queue-drain documentation promised that the queue stores “the full agent prompt,” but did not make non-empty prompt a schema invariant.
- Dispatch-gate tests checked that blocked launches were enqueued, but not that they were enqueued with non-empty, relaunchable payloads.
- The Bash helper used a brace-heavy default expansion in a JSON context, but no
  regression test checked that the exact stdin JSON survived into the enqueue
  subprocess.
- Recovery UX treated “wrote a queue row” as success instead of requiring “wrote a valid queue row that can relaunch the user’s intent.”

The systemic miss was accepting observability claims without executable contracts: active lock, queued agent, and ready work were status labels, not proven states.

## Corrective Actions

### P0 — Queue integrity

- `QueueDrainer.enqueue()` must reject empty/whitespace-only prompts.
- `QueueDrainer.get_ready_agents()` must quarantine existing empty-prompt queued items instead of returning them as ready.
- `dispatch-gate.sh` must report enqueue failure when the Agent payload is unavailable instead of printing a queue ID.

### P0 — Validation lock integrity

- Validation locks with missing/non-positive owner PID must be stale unless protected by the very-young SessionStart race window in cleanup.
- Validation locks with `capsule_dir` present but missing on disk must be stale.
- User-facing lock messages must be printed only after the active decision has passed, and must avoid echoing stale metadata after cleanup.

### P1 — Contract and regression tests

- Add regression coverage for empty stdin / missing Agent payload.
- Add regression coverage for queue corruption quarantine.
- Add regression coverage for ghost validation locks with `pid=0` and nonexistent `capsule_dir`.
- Update queue-drain docs to include `status: corrupt` and prompt validity requirements.

## Prevention Pattern

For all durable SO runtime state, status must be derived from invariant checks:

| State claim | Required proof |
|---|---|
| lock active | lock exists, schema valid, TTL valid, owner PID live, heartbeat not stale when present, capsule path valid when present |
| agent queued | prompt is non-empty and persisted with a stable ID/fingerprint |
| agent ready | queue item is queued, valid, not stale, and has relaunchable prompt |
| recovery success | the persisted row can actually perform the promised recovery action |

## Verification

Targeted verification should run:

```bash
python3 -m pytest tests/unit/test_queue_drainer.py \
  tests/unit/test_validation_capsule.py \
  tests/unit/test_dispatch_gate_perf.py -q
```

A broader follow-up lane should include dispatch/queue integration tests once the P0 invariants pass locally.
