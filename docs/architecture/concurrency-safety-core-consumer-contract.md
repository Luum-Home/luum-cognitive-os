# Concurrent-Agent Safety Core/Consumer Contract

## Purpose

This contract defines how Cognitive OS protects concurrent agent work in the core and how consuming projects project their own risk profile into that protection layer.

## Core-owned agentic primitives

| Primitive | Core path | Contract |
|---|---|---|
| `edit-coop` | `scripts/edit-coop.sh` | Detect concurrent same-file edits before an agent overwrites another agent's scope. |
| `git-coop` | `scripts/git-coop.sh` | Inspect git state before destructive branch/history operations. |
| `stash-leak-alarm` | `scripts/stash-leak-alarm.sh` | Warn/block on stale hidden work. |
| `plan-claim verifier` | `scripts/verify_plan_claims.py` | Reject false-done claims without bilateral proof. |
| `preserve-branch doctor` | `scripts/cos-doctor-preserve.sh` | Detect preserve branches without manifest, with mixed scope, or already integrated. |
| `concurrency doctor` | `scripts/cos-doctor-concurrency.sh` | Prove the local safety surface exists and compiles. |
| `work inventory doctor` | `scripts/cos-doctor-work-inventory.sh` | Produce a projectable closure checklist across dirty state, preserve branches, linked worktrees, and stashes. |
| `worktree triage doctor` | `scripts/cos-worktree-triage.sh` | Compare one linked worktree to a target branch, identify already-applied vs still-to-port commits, surface dirty/stash blockers, and mark removal safe only after proof. |
| `approval ledger` | `scripts/approval_ledger.py` | Record high-risk approvals with verification and rollback evidence. |
| `resource lease` | `scripts/resource_lease.py` | Provide named, expiring cooperative leases for critical domains. |
| `task claim ledger` | `scripts/claim_task.py` + `lib/task_claim_ledger.py` | Acquire an expiring task-level claim before concurrent agents start the same logical work; records `task_id`, `session_id`, `agent_id`, `scope`, `expected_files`, and fingerprint. |
| `agent work ledger` | `scripts/agent_work_ledger.py` | Record started/completed/aborted work scopes across agents. |
| `cross-session reconciler` | `scripts/cross_session_reconciler.py` | Merge runtime safety state into one recovery report. |
| `session filesystem reaper` | `hooks/_lib/session-fs-reap.sh` + `lib/session_lifecycle.py` | Archive stale clean session directories and delete only archived sessions beyond retention. |

## Consumer projection

Consumers configure policy through `concurrency_safety` in `cognitive-os.yaml`. The SO core remains responsible for implementation; consumers provide phase and risk context.

## Test lanes

| Lane | Purpose | Representative tests |
|---|---|---|
| Unit | Config projection and defaults | `tests/unit/test_concurrency_safety_config.py` |
| Behavior | Primitive command behavior | `tests/behavior/test_concurrency_safety_ledgers.py`, `tests/behavior/test_cos_work_inventory.py`, `tests/behavior/test_cos_worktree_triage.py` |
| Integration | Real same-file accident simulation | `tests/integration/test_concurrent_agent_same_file.py` |
| Chaos/scenario | Recovery report over mixed runtime state | `tests/chaos/test_cross_session_reconciler.py` |

## Expected behavior

- If two agents attempt the same logical task, the task claim ledger must let the first live claim win and return holder metadata to the second agent.
- If two agents target the same file, the edit cooperation path must surface the conflict.
- If an agent claims done without proof, the plan verifier must fail.
- If hidden work ages past thresholds, the stash leak alarm must warn or block.
- If a critical resource is leased, a second agent must be blocked until release or expiry.
- If sessions are interrupted, the cross-session reconciler must reveal active leases, active work, approvals, edit locks, and preserve branch status.
- Before preserved work is deleted, the work inventory doctor must check the current worktree, linked worktrees, stashes, and preserve branches in one checklist.
- Before a linked worktree is removed, the worktree triage doctor must prove which commits are already applied, which still need porting, and whether dirty files or stashes block cleanup.
- Session filesystem artifacts are cleaned by archive-first lifecycle decisions; absence from `active-sessions.json` is not enough to delete.
