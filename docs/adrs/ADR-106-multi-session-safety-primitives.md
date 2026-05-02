# ADR-106 — Multi-Session Safety Primitives

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-05-02
**Author**: Matias Nahuel Améndola
**Related**: ADR-088 (provenance markers), ADR-089 (multi-session git coordination), ADR-098 (multi-agent file coordination), ADR-104 (startup circuit breaker), `docs/incidents/2026-05-02-false-done-compounding.md`

## Status

Proposed. Policy definition and primitive specifications. Implementation of each primitive is tracked as a separate task.

## Context

The 2026-05-02 incident exposed three concurrent failure modes in multi-IDE / multi-agent workflows:

**1. Stash leak**: `pre-agent-snapshot.sh` auto-stashed 59 modified files before a parallel agent ran. The stash was never re-applied. The operator and subsequent agents had no signal that 59 files of invisible work existed in `stash@{0}`.

**2. Uncoordinated concurrent commits**: a second orchestrator session (X-COS-Session: 1777732313 / 1777731331) committed `eaac243f`, `49c46c69`, `b1de3c40` to main concurrently with the primary session. No collision occurred by luck (non-overlapping files), but no mechanism prevented or detected the overlap.

**3. False-done propagation across sessions**: the primary driver of the incident (covered by ADR-105) is that a false `[x]` in a plan file, once committed, becomes the ground truth for any subsequent session that reads the plan. In multi-IDE environments, Session B opens during Session A's commit window and reads the stale plan state without knowing it is false.

ADR-089 covers git-index coordination. ADR-098 covers file-level edit locking within a session. Neither covers: stash lifecycle alarms, plan file advisory locking across sessions, commit provenance cross-referencing, or orchestrator-level bilateral verification.

## Decision

Four primitives, each independently deployable.

---

### Primitive 1 — Stash Leak Alarm

**Problem**: auto-pre-agent stashes created by `pre-agent-snapshot.sh` silently accumulate. Unapplied stashes represent invisible state.

**Policy**:

- At every `SessionStart` and before every agent dispatch, check for stashes whose reflog message matches `auto-pre-agent-*`.
- If any such stash is older than `COS_STASH_LEAK_TTL` (default: 600 seconds / 10 minutes), emit a WARN-level alarm to the operator via stdout and write to `.cognitive-os/runtime/stash-leak-alarm.json`.
- If the stash is older than `COS_STASH_LEAK_BLOCK_TTL` (default: 3600 seconds / 1 hour), **block dispatch** until the operator explicitly resolves it via `git stash pop` or `git stash drop` and removes the alarm file.

**Commands for operator**:

```bash
# List unapplied auto-pre-agent stashes
git stash list | grep auto-pre-agent

# Apply and resolve
git stash pop stash@{N}

# Discard (if work is superseded)
git stash drop stash@{N}

# Clear alarm after resolution
rm -f .cognitive-os/runtime/stash-leak-alarm.json
```

**Alarm schema** (`.cognitive-os/runtime/stash-leak-alarm.json`):

```json
{
  "detected_at": "<ISO8601>",
  "stash_ref": "stash@{N}",
  "stash_message": "auto-pre-agent-<hash>",
  "age_seconds": N,
  "file_count": N,
  "blocking": true|false
}
```

---

### Primitive 2 — Plan File Advisory Lock

**Problem**: two sessions can simultaneously read and modify the same plan file. Session A closes `[x]` based on false verification; Session B reads `[x]` before Session A's correction lands.

**Policy**:

- Before writing a `[ ]` → `[x]` transition to any plan file under `.cognitive-os/plans/`, the writing session MUST acquire an advisory lock: `mkdir .cognitive-os/runtime/plan-locks/<plan-filename>.lock/`.
- Lock contains: `session_id`, `agent_id`, `pid`, `acquired_at`, `purpose`.
- A second session attempting to write the same plan file receives an error with the lock holder's metadata and MUST NOT proceed until the lock is released.
- Lock TTL: `COS_PLAN_LOCK_TTL` (default: 1800 seconds). Stale locks (PID dead OR TTL expired) are auto-cleared on next acquire attempt.
- Lock is released when the session completes the plan update and commits, or on session end.

**This is advisory**: it does not prevent reads. It only gates concurrent writes. Sessions that only read plan files (for context) are unaffected.

---

### Primitive 3 — Commit Provenance Enforcement

**Problem**: commits from concurrent orchestrator sessions are indistinguishable in `git log`. No mechanism surfaces "these 3 commits came from a different session than the other 4."

**Policy**:

- Every commit to `main` (or any branch tracked by a COS orchestrator) MUST carry an `X-COS-Session` trailer in the commit message body, following ADR-088 provenance marker format.
- Format: `X-COS-Session: <COGNITIVE_OS_SESSION_ID>`
- The `pre-commit` hook validates that `X-COS-Session` is present when `COGNITIVE_OS_SESSION_ID` is set in environment. If the env var is set and the trailer is absent, the commit is rejected with: `ERROR: Missing X-COS-Session provenance trailer. Add: X-COS-Session: <session-id>`.
- When two sessions commit concurrently, the session IDs differ, making the parallel activity visible in `git log --format="%H %s %b"` queries.

**Kill-switch**: `COS_SKIP_PROVENANCE_CHECK=1` bypasses the pre-commit check (for manual operator commits). Every bypass is logged to `.cognitive-os/runtime/provenance-bypass.jsonl`.

---

### Primitive 4 — Orchestrator Bilateral Verification Gate

**Problem**: orchestrators commit sub-agent output that contains false-done claims without independent verification.

**Policy** (see also ADR-105 §4):

- Before any orchestrator commit that transitions a plan checkbox from `[ ]` to `[x]`, the orchestrator MUST run the bilateral verification command for every high-stakes claim in the wave (per ADR-105 definitions).
- The orchestrator documents the verification commands and their exit codes in the commit message body or an adjacent `.cognitive-os/runtime/verification-log/` entry.
- If any bilateral check fails: the orchestrator does NOT commit, surfaces the discrepancy to the operator, and marks the plan item as `[ ]` (reverting the false-done).

**Implementation note**: this is an orchestrator behavioral rule, not a hook. Hooks cannot run arbitrary verification commands on behalf of the orchestrator. The orchestrator is responsible for exercising this gate.

---

### Future Work — Cross-Session Reconciler

A cross-session reconciler would periodically compare plan file state across worktrees and active sessions, detecting `[x]` divergence before it compounds. This is deferred: the four primitives above address the immediate failure modes; a reconciler requires session-to-session IPC that does not yet exist in the stack.

Tracking reference: see `docs/architecture/FROZEN-BACKLOG.md`.

---

## Consequences

### Positive

- Stash leaks surface immediately rather than silently persisting across sessions.
- Plan file concurrent writes produce an explicit error instead of silent last-write-wins.
- Parallel session activity is visible in git log via X-COS-Session trailers.
- Orchestrator bilateral check provides a formal gate before false-done reaches main.

### Negative

- Plan lock TTL introduces a failure mode: a crashed session holds the lock until TTL expires (30 min max). Mitigation: stale-PID detection on acquire, same pattern as ADR-098.
- Provenance trailer requirement adds 1 line to every commit message. Operator manual commits need `X-COS-Session` or `COS_SKIP_PROVENANCE_CHECK=1`.
- Stash block threshold (1 hour) may fire legitimately on long sessions with intentional deferred stashes. Operator can clear the alarm file after inspecting the stash.

### Neutral

- These primitives are additive: they do not change existing hook, lock, or commit logic. They layer on top of ADR-089 (git-index) and ADR-098 (file edit).

## Alternatives rejected

| Alternative | Rejection reason |
|---|---|
| Hard-block all parallel sessions (one-at-a-time discipline) | Incompatible with real workflows (human + multiple concurrent agents). ADR-098 rejected this for the same reason. |
| CRDT merge for plan files | Sobreingeniería at current session volume (2-4 concurrent). Defer until evidence of need (same reasoning as ADR-098 CRDT discussion). |
| Rely on git conflict detection | Plan files rarely conflict at the line level even when logically conflicting (`[x]` in two different sections). Git merge succeeds silently. |
| Enforce provenance via branch naming | Branch names are not part of commit records; does not survive merge. Trailers persist in commit history. |

## Verification

Each primitive is independently verifiable:

**Primitive 1** (stash alarm):
```bash
# Simulate stash leak: create auto-pre-agent stash, wait, check alarm
git stash push -m "auto-pre-agent-test-$(date +%s)" -- /dev/null
# After TTL: alarm file should appear at .cognitive-os/runtime/stash-leak-alarm.json
```

**Primitive 2** (plan lock):
```bash
bash scripts/plan-lock.sh acquire .cognitive-os/plans/so-existential.md "test"
# Second acquire from different session-id → exit 2 with holder metadata
COGNITIVE_OS_SESSION_ID=other bash scripts/plan-lock.sh acquire .cognitive-os/plans/so-existential.md "test"
bash scripts/plan-lock.sh release .cognitive-os/plans/so-existential.md
```

**Primitive 3** (provenance):
```bash
# Commit without trailer while COGNITIVE_OS_SESSION_ID is set → rejected
COGNITIVE_OS_SESSION_ID=test-session git commit -m "test commit" --allow-empty
# Expected: ERROR: Missing X-COS-Session provenance trailer
```

**Primitive 4** (bilateral gate):
Verified manually: orchestrator runs bilateral commands and documents exit codes before committing plan closures. No automated test exists yet; behavioral correctness depends on orchestrator following this ADR.

## References

- Incident: `docs/incidents/2026-05-02-false-done-compounding.md`
- ADR-105: bilateral claim verification contract (companion ADR)
- ADR-088: provenance markers (extends X-COS-Session trailer convention)
- ADR-089: multi-session git coordination (git-index layer)
- ADR-098: multi-agent file coordination (file-edit layer)
- ADR-099: pre-agent snapshot copy-on-untracked (origin of auto-pre-agent stashes)
- `scripts/pre-agent-snapshot.sh`: stash creation source
- `.cognitive-os/runtime/`: runtime state directory for alarms, locks, logs
