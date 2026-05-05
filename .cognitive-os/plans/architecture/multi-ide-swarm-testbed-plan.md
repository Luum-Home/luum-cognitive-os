# Multi-IDE Swarm Safety Testbed Plan

> Status: implementation plan  
> Updated: 2026-05-02  
> Related: [ADR-118](../adrs/ADR-118-multi-ide-swarm-testbed.md)

## Goal

Prove that Cognitive OS can run multiple IDE sessions and agents with bounded
race risk. The testbed should reproduce incidents before adding optimistic
claims about safety.

## Phase 1 — Blocking primitives

1. Add atomic task claims with `scripts/claim_task.py`.
2. Exercise existing file-lock behavior.
3. Exercise existing resource leases for logical domains.
4. Exercise destructive git blocking for rebase/reset-over-WIP.

## Phase 2 — Harness parity

1. Verify Claude and Codex share the portable Bash gates.
2. Mark Claude-only `Agent` and `Edit|Write` coverage as an explicit Codex gap.
3. Require the memory lifecycle doctor for each supported harness.
4. Provide governed Codex fallbacks until hook parity exists:
   - `scripts/cos-governed-agent.sh` for task-claim/work-ledger guarded agent commands.
   - `scripts/cos-governed-edit.sh` for edit-lock guarded file mutations.

## Phase 3 — Reconciliation

1. Use watermark/reaper to mark pending tasks completed by another session.
2. Extend the status composer with task-claim visibility.
3. Promote warnings to blockers only after tests prove low false-positive rates.

## Acceptance Criteria

```bash
python3 -m pytest tests/chaos/test_multi_ide_swarm_safety.py -q
```

The lane passes without mutating the real repository's stash, branches, remotes,
or worktree.
## Concrete Slice Backlog

Bounded ADR-118 slices are tracked in `.cognitive-os/plans/architecture/adr-118-121-123-slices.md` under `ADR-118-S*`.
