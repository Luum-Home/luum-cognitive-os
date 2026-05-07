# ADR-222 — Pre-Agent Stash Deferred Until Agent Launch Confirmed

<!-- SCOPE: OS -->

**Status**: Accepted — Slices 1–8 implemented (2026-05-07)
**Date**: 2026-05-06
**Related**: ADR-099 (pre-agent snapshot copy-on-untracked), ADR-116 (governed preflight), ADR-117 (stash mutation reversibility), ADR-200 (state retention controller), ADR-203 (subagent capability contract and launch preflight), ADR-213 (agent preflight before stash snapshot), ADR-221 (stash refs by SHA)
**Supersedes (in part)**: the PreToolUse-Agent ordering currently relied on by `pre-agent-snapshot.sh`.
**Source**: Operator session 2026-05-06 — multiple orphan `auto-pre-agent-*` stashes produced when `pre-agent-snapshot.sh` created a stash before launch success was guaranteed. ADR-213 moved `agent-prelaunch.sh` before the snapshot hook, but follow-up forensics showed other PreToolUse-Agent blockers still run after the snapshot hook; if any of them block, `PostToolUse` never fires and `post-agent-snapshot-restore.sh` never runs. The class remains until stash creation is deferred until launch confirmation or removed entirely.

---

## Context

ADR-213 (agent preflight before stash snapshot) acknowledged the problem in its own header text:

> *"this hook must run after blocking Agent preflight hooks such as `agent-prelaunch.sh`. It mutates git stash; if a later preflight blocks and PostToolUse never fires, WIP can be hidden in stash."*

The fix proposed there was an **ordering invariant**: ensure `pre-agent-snapshot.sh` runs *after* the blocking preflight (`agent-prelaunch.sh`, `cos_work_inventory.py --strict`). The 2026-05-06 follow-up forensics show that ordering invariant is **not sufficient end-to-end**:

- The hook *file* declares the invariant in a comment, but comments are not launch admission.
- There is no machine-checkable proof that **every** blocking PreToolUse-Agent hook in every projected harness profile runs before `pre-agent-snapshot.sh`.
- Different harnesses (Claude Code, Codex, OpenCode/OpenClaw-style runners) project hooks into PreToolUse in their own order; ADR-213's comment is advisory inside Cognitive OS but has no enforcement leverage on the harness scheduler.
- The first preflight may pass and a second one (different hook, different concern) may block — `pre-agent-snapshot.sh` would already have run and stashed.
- A preflight that emits a non-blocking warning today may upgrade to BLOCK tomorrow; the stash gets created speculatively each time unless launch confirmation is the boundary.

The structural property we need is not "stash runs after preflight." It is: **stash never exists unless the agent actually launched.**

This is what `auto-pre-agent` is trying to express. The current implementation expresses it incorrectly: it captures *speculatively at PreToolUse, hoping the launch happens*, and orphans the capture when it doesn't. The corrected expression is: capture *eagerly into a candidate*, but **only commit the capture to the stash store when the agent actually starts executing**.

This ADR specifies the corrected expression. It does **not** answer the larger question of whether `git stash` should be the capture primitive at all (the prior-art research report `docs/research/multi-agent-orchestration-prior-art-2026-05-06.md` argues it should not, and recommends worktree-per-write-agent as the long-term replacement). ADR-222 holds the line on correctness for as long as `git stash` is the implementation.

## Decision

Replace the speculative-capture-on-PreToolUse model with a **two-phase capture-then-commit pattern**:

1. **Phase 1 — Plan (PreToolUse)**:
   `pre-agent-snapshot.sh` runs *after* all blocking preflight hooks have passed (ADR-213 ordering, asserted by a manifest declaration — see "Manifest declaration" below). It does **not** invoke `git stash push`. It computes:
     - The set of files that would be stashed (`git status --porcelain`, `.cognitive-os/`-excluded paths).
     - A capture plan written to `.cognitive-os/runtime/pre-agent-plan-<agent_id>.json`.
     - For copy-on-untracked mode (ADR-099), the untracked-copy step proceeds (it is non-mutating to git state; it only writes to `.cognitive-os/snapshots/`). The tracked-modified stash is NOT yet pushed.

2. **Phase 2 — Commit (Agent launch confirmed)**:
   A new hook `agent-launch-confirmed.sh` (or, where the harness supports it, a PreToolUse-late phase) fires **after** the harness has confirmed the agent process is alive. It reads the plan, runs the actual `git stash push` keyed on the plan's file list, resolves the SHA per ADR-221, and writes the v2 marker.

3. **Phase 3 — Restore (PostToolUse)**:
   `post-agent-snapshot-restore.sh` runs as today, reading the v2 marker, applying by SHA. If the plan exists but no marker exists (Phase 2 never ran), the plan is consumed-and-deleted by the restore hook — no stash was created, no orphan, no race.

4. **Fallback for harnesses without a confirmed-launch signal**:
   Some harnesses do not expose "agent launched" as a separate event. For those, the Phase 2 commit is collapsed into the PreToolUse path *but only after* a `dispatch-gate` lock confirms preflight passed end-to-end. The lock is acquired at the start of the PreToolUse phase and released only if either (a) preflight blocks (no stash created) or (b) all preflight hooks reported PASS (stash committed). The `validation-lock.sh` library that ADR-099 already uses for `COS_VALIDATION_MODE` is the natural place to extend.

## Manifest declaration

```yaml
# manifests/pre-agent-snapshot.yaml
schema_version: pre-agent-snapshot/v2
status: active
owner: platform-safety

# ADR-213 ordering invariant — declared, not just commented
hook_ordering:
  PreToolUse:Agent:
    must_run_after:
      - agent-prelaunch.sh           # ADR-116 governed preflight
      - hook-timing-wrapper.sh       # ADR-* timing wrapper
    must_run_before:
      - agent-launch-confirmed.sh    # this ADR
      - PostToolUse:Agent:*

# Two-phase capture
phases:
  plan:
    when: PreToolUse:Agent (after preflight)
    mutates: ".cognitive-os/runtime/pre-agent-plan-<agent_id>.json"
    git_state_mutates: false        # invariant; tested
  commit:
    when: agent-launch-confirmed | end-of-PreToolUse-with-lock
    mutates: "git stash"
    git_state_mutates: true
    requires_plan: true             # commit refuses without a plan
  restore:
    when: PostToolUse:Agent
    mutates: "git stash apply"
    git_state_mutates: true

# Orphan handling
orphans:
  plan_without_marker:
    detect: "plan file exists, no marker, age > plan_ttl_seconds"
    plan_ttl_seconds: 300            # 5 min — agent launch should have committed by then
    action: delete                   # plan is cheap to recreate; deletion is safe
  marker_without_plan:
    detect: "marker file exists, plan deleted"
    action: log_warning              # stash exists but plan is gone — restore by SHA still works
  stash_without_marker:
    detect: "auto-pre-agent-* stash with no live marker pointing at it"
    action: emit stash_orphan event  # ADR-200 retention controller may reap per policy
```

## Hook ordering enforcement (ADR-213 made testable)

A new test, `tests/audit/test_pre_agent_hook_ordering.py`, parses the harness hook configurations (`settings.json`, `.claude/settings.local.json`, codex equivalents) and asserts:

- `pre-agent-snapshot.sh` is registered AFTER `agent-prelaunch.sh` in PreToolUse:Agent.
- `agent-launch-confirmed.sh` is registered AFTER `pre-agent-snapshot.sh` (or, in the fallback mode, the lock-protected variant is in use).
- `post-agent-snapshot-restore.sh` is the only PostToolUse:Agent hook that calls `git stash apply`.

This is the ADR-213 invariant lifted from a comment to a CI gate.

## Hard rules

- **Phase 1 (plan) MUST NOT touch `git stash`.** Verified by a test that runs the planning function against a dirty fixture and asserts `git stash list` is byte-identical before and after.
- **Phase 2 (commit) MUST NOT run if no plan file exists.** Refuses with a clear error rather than capturing speculatively.
- **Phase 2 MUST run under either a launch-confirmed signal or a dispatch-gate lock.** No third path; no `--force`.
- **Phase 3 (restore) MUST tolerate plan-without-commit.** A plan file with no corresponding marker is a normal, expected condition (preflight blocked / agent never launched) and is silently cleaned up.
- **Plan TTL is 5 minutes.** Any plan older than `plan_ttl_seconds` without a corresponding marker is auto-deleted by the next SessionStart hook (consumes ADR-200 retention controller cadence).
- **All stash references MUST be by SHA per ADR-221.** This ADR depends on ADR-221 for marker schema.
- **Hook ordering MUST be enforced by `tests/audit/test_pre_agent_hook_ordering.py`.** Comments in hook headers are documentation, not enforcement.

## Consequences

### Positive

- The 2026-05-06 orphan-stash class of bug becomes structurally impossible: no stash exists if the agent didn't launch.
- ADR-213's ordering invariant gets actual enforcement (CI test) instead of being a comment in a header.
- The validation-mode escape hatch (`COS_SUPPRESS_AGENT_SNAPSHOT`) becomes redundant for the "validation capsule mutates worktree" concern — there is no PreToolUse stash for it to skip.
- ADR-200 retention controller can reason cleanly about orphan stashes because the "blocked-preflight" producer is removed.
- The two-phase pattern matches the dominant industry pattern (see prior-art research): plan, then act, with a confirmed-launch boundary in between.

### Negative / trade-offs

- One more hook (`agent-launch-confirmed.sh`) in the lifecycle. Mitigation: in fallback mode, no new hook — the lock-extended PreToolUse path stays a single hook entry.
- Harnesses that don't emit a confirmed-launch signal must use the lock-fallback path, which is structurally similar to today's flow. Mitigation: explicitly documented; the test suite covers both modes.
- A 5-minute plan TTL means a slow harness that genuinely takes >5 min between PreToolUse and confirmed-launch will lose the plan and re-plan. Mitigation: tunable via manifest; default is conservative; telemetry will tell us if it's wrong.
- Migration: existing in-flight markers and plans from the v1 system must be drained. Mitigation: ADR-221 already specifies a one-cycle legacy reader; ADR-222 piggybacks on that path.

## Alternatives rejected

- **Just enforce ADR-213 ordering more loudly**: rejected. Even with perfect ordering, a downstream preflight (different hook, different concern) can block after `pre-agent-snapshot.sh` ran. Ordering is a necessary but not sufficient condition. The two-phase pattern is the sufficient one.
- **Run `pre-agent-snapshot.sh` as PostToolUse instead of PreToolUse**: rejected. By PostToolUse the agent has already executed and may have modified the working tree; the snapshot is no longer "the operator's pre-agent state."
- **Use a transactional `git` wrapper that auto-rolls-back the stash on agent-launch-failure**: rejected. Git has no native transaction primitive; emulating one means tracking exactly the SHA we'd track anyway, plus more code. The two-phase explicit version is simpler.
- **Capture via filesystem copy instead of stash, only for tracked files**: ADR-099 already does this for untracked. Extending to tracked is a bigger architectural move (it's effectively shadow-state, the Cline pattern called out in the prior-art research). Out of scope for ADR-222; tracked separately.
- **Eliminate auto-stash entirely (worktree-per-write-agent)**: this is the right long-term move. ADR-222 holds correctness while that move is sequenced.
- **Just delete `pre-agent-snapshot.sh`**: rejected for now. The non-zero population of operators who depend on it for accidental-edit recovery is real; removing without a replacement leaves a regression.

## Acceptance criteria

```bash
python3 -m pytest tests/audit/test_pre_agent_hook_ordering.py tests/unit/test_pre_agent_two_phase.py tests/behavior/test_pre_agent_blocked_preflight_no_orphan.py -q
```

The tests must prove:

- Hook ordering audit fails if `pre-agent-snapshot.sh` is moved to run before `agent-prelaunch.sh` in any harness's PreToolUse:Agent config.
- Phase-1 planning function leaves `git stash list` byte-identical (read-only invariant).
- Phase-2 commit refuses to run without a plan file, exits non-zero with a clear message.
- Phase-2 commit runs successfully when a plan exists and the lock is held.
- Behavior test: simulate a blocked preflight (return non-zero from `agent-prelaunch.sh`); assert no `auto-pre-agent-*` stash is created and no plan file remains older than `plan_ttl_seconds`.
- Behavior test: simulate a passed preflight + crashed agent (kill -9 mid-flight); assert the plan is cleaned up by the next SessionStart and no stash orphans.
- Behavior test: passed preflight + completed agent → stash created, marker written by SHA (ADR-221), restore consumes it.
- Operator-facing log: when a plan is cleaned up due to blocked preflight, a single advisory line is emitted, no warnings/errors.

## Implementation slices

1. `manifests/pre-agent-snapshot.yaml` — declare the two-phase pattern, hook ordering, plan TTL, orphan policy.
2. Refactor `pre-agent-snapshot.sh`:
   - Phase 1: write plan file; do NOT call `git stash push`.
   - For ADR-099 copy-on-untracked: untracked-copy step still runs (non-git mutation; safe).
3. New hook `hooks/agent-launch-confirmed.sh` (or PreToolUse-late variant guarded by `validation-lock.sh`):
   - Reads plan, calls `git stash push` with the plan's file list.
   - Resolves SHA per ADR-221.
   - Writes v2 marker.
4. Update `post-agent-snapshot-restore.sh`:
   - Tolerate plan-without-marker (silent cleanup).
   - Apply by SHA.
5. SessionStart sweep (`hooks/session-start-stash-reapply.sh` extended):
   - Sweep plans older than `plan_ttl_seconds` with no marker; delete.
   - Sweep markers older than retention policy with no live agent (ADR-200 hook).
6. CI audit test `tests/audit/test_pre_agent_hook_ordering.py`.
7. Unit tests for plan-builder, plan-consumer, plan-TTL-sweep.
8. Behavior tests for the four scenarios (blocked-preflight, crashed-agent, completed-agent, late-launch-within-TTL).
9. Operator runbook update `docs/runbooks/agent-snapshot-recovery.md` — describe two-phase, add troubleshooting for "I see a plan but no marker" (= preflight blocked; expected).
10. Migration: one-release-cycle legacy reader (piggyback on ADR-221's legacy path).

## Implementation status (2026-05-07)

Slices 1–8 are implemented as a tactical mitigation while ADR-223 worktree-per-write-agent replaces operator-worktree auto-stash over time:

- `manifests/pre-agent-snapshot.yaml` declares the two-phase contract and ordering invariants.
- `hooks/pre-agent-snapshot.sh` now performs Phase 1 planning only in non-legacy mode: it copies untracked files and writes `.cognitive-os/runtime/pre-agent-plan-<agent_id>.json` without calling `git stash`.
- `hooks/agent-launch-confirmed.sh` performs Phase 2 at the end of the `PreToolUse:Agent` chain: it refuses without a plan, stashes only planned tracked files, records stash SHA per ADR-221, writes the v2 marker, and deletes the plan.
- `hooks/post-agent-snapshot-restore.sh` treats plan-without-marker as normal blocked/aborted launch cleanup and exits without scanning for fallback stashes.
- `hooks/session-start-stash-reapply.sh` sweeps stale uncommitted plan files using the same 300s TTL declared in the manifest.
- `scripts/_lib/settings-driver-claude-code.sh`, `.claude/settings.json`, `cognitive-os.yaml`, and `manifests/hook-quality.yaml` register `agent-launch-confirmed.sh` last in the `PreToolUse:Agent` group.
- Tests cover unit, audit, and behavior lanes: `tests/unit/test_pre_agent_two_phase.py`, `tests/audit/test_pre_agent_hook_ordering.py`, and `tests/behavior/test_pre_agent_blocked_preflight_no_orphan.py`.

Remaining/deprecated path: `COS_LEGACY_SNAPSHOT=1` still uses old one-phase stash semantics by explicit opt-in only. The long-term replacement remains ADR-223 worktree-per-write-agent; ADR-222 exists to make the legacy operator-worktree lane stop orphaning stashes while that migration proceeds.

## Open questions

- Does Claude Code expose a "confirmed launch" event we can hook? Initial investigation: not directly; the closest signal is the first tool-use the subagent emits, which is too late. Likely we'll use the lock-fallback for Claude Code and any harness without explicit launch signaling.
- Should the plan file include the *expected* tool-use IDs / agent name so the restore hook can correlate with the actual invocation? Initial answer: yes, low cost, high diagnostic value. Add to v2 marker schema (extends ADR-221 v2 schema).
- Should `dispatch-gate` (the validation-mode lock) be promoted to a first-class concept in cognitive-os.yaml (e.g., `orchestration.dispatch_gate.enabled`)? Initial answer: defer; current opt-in via env vars suffices until we have a second consumer.
- Coordination with ADR-203 (subagent capability contract) — the contract's preflight phase is the natural place for "Phase 1 plan" if we converge on a single subagent-launch primitive. Tracked as a follow-up.
- Coordination with ADR-211 (service mode readiness) — service mode invocation paths must NOT call `pre-agent-snapshot.sh` at all. ADR-099 already disables under `COS_VALIDATION_MODE`; service mode should set the equivalent flag. Verify in the service-mode integration test.
