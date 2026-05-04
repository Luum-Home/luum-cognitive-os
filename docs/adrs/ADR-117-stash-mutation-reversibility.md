# ADR-117 — Stash Mutation Must Be Reversible-by-Design

**Status:** Proposed
**Date:** 2026-05-02
**Authors:** Cognitive OS governance session

---

## Status

Proposed (2026-05-02). R1 has landed; R2-R4 remain in flight and are governed by this reversibility contract.

## Context

On 2026-05-02, a compounding false-done incident produced **5 or more involuntary revert events in a single session**. Post-mortem analysis (see `docs/incidents/2026-05-02-false-done-compounding.md` and `docs/reports/stash-resolution-2026-05-01.md`) identified a shared root cause: `git stash` operations in OS hooks were:

- **Anonymous** — stash messages were auto-generated (`WIP on branch`), making forensic identification unreliable
- **Destructive on failure** — hooks used `git stash pop`, which drops the stash entry on apply even when the apply itself partially fails, losing work silently
- **Unaudited** — no structured log recorded which hook pushed/applied/dropped which stash and when
- **Uncoordinated** — multiple concurrent hooks and sessions could push/apply/drop stashes without awareness of each other, producing the 59-file invisible stash-leak observed in the incident
- **Unbounded** — no maximum on accumulated stashes per session; stale entries accumulated undetected

The stash leak in that incident was not detected until an adversarial review was manually triggered. By that time, 59 modified files had been silently withheld from working tree state, invalidating agent observations and contributing to cascading false-done reports.

**This ADR codifies the policy contract that every current and future hook touching `git stash` MUST satisfy.**

Referenced ADRs for co-located context:
- ADR-105 (claim verification contract)
- ADR-106 (multi-session safety primitives)
- ADR-113 (validation capsule liveness)
- ADR-116 (multi-session coordination primitives)

---

## Decision

Every `git stash` operation executed by an OS hook (in `hooks/`, `packages/*/hooks/`, or any script invoked by a hook) MUST satisfy the following five invariants simultaneously:

### 1. Named — stashes carry a stable, machine-parseable identifier

Stash push messages MUST embed either:
- a UUID generated at push time, or
- a composite `{session-id}:{hook-name}:{epoch}` identifier

Acceptable:
```sh
git stash push -m "cos-pre-agent:${SESSION_ID}:${HOOK_NAME}:$(date +%s)"
```

Not acceptable:
```sh
git stash          # anonymous — forbidden
git stash push     # anonymous — forbidden
git stash push -m "WIP"   # no stable identifier — forbidden
```

### 2. Apply-by-name — never `git stash pop`

Hooks MUST apply a stash by its named reference and then explicitly drop it:

```sh
STASH_REF=$(git stash list | grep "${STASH_LABEL}" | head -1 | cut -d: -f1)
git stash apply "${STASH_REF}"   # apply: leaves stash intact if apply fails
git stash drop "${STASH_REF}"    # explicit drop: only after successful apply
```

`git stash pop` is **forbidden** in hook code because it atomically drops the stash entry before signalling apply failure, making recovery impossible.

### 3. Auditable — every stash operation emits a JSONL event

Every push, apply, and drop MUST append a line to `.cognitive-os/metrics/stash-ops.jsonl`:

```json
{"ts":"2026-05-02T14:31:00Z","hook":"pre-agent-snapshot","name":"cos-pre-agent:abc123:pre-agent-snapshot:1746192660","action":"push","status":"ok"}
{"ts":"2026-05-02T14:31:45Z","hook":"post-agent-restore","name":"cos-pre-agent:abc123:pre-agent-snapshot:1746192660","action":"apply","status":"ok"}
{"ts":"2026-05-02T14:31:45Z","hook":"post-agent-restore","name":"cos-pre-agent:abc123:pre-agent-snapshot:1746192660","action":"drop","status":"ok"}
```

Required fields: `ts` (ISO-8601), `hook` (string), `name` (stash message/label), `action` (`push|apply|drop`), `status` (`ok|fail|skip`).

Failure to write to the log is non-fatal (hooks MUST NOT abort on log write errors), but MUST emit a stderr warning.

### 4. Budget — max 5 unrestored stashes per session before blocking

Before every new stash push, a hook MUST check the count of unrestored session stashes:

```sh
UNRESTORED=$(git stash list | grep -c "${SESSION_ID}" || true)
if [ "${UNRESTORED}" -ge 5 ]; then
  echo "WARNING: stash budget exhausted (${UNRESTORED} unrestored for session ${SESSION_ID})" >&2
  # emit warning to stash-ops.jsonl (action: "budget-warn")
  # block new snapshot push — return non-zero so caller falls back gracefully
  exit 1
fi
```

The budget limit of 5 is a session-scoped guardrail. Exceeding it indicates a missing restore path (a hook pushed but its paired hook never applied), which is itself a defect.

### 5. Coordinated — stash-mutating hooks MUST acquire the stash lock

Any hook that executes a push, apply, or drop MUST acquire `.cognitive-os/runtime/stash.lock` before operating and release it after. This uses the `flock` library introduced in R3.

Exemptions are allowed only when:
- the hook is provably read-only with respect to stash (e.g., a hook that only reads `git stash list`)
- the exemption is documented in the hook header with a comment beginning `# STASH-LOCK-EXEMPT:`

---

## Consequences

### Positive

- **Structural prevention of the silent-revert pattern.** Named, apply-by-name stashes ensure that a partial failure leaves a recoverable stash entry. There is no silent revert; the operator can always `git stash apply <ref>`.
- **Traceable audit trail for forensic recovery.** `stash-ops.jsonl` provides a chronological, machine-readable record. Post-mortem analysis that previously required grepping `git reflog` can now query structured data.
- **Session isolation.** Budget enforcement and session-tagged names prevent stash accumulation from leaking across sessions, eliminating the 59-file invisible-stash class of incident.

### Negative

- **Slight latency per stash operation.** Lock acquisition via `flock` adds approximately 5 ms per operation. This is acceptable for the pre/post-agent hook cadence (typically once per agent invocation), but may be noticeable if a hook calls stash in a tight loop.
- **New hook author learning curve.** Any contributor writing a hook that touches stash must understand the five-invariant contract. Without tooling enforcement, this relies on code review. The compliance gate (see below) partially mitigates this.
- **JSONL write dependency.** Hooks that run in sandboxed environments where `.cognitive-os/metrics/` is read-only will fail to write the audit log. The non-fatal fallback (warn on stderr, continue) prevents hook abort, but the audit trail will be incomplete.

---

## Implementation Status

| Primitive | Description | Status |
|-----------|-------------|--------|
| **R1** — `post-agent-snapshot-restore` hook | Restores named stashes after agent completes; paired with pre-agent push | **Landed** (in `hooks/post-agent-snapshot-restore.sh`) |
| **R2** — Auto-checkpoint named stashes library | `lib/stash_ops.py` providing `push_named()`, `apply_by_name()`, `drop_by_ref()`, `audit_append()` | **In flight** |
| **R3** — `flock`-based stash lock library | `lib/stash_lock.sh` wrapping `flock .cognitive-os/runtime/stash.lock` with TTL and cleanup | **In flight** |
| **R4** — Session budget warning | Budget check integrated into stash push path; warn at ≥5 unrestored stashes | **In flight** |

R2, R3, and R4 are under active development as of 2026-05-02. This ADR is the policy specification against which those implementations will be verified.

---

## Compliance Gate

A pre-commit hook OR contract test (to be introduced alongside R2) MUST flag any new or modified hook file that contains:

```
git stash push
git stash pop
git stash$
```

...without a corresponding invocation of the `stash_lock` library or an explicit `# STASH-LOCK-EXEMPT:` annotation.

The compliance checks are currently distributed across `tests/integration/test_auto_checkpoint_named_stash.py`, `tests/integration/test_stash_lock.py`, `tests/integration/test_stash_lock_hook_wiring.py`, `tests/integration/test_stash_reapply.py`, `tests/integration/test_stash_budget_warn.py`, and `tests/behavior/test_stash_leak_alarm.py`. A future consolidation may add a single contract wrapper, but this ADR no longer names a non-existent required path.

Until a single contract wrapper exists, code review MUST verify that any hook PR touching stash keeps those behavior and integration tests green.

---

## Alternatives rejected

1. **Allow anonymous `git stash` in hooks and rely on manual reflog recovery.** Rejected because the 2026-05-02 incident showed anonymous stashes made forensic recovery slow and unreliable.
2. **Continue using `git stash pop` because it is shorter.** Rejected because failed apply can drop the only recoverable copy and turn a temporary conflict into silent data loss.
3. **Warn only when stash count is high.** Rejected because warnings after mutation do not make stash operations reversible; named apply/drop and lock discipline are required.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/integration/test_stash_lock.py -q
```

## References

- ADR-105 — Claim Verification Contract (`docs/adrs/ADR-105-claim-verification-contract.md`)
- ADR-106 — Multi-Session Safety Primitives (`docs/adrs/ADR-106-multi-session-safety-primitives.md`)
- ADR-113 — Validation Capsule Liveness (`docs/adrs/ADR-113-validation-capsule-liveness.md`)
- ADR-116 — Multi-Session Coordination Primitives (`docs/adrs/ADR-116-multi-session-coordination-primitives.md`)
- Post-mortem: `docs/incidents/2026-05-02-false-done-compounding.md`
- Investigation report: `docs/reports/stash-resolution-2026-05-01.md`
- Revert-investigation task context: R1 (landed), R2–R4 (in flight)
