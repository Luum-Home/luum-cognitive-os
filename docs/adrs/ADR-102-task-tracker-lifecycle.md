# ADR-102 — Task tracker lifecycle: pending → in_progress → terminal, with PID capture and zombie reaper

## Status

Accepted.

**Date:** 2026-04-30  
**Author:** luum (session: task-tracker-lifecycle-fix)

---

## Context

Four systemic bugs were diagnosed in the task tracker lifecycle on 2026-04-30, causing queue saturation via zombie `in_progress` records:

**Bug 1 — Premature `in_progress` write:**  
`hooks/agent-prelaunch.sh` and `hooks/_lib/task_bridge.py::register()` wrote `status: "in_progress"` at PreToolUse time — before the agent process existed. When an agent failed to start (harness crash, cancel), the record stayed `in_progress` indefinitely. This caused `dispatch_gate_check.py` to count phantom slots and block legitimate agent launches. 4 zombie records saturated the queue on the day of diagnosis.

**Bug 2 — No PID capture:**  
All records in `active-tasks.json` had `pid: null`, even for successfully-completed tasks. `agent_health_monitor.py::_classify_task()` has dead-PID detection logic that was never reachable because `pid` was always `null`. The liveness check was a dead code path.

**Bug 3 — Zombie reaper skips `pid=null` records:**  
`scripts/so-reaper.sh` delegates to `lib.process_registry` which only processes PIDs in the registry. Records with `pid=null` are invisible to it. Stale `pending`/`in_progress` records with no PID accumulated without any automatic cleanup.

**Bug 4 — Queue↔active-tasks split state:**  
`dispatch-queue.json` and `active-tasks.json` were two independent state files with no synchronization. When a queue item was cancelled or dispatched, the corresponding `active-tasks.json` record was not updated. This broke any consumer that relied on `active-tasks.json` as the authoritative source.

---

## Decision

### Fix 1 — Defer `in_progress` until agent actually starts

**`hooks/agent-prelaunch.sh`** now writes `status: "pending"` at PreToolUse time, along with a `requested_at` timestamp. The `in_progress` status is only written when the agent's own process runs.

**`hooks/_lib/task_bridge.py::register()`** follows the same change: writes `"pending"` instead of `"in_progress"`. `panel_context()` is updated to include pending tasks alongside in-progress tasks so the orchestrator sees the full active set.

**`hooks/_lib/dispatch_gate_check.py`** already counts only `status == "in_progress"` records — no change needed. Pending records correctly do not consume dispatch slots.

### Fix 2 — PID capture via subagent preamble

**`scripts/write_context_marker.py`** gains a new function `_claim_pending_task(repo, pid, tool_use_id)`:

- When called with `kind="subagent"`, the function finds the most recent `pending` record in `active-tasks.json` matching the agent's `toolUseId` (read from `CLAUDE_TOOL_USE_ID` env), falls back to the most recently created `pending` record if no toolUseId match is found.
- Sets `status="in_progress"`, `pid=<os.getpid()>`, `started_at=now`.
- Uses `fcntl.LOCK_EX` + atomic temp-rename for concurrent safety.
- Best-effort: swallows all errors — a failed PID capture does not abort the subagent.

This is best-effort because the harness does not currently inject `CLAUDE_TOOL_USE_ID` into the subagent environment. The fallback (most-recent-pending) is slightly fragile under high concurrency (multiple pending records from rapid launches), but is correct for the common case of sequential launches.

### Fix 3 — Zombie reaper extension

**`scripts/so-reaper.sh`** gains a second Python sweep after the existing process-registry cleanup. The sweep reads `active-tasks.json` with an `fcntl` exclusive lock and applies:

| Record state | Verdict | Action |
|---|---|---|
| `in_progress`, PID set, PID dead | zombie | `status = "cancelled-zombie"`, `completedAt = now`, note |
| `pending`, PID null, age > 30 min | stale | `status = "cancelled-stale"`, `completedAt = now`, note |
| `pending`, PID null, age ≤ 30 min | starting | left alone |
| `completed`/`failed`/other | terminal | left alone |

The reaper **never kills processes** — it only marks records. The 30-minute stale threshold is intentionally generous to cover slow subagent startup.

The sweep runs at the existing reaper cadence (every 300 seconds via `reaper-daemon-launcher.sh` background loop, plus at SessionEnd). No frequency increase was made.

### Fix 4 — Queue↔active-tasks sync

**`lib/queue_drainer.py`** gains:

- `_sync_active_tasks(tool_use_id, new_status, note)`: internal helper that updates the active-tasks.json record matching `tool_use_id` (falls back to most-recent-pending). Uses `fcntl` exclusive lock + atomic rename.
- `cancel_queued(agent_id, tool_use_id)`: removes from dispatch-queue and calls `_sync_active_tasks(..., "cancelled-dequeued")`.
- `mark_dispatched(agent_id, tool_use_id)` (replaces old signature): sets dispatch-queue status to `"dispatching"` and calls `_sync_active_tasks(..., "in_progress")`.

The old `mark_dispatched(agent_id: str) -> bool` (no sync) is removed.

---

## Consequences

### Positive

- **Dispatch gate accuracy restored:** pending records do not consume slots, so the gate counts only genuinely running agents.
- **Queue draining unblocked:** stale records no longer cause permanent saturation.
- **PID-based liveness checks now reachable:** `agent_health_monitor._classify_task()` dead-PID logic can fire once subagents start capturing PIDs.
- **Authoritative state:** `active-tasks.json` is kept consistent with `dispatch-queue.json` across cancel and dispatch operations.

### Negative / Trade-offs

- **PID capture requires subagent preamble cooperation:** the `write_context_marker.py` call must be in the subagent's own execution path. If a subagent skips the preamble (e.g., raw subprocess without preamble injection), PID remains null and the record falls back to stale-age cleanup at 30 min.
- **Fallback matching is heuristic under concurrency:** when `CLAUDE_TOOL_USE_ID` is not in env, we match the most recently created pending record. Under burst launches (>1 agent per second), the wrong record could be claimed. Mitigation: toolUseId injection from harness fixes this entirely.
- **30-minute stale threshold means slow cleanup:** a crashed subagent that never ran its preamble leaves a `pending` record for up to 30 minutes before the reaper cleans it. This is acceptable given the reaper runs every 5 minutes.

---

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.
## Files Changed

| File | Change |
|---|---|
| `hooks/agent-prelaunch.sh` | Write `pending` instead of `in_progress` |
| `hooks/_lib/task_bridge.py` | `register()` writes `pending`; `panel_context()` shows pending tasks |
| `scripts/write_context_marker.py` | Add `_claim_pending_task()`, call it on `kind="subagent"` |
| `scripts/so-reaper.sh` | Add zombie sweep of `active-tasks.json` |
| `lib/queue_drainer.py` | Add `_sync_active_tasks()`, `cancel_queued()`, update `mark_dispatched()` |
| `tests/unit/test_task_tracker_lifecycle.py` | New test suite (14 tests, all passing) |
| `tests/unit/test_task_bridge.py` | Updated status assertion to `"pending"` |

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/unit/test_task_tracker_lifecycle.py tests/unit/test_task_bridge.py -q
```
