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
| `approval ledger` | `scripts/approval_ledger.py` | Record high-risk approvals with verification and rollback evidence. |
| `resource lease` | `scripts/resource_lease.py` | Provide named, expiring cooperative leases for critical domains. |
| `agent work ledger` | `scripts/agent_work_ledger.py` | Record started/completed/aborted work scopes across agents. |
| `cross-session reconciler` | `scripts/cross_session_reconciler.py` | Merge runtime safety state into one recovery report. |

## Consumer projection

Consumers configure policy through `concurrency_safety` in `cognitive-os.yaml`. The SO core remains responsible for implementation; consumers provide phase and risk context.

## Test lanes

| Lane | Purpose | Representative tests |
|---|---|---|
| Unit | Config projection and defaults | `tests/unit/test_concurrency_safety_config.py` |
| Behavior | Primitive command behavior | `tests/behavior/test_concurrency_safety_ledgers.py` |
| Integration | Real same-file accident simulation | `tests/integration/test_concurrent_agent_same_file.py` |
| Chaos/scenario | Recovery report over mixed runtime state | `tests/chaos/test_cross_session_reconciler.py` |

## Expected behavior

- If two agents target the same file, the edit cooperation path must surface the conflict.
- If an agent claims done without proof, the plan verifier must fail.
- If hidden work ages past thresholds, the stash leak alarm must warn or block.
- If a critical resource is leased, a second agent must be blocked until release or expiry.
- If sessions are interrupted, the cross-session reconciler must reveal active leases, active work, approvals, edit locks, and preserve branch status.
