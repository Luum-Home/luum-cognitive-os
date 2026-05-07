# ADR-225 — Branch-Per-Task Mode

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)  
**Date**: 2026-05-07  
**Related**: ADR-219 (work ownership), ADR-220 (worktree divergence), ADR-223 (worktree-per-write-agent), ADR-233 (agent-team file IPC), ADR-235 (detached agent daemon)

---

## Context

Worktree-per-write-agent isolates filesystem mutations, but branch identity still needs a stable operator-visible contract. Without a branch-per-task policy, detached/cloud/write agents can create worktrees whose branch names do not map back to the task ledger, making WIP ownership hard to audit.

## Decision

Define a canonical branch-per-task policy:

```text
codex/task/<task-id-slug>
```

Read-only agents are exempt. Write/cloud/detached agents should eventually be blocked if they are not on their canonical task branch. Slice A ships observe/check tooling only; enforcement waits until ADR-223 becomes default-on for write agents.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/branch_task_policy.py` computes canonical branch names and evaluates current branch vs task id.
- `lib/branch_task_policy.py` package symlink.
- `scripts/cos-branch-task-check` CLI emits JSON and supports `--strict` exit 2.
- `manifests/branch-per-task.yaml` declares observe mode and invariants.
- Unit, audit, and behavior tests cover slugging, pass/block verdicts, manifest, and CLI strict behavior.

Not implemented yet:

- Default prelaunch blocking.
- Automatic branch migration for existing worktrees.
- Integration with ADR-233 task claims and ADR-235 detached daemon.

## Hard rules

- Branch names derive from task IDs, not raw prompts.
- Read-only agents are exempt.
- Slice A is observe/check only; no branch creation/mutation.
- Strict mode is available for readiness/smoke tests and future prelaunch gates.
