---
adr: 113
title: Validation Capsule Liveness Primitives
status: accepted
implementation_status: implemented
date: '2026-05-02'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation/shipped/delivered evidence
---

<!-- SCOPE: os-only -->
# ADR-113: Validation Capsule Liveness Primitives

## Status

Accepted — 2026-05-02.
**Deciders**: orchestrator (incident-driven)
**Supersedes**: extends ADR-106 (multi-session safety primitives) §P3 (orchestrator bilateral verification gate); does NOT supersede ADR-098 (multi-agent file coordination)
**Cross-refs**: ADR-105 (claim verification contract), ADR-106 (multi-session safety primitives), `docs/06-Daily/incidents/2026-05-02-false-done-compounding.md`

## Context

The validation capsule lock (`hooks/_lib/validation-lock.sh`, `scripts/cos-validation-capsule.sh`) blocks new agent dispatches while another session validates the repository. Today's lock file at `.cognitive-os/runtime/validation-capsule.lock` carries:

- `pid` — owner shell PID
- `expires_at_epoch` — TTL fail-safe
- `started_at_epoch`, `run_id`, `head`, `capsule_dir`, `command`, `message`

The current liveness check (`cos_validation_lock_active()`):
1. Checks `expires_at_epoch < now` → stale
2. Else `os.kill(pid, 0)` → if `ProcessLookupError`, stale; else assumed active

This is correct for crashed processes, killed terminals, and TTL expiry. But during the 2026-05-02 session the orchestrator hit dispatch-gate blocks back-to-back across multiple capsules from parallel sessions. The operator could not distinguish:

- "validation is genuinely working — wait"
- "validation is hung but PID alive — break it"
- "validation finished but trap missed cleanup — break it"

The only escape today is `COS_VALIDATION_ALLOW_CONCURRENT_AGENTS=1`, a global bypass that defeats the protection. There is no targeted remedy.

## Decision

Extend the validation capsule lock with **5 liveness primitives** that fail-safe and self-heal without operator intervention in the common case, and provide ergonomic tooling for the rare case where intervention is needed.

### P1 — Heartbeat (mechanical liveness)

Capsule launcher spawns a background heartbeat writer that updates `last_heartbeat_epoch` in the lock JSON every **30 s**. The cleanup trap kills the heartbeat on exit.

**Lock file extension**:
```json
{
  "pid": 91283,
  "expires_at_epoch": 1717350000,
  "started_at_epoch": 1717348500,
  "last_heartbeat_epoch": 1717349850,
  "heartbeat_interval_seconds": 30
}
```

**Stale rule**: `now - last_heartbeat_epoch > 3 * heartbeat_interval_seconds` → stale (allow 3 missed beats before declaring death).

Catches: deadlocks, busy loops, sleeping forever, OOM-killed-but-PID-reused.

### P2 — Activity log (semantic liveness)

Capsule subprocess appends to `.cognitive-os/runtime/validation-activity.jsonl` every time a meaningful event occurs (test invocation, file write inside the capsule). One JSON line per event:

```json
{"ts":"2026-05-02T16:35:56Z","capsule":"validation-...","action":"test_run","detail":"pytest tests/unit/"}
{"ts":"2026-05-02T16:36:12Z","capsule":"validation-...","action":"file_write","detail":".cognitive-os/metrics/validation.jsonl"}
```

The capsule populates this best-effort. As a fallback for non-instrumented commands, the validation hook scans capsule's metrics directory mtime; if newest mtime > 5 min old, semantic-stale.

**Stale rule**: activity staleness is a secondary signal only when the owner PID is dead or missing. If the PID is alive and heartbeat is fresh, a quiet long-running validation command must stay active even when `last_activity_ts` is older than 300 s.

### P3 — Diagnostic command `cos validation status`

New script `scripts/cos-validation-status.sh` (`SCOPE: os-only`). Reports:

```
$ bin/cos validation status
Capsule:        validation-20260502T163556Z-91283
PID:            91283 (alive)
Age:            2m 14s
Heartbeat:      12s ago         [HEALTHY]   (interval: 30s)
Last activity:  8s ago          [HEALTHY]   (action: test_run)
Verdict:        WORKING
Wait estimate:  5-15 min based on similar runs
```

When the verdict is bad:

```
Verdict:        STALE
Reason:         heartbeat 12m old (threshold 90s)
Suggestion:     bin/cos validation break --capsule validation-20260502T163556Z-91283
Audit:          previous similar incidents in .cognitive-os/metrics/validation-stale.jsonl
```

### P4 — Targeted recovery `cos validation break`

New script `scripts/cos-validation-break.sh` (`SCOPE: os-only`). Replaces the global `COS_VALIDATION_ALLOW_CONCURRENT_AGENTS=1` bypass with a targeted, audited operation:

```
$ bin/cos validation break --capsule validation-20260502T163556Z-91283
This will:
  1. Send SIGTERM to PID 91283
  2. Wait 5s; if still alive, SIGKILL
  3. Remove .cognitive-os/runtime/validation-capsule.lock
  4. Remove worktree at /var/folders/.../validation-...
  5. Append audit entry to .cognitive-os/audit/validation-breaks.jsonl
Continue? [y/N]
```

Flags:
- `--capsule ID` (required) — must match the active lock's `run_id` to prevent break-by-typo
- `--force` — skip prompt (only for cron / automation)
- `--no-kill` — remove lock without killing the PID (when PID owner is human-managed)
- `--reason TEXT` — required text written to audit trail

Audit entry:
```json
{
  "ts": "2026-05-02T16:50:00Z",
  "actor_pid": 12345,
  "broken_capsule": "validation-20260502T163556Z-91283",
  "broken_pid": 91283,
  "reason": "stale: heartbeat 12m old",
  "stale_signals": ["heartbeat", "activity"],
  "method": "sigterm-then-sigkill"
}
```

`COS_VALIDATION_ALLOW_CONCURRENT_AGENTS=1` remains for emergency global bypass but is deprecated in user-facing docs.

### P5 — SessionStart auto-recovery

New hook `hooks/validation-lock-cleanup.sh` (`SCOPE: os-only`). Registered as SessionStart hook in `scripts/apply-efficiency-profile.sh`. On every session start:

1. Read all `*.lock` files under `.cognitive-os/runtime/`
2. For each: apply 4-layer staleness check (TTL → PID → heartbeat → activity). Activity is advisory while PID+heartbeat are healthy; it may delete only ownerless/dead locks.
3. If stale: remove + log to `.cognitive-os/metrics/validation-auto-recovery.jsonl`
4. Print summary to stderr if any cleanup happened

This catches the common case where a session ended without trap firing (terminal closed, kernel panic, laptop sleep then wake to a different network).

Idempotent. Never blocks session start. Logs but does not warn unless ≥1 lock cleaned (signal vs noise).

## Consequences

### Positive

- **Hang detection**: P1+P2 catch alive-but-frozen processes (current gap)
- **Self-healing**: P5 cleans up after closed terminals automatically; the operator never sees stale locks from sessions they don't remember
- **Ergonomic recovery**: P4 replaces global bypass with targeted, audited operation; operator confidence increases
- **Diagnostic transparency**: P3 turns "WHY am I blocked?" from grep + jq archaeology into one command
- **No protocol break**: existing TTL+PID logic preserved; new fields are additive

### Negative / Cost

- **+30s heartbeat interval = additive load**: 1 file write every 30s during validation. Negligible (validation runs minutes; few writes).
- **Activity log size growth**: bounded by validation duration; rotates with capsule lifecycle (lives in capsule dir, dies with capsule).
- **Implementation cost**: ~3-4h estimated (5 small components + tests).
- **Audit trail growth**: `validation-breaks.jsonl` and `validation-auto-recovery.jsonl` grow over time; rotation needed (deferred to follow-up).

### Risks

- **Heartbeat thread leaks**: if the cleanup trap doesn't kill the heartbeat subprocess, leftover heartbeats could falsely keep the lock fresh. Mitigation: trap uses PGID-kill, plus P5 cleanup eventually catches it via PID liveness when terminal closes.
- **Activity log false negatives**: a legitimate long-running validation step (e.g., big pytest with long collection phase) might not write metrics for 5 min. Mitigation: 5 min threshold tuneable via env; status command shows elapsed time for operator judgement.
- **Race: P5 cleanup vs concurrent capsule starting**: very narrow window where P5 deletes a lock as another session writes one. Mitigation: P5 reads `started_at_epoch` and only deletes locks older than 60 s.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep only PID and TTL checks | Cannot distinguish real long-running validation from an alive-but-hung process. |
| Use `COS_VALIDATION_ALLOW_CONCURRENT_AGENTS=1` as the standard escape | Bypasses the safety boundary globally and reintroduces concurrent mutation risk. |
| Require manual lock deletion without diagnostics | Forces operators to guess whether validation is still productive. |

## Implementation Plan

| Component | File | Hours |
|---|---|---|
| Heartbeat writer | `scripts/cos-validation-capsule.sh` (modify) | 0.5 |
| Lock reader extension | `hooks/_lib/validation-lock.sh` (modify) | 0.5 |
| Activity log emit + read | `scripts/cos-validation-capsule.sh` + `hooks/_lib/validation-lock.sh` | 0.5 |
| `bin/cos validation status` | `scripts/cos-validation-status.sh` (new) | 0.75 |
| `bin/cos validation break` | `scripts/cos-validation-break.sh` (new) | 0.75 |
| SessionStart cleanup hook | `hooks/validation-lock-cleanup.sh` (new) | 0.5 |
| `bin/cos` dispatch routing | `bin/cos` (modify, add `validation` subcommand) | 0.25 |
| `apply-efficiency-profile.sh` registration | (modify) | 0.25 |
| Tests | `tests/unit/test_validation_capsule.py` (extend) + `tests/integration/test_validation_status_break.py` (new) | 1.0 |

**Total**: ~5h (vs initial 3-4h estimate; tests inflated by KD6-style invariant tests).

## Acceptance Criteria

- [ ] Lock file written by `cos-validation-capsule.sh` includes `last_heartbeat_epoch` and `heartbeat_interval_seconds`
- [ ] `cos_validation_lock_active()` returns 1 (stale) when heartbeat > 3× interval old
- [ ] `cos_validation_lock_active()` returns 1 (stale) when activity > 5 min stale (semantic check)
- [ ] `bin/cos validation status` produces structured report distinguishing HEALTHY / STALE for each signal
- [ ] `bin/cos validation break --capsule X --reason TEXT` removes lock + kills PID + writes audit; refuses without `--reason`
- [ ] `hooks/validation-lock-cleanup.sh` runs at SessionStart; cleans only locks ≥60s old; logs to JSONL
- [ ] Tests cover: heartbeat staleness, activity staleness, status command output schema, break command targeting + audit, P5 cleanup idempotency, race-window protection
- [ ] No regression: existing TTL + PID checks still work
- [ ] Documentation: `docs/05-Methodology/runbooks/validation-capsule-recovery.md` (NEW) explains operator workflows

## Verification

```bash
python3 -m pytest tests/unit/test_validation_capsule.py -q
python3 -m pytest tests/unit/test_validation_capsule_liveness.py -q
bash scripts/cos-validation-status.sh --help
```

## References

- Incident: `docs/06-Daily/incidents/2026-05-02-false-done-compounding.md` §Multi-session race
- Related: ADR-098 (multi-agent file coordination), ADR-106 (multi-session safety primitives), ADR-099 (pre-agent snapshot)
- Code: `hooks/_lib/validation-lock.sh`, `scripts/cos-validation-capsule.sh`, `tests/unit/test_validation_capsule.py`
- Bypass deprecation: `COS_VALIDATION_ALLOW_CONCURRENT_AGENTS=1` retains emergency function but is no longer the recommended escape


## 2026-05-02 correction

`make test-laptop` exposed a race where a quiet but live pytest process inside a validation capsule could be treated as semantically stale and the capsule worktree removed mid-run. The corrected rule is: live PID plus fresh heartbeat is authoritative liveness; activity staleness may only reap ownerless/dead locks. Cleanup primitives that remove validation capsule worktrees must also check the source repo validation lock before `git worktree remove --force`.
