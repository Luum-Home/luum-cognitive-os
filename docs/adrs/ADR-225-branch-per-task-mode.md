# ADR-225 — Branch-Per-Task Mode

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–B implemented (2026-05-07)  
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

Read-only agents are exempt. Write/cloud/detached agents are blocked at prelaunch when they explicitly declare a write/cloud/detached lifecycle lane, or when `COS_BRANCH_PER_TASK_ENFORCE=1` is set. Generic legacy Agent launches remain advisory until ADR-223 is fully default-on.

## Implementation status (2026-05-07)

Implemented Slice A:

- `packages/agent-lifecycle/lib/branch_task_policy.py` computes canonical branch names and evaluates current branch vs task id.
- `lib/branch_task_policy.py` package symlink.
- `scripts/cos-branch-task-check` CLI emits JSON and supports `--strict` exit 2.
- `manifests/branch-per-task.yaml` declares observe mode and invariants.
- Unit, audit, and behavior tests cover slugging, pass/block verdicts, manifest, and CLI strict behavior.

Implemented Slice B:

- `agent-prelaunch.sh` enforces `cos-branch-task-check --strict` for explicit write/cloud/detached lifecycle launches.
- `COS_BRANCH_PER_TASK_ENFORCE=1` forces enforcement for all non-read-only Agent launches.
- `COS_SKIP_BRANCH_PER_TASK_GATE=1` is the explicit operator bypass.

Implemented 2026-05-07:

- Detached-agent `--prepare-worktree` now defaults to `codex/task/<task>` branch prefixes, aligning ADR-235 with branch-per-task.
- ADR-223 `prepare_agent_worktree(..., branch_prefix=...)` supports branch migration/auto-branching callers without prompt-derived branch names.

Not implemented yet:

- Automatic branch migration for existing worktrees.
- ADR-235 detached daemon auto-branching beyond explicit ADR-223 worktree preparation.

## Hard rules

- Branch names derive from task IDs, not raw prompts.
- Read-only agents are exempt.
- Enforcement is prelaunch-only and does not create or mutate branches.
- Strict mode is available for readiness/smoke tests and future prelaunch gates.

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on conversation history.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
