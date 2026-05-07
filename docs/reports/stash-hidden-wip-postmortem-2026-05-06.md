# Post-Mortem — Hidden WIP in Auto Pre-Agent Stash

**Date**: 2026-05-06
**Severity**: P1 operator-trust / data-preservation
**Status**: Reopened — ADR-213 fixed one ordering bug, but did not eliminate the failure class. Superseded by ADR-221 / ADR-222 and the multi-agent prior-art research.

## Summary

License-switch WIP appeared to be missing from progressive commits. It was not
lost. It had been moved into duplicate `auto-pre-agent-*` stashes by the
pre-agent snapshot path before a later Agent launch actually completed.

The first fix, ADR-213, moved `agent-prelaunch.sh` before
`pre-agent-snapshot.sh`. That was necessary, but not sufficient. Local forensics
later showed `.claude/settings.json` still runs multiple PreToolUse-Agent hooks
after `pre-agent-snapshot.sh`, including hooks that can block. If any later hook
blocks, the Agent tool never launches and the normal PostToolUse restore path
still does not fire.

The durable root cause is therefore not a single bad ordering pair. It is this
architectural violation:

> COS mutates git state during launch preparation before launch success is a
> guaranteed fact.

That is why the same class can recur across harnesses, profiles, or future hooks.

## Impact

- Operator could not trust whether progressive work had been committed,
  preserved, stashed, or silently hidden.
- The working tree could look clean even though meaningful product/legal WIP
  existed only in stash.
- Later stale-stash guards correctly noticed dangerous residue, but those guards
  were downstream symptoms: COS created hidden WIP first, then blocked itself on
  its own artifact.
- The incident undermines public-release trust because a repo can be clean at
  HEAD while history/stashes/branches still contain sensitive or unreconciled
  state.

## Timeline

1. License-switch files were modified in the working tree.
2. A later Agent launch began.
3. `pre-agent-snapshot.sh` created an `auto-pre-agent-*` stash.
4. A launch gate blocked the Agent before execution completed.
5. Since Agent never launched successfully, PostToolUse restore did not run.
6. The WIP remained only in stash until manual forensics preserved it on
   `codex/stash-license-review-20260506`.
7. ADR-213 moved `agent-prelaunch.sh` before `pre-agent-snapshot.sh`.
8. Follow-up local audit found remaining blockers after `pre-agent-snapshot.sh`,
   so the class was reopened.
9. The prior-art research across 79 sources / 52 domains showed that mature
   agent harnesses generally isolate write-capable agents with worktrees,
   containers/VMs/microVMs, or shadow-state — not by stashing the operator's
   working tree during launch.

## Root cause

The original bad pair was:

```text
pre-agent-snapshot.sh  # mutates stash
agent-prelaunch.sh     # may block launch
```

ADR-213 corrected that pair:

```text
agent-prelaunch.sh     # blocking launch admission
pre-agent-snapshot.sh  # stash/copy snapshot only after that admission hook
```

But the stronger invariant was still missing:

```text
all blocking launch gates must complete
agent launch must be confirmed
only then may COS create a git-state mutation for pre-agent preservation
```

The active hook window still had later blockers after `pre-agent-snapshot.sh`.
That means mutation-before-admission survived in a different shape.

## Contributing factors

- Snapshot markers stored mutable refs like `stash@{0}` instead of immutable stash
  SHAs. New stashes can shift positions and make old markers point at different
  state.
- Ownership/liveness is fragmented across stashes, worktrees, claims, edit locks,
  heartbeats, branch locks, process hints, and preserve branches. COS can fail
  closed but cannot yet prove path ownership end-to-end.
- Agents over-reported certainty from preservation artifacts. A preserved branch
  or stash proves data was copied; it does not prove no live agent/worktree still
  owns that path.
- The implementation was trying to be harness-agnostic while relying on a
  harness-specific lifecycle assumption: that a PostToolUse restore event would
  always follow a PreToolUse snapshot.

## Corrective decisions

1. **ADR-221 — Stash Ref by SHA, Not by Position**
   Any remaining stash consumer must identify stashes by immutable SHA, not
   `stash@{N}`.

2. **ADR-222 — Pre-Agent Stash Deferred Until Agent Launch Confirmed**
   Short-term correctness: create a non-git-mutating plan during PreToolUse;
   commit the stash only after launch is confirmed or after an end-of-preflight
   lock proves all blockers passed.

3. **Agent-lifecycle reconstruction**
   Long-term direction from the 79-source prior-art research: replace
   auto-pre-agent stash with worktree-per-write-agent plus optional shadow-state
   snapshots. The operator's working tree should be invariant under Agent launch.

4. **Ownership/liveness truth source**
   Build `cos work ownership --paths ...` into a real source of truth by joining
   worktrees, stashes, dirty files, preserve branches, edit locks, task claims,
   heartbeats, process liveness, and branch locks.

## Non-fixes explicitly rejected

- Do not solve this by making stash cleanup more aggressive. Cleanup reduces
  residue after the fact; it does not prevent hidden WIP.
- Do not rely on comments in hook headers as the ordering proof. The invariant
  must be asserted by tests against every projected harness profile.
- Do not use `stash@{0}` as identity in any new code.
- Do not treat “agent says it preserved the branch” as proof that no live owner
  remains.

## Preventive rule

Any hook that mutates stash, hides WIP, deletes files, rewrites working-tree
state, or changes branch/worktree ownership must run only after all blocking
admission gates have passed and launch is confirmed, unless it has explicit
restore-on-block semantics tested against the no-PostToolUse path.

## Regression tests required

Existing tests proved the old `agent-prelaunch.sh` ordering bug. They did not
cover late blockers after snapshot. The missing smoke/automated tests are:

1. Parse every projected Agent PreToolUse hook list and assert no blocking hook
   runs after `pre-agent-snapshot.sh` in one-phase mode.
2. Simulate a late blocker after `pre-agent-snapshot.sh`; assert no
   `auto-pre-agent-*` stash is created, or that it is synchronously restored in
   the same failed launch path.
3. Plan-only test for ADR-222: Phase 1 leaves `git stash list` byte-identical.
4. Commit-only test for ADR-222: Phase 2 refuses to run without a plan and a
   confirmed-launch signal/lock.
5. Restore drift test for ADR-221: create a stash, record SHA, push additional
   stashes, then restore the original by SHA.
6. SessionStart cleanup test: stale plan-without-marker is deleted without
   creating or dropping a stash.
7. Cross-harness projection test: Claude, Codex, OpenCode/OpenClaw-style
   profiles all satisfy the same no-hidden-WIP invariant.

## Evidence links

- `docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`
- `docs/adrs/ADR-221-stash-ref-by-sha-not-by-position.md`
- `docs/adrs/ADR-222-pre-agent-stash-defer-until-launch-confirmed.md`
