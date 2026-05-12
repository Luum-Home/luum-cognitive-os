# Concurrent Agent Safety Master Document

> Status: research master document
> Updated: 2026-05-02
> Scope: Cognitive OS primitives and automated scenario tests for simultaneous agents and sessions
> Related ADRs: [ADR-089](../adrs/ADR-089-multi-session-git-coordination.md), [ADR-098](../adrs/ADR-098-multi-agent-file-coordination.md), [ADR-105](../adrs/ADR-105-claim-verification-contract.md), [ADR-106](../adrs/ADR-106-multi-session-safety-primitives.md)
> Execution plan: [Concurrent Agent Safety Testbed Plan](../../.cognitive-os/plans/architecture/concurrent-agent-safety-testbed-plan.md)
> Scenario matrix: [Concurrent Agent Scenario Test Matrix](concurrent-agent-scenario-test-matrix.md)
> Decision record: [ADR-108 — Concurrent Agent Safety Layer](../adrs/ADR-108-concurrent-agent-safety-layer.md)

## Executive Summary

Cognitive OS should support multiple agents and multiple IDE/harness sessions working at the same time. Blocking all concurrency would waste the main advantage of agentic workflows. The safety target is different:

> Allow concurrent agents, but make silent damage structurally impossible.

The current repository already contains several important primitives: git-index coordination, file-level edit locks, bilateral claim verification, provenance markers, and multi-session safety proposals. These pieces need a unifying master model and an automated scenario testbed that reproduces realistic failures before users encounter them.

Manual verification is not enough. Every safety claim in this document must eventually be backed by an automated test, preferably in behavior, integration, or chaos lanes depending on cost and isolation needs.

## Problem Statement

When agents work simultaneously, ordinary local assumptions break:

- one agent may overwrite another agent's file edits;
- one session may commit while another session is still validating;
- a plan checkbox may become false shared state;
- auto-snapshots or stashes may hide work from later sessions;
- commit history may not reveal which session produced which change;
- two agents may work on different files but the same logical primitive;
- a report may say “done” while only half of the predicate was checked.

These are not model-intelligence failures only. They are distributed-systems failures: shared mutable state, partial truth, stale reads, missing locks, weak provenance, and no reconciliation loop.

## Design Principle

If a failure mode can happen under realistic agent concurrency, it should have:

1. a primitive that prevents, detects, or reconciles it;
2. a durable runtime artifact showing what happened;
3. an automated scenario test that reproduces the failure and proves the primitive works.

## Existing Building Blocks

| Area | Existing document | Current role |
|---|---|---|
| Git index coordination | ADR-089 | Serializes dangerous git index operations across sessions. |
| File edit coordination | ADR-098 | Uses file-level locks and conflict metadata to prevent silent overwrite. |
| Claim verification | ADR-105 | Defines bilateral proof for high-stakes claims such as archived, removed, wired, registered, and done. |
| Multi-session safety | ADR-106 | Defines stash leak alarm, plan file lock, commit provenance, and orchestrator bilateral gate. |
| Startup circuit breaker | ADR-104 | Protects against startup/session storms. |
| Provenance markers | ADR-088 | Makes origin/session traceable through commit metadata. |

## Missing Unified Layer

The missing layer is an explicit **Concurrent Agent Safety Layer**. It should not replace ADR-089, ADR-098, ADR-105, or ADR-106. It should compose them into one model:

```text
Agent intent
  -> declared scope
  -> resource/primitive lease
  -> file/git/plan locks
  -> execution
  -> claim verification
  -> provenance
  -> reconciliation
  -> automated scenario proof
```

## Candidate Primitives

### Primitive 1 — Agent Work Ledger

A central append-only record of agent work units.

Required fields:

- session id;
- agent id;
- harness;
- declared task;
- declared scope;
- permission profile;
- touched files;
- tests run;
- claims made;
- claims verified;
- commit hashes produced;
- status.

Potential location:

```text
.cognitive-os/runtime/agent-work-ledger.jsonl
```

Purpose: make concurrent activity observable and queryable.

### Primitive 2 — Resource Lease

A lock for logical resources, not just files.

Examples:

- `runtime/settings-projection`;
- `primitive/hooks/session-start`;
- `primitive/auto-rollback`;
- `domain/auth`;
- `domain/test-runner`;
- `docs/master-plan`.

Purpose: two agents can edit different files but still collide logically. Resource leases catch domain-level collisions.

Potential location:

```text
.cognitive-os/runtime/resource-leases/<resource>.lock/
```

### Primitive 3 — Cross-Session Reconciler

A read-only process that compares active sessions, worktrees, plans, ledgers, locks, stashes, and commits.

Responsibilities:

- detect stale locks;
- detect stash leaks;
- detect divergent plan checkboxes;
- detect commits without provenance;
- detect work claimed done without verification;
- detect active sessions touching the same logical resource.

Potential command:

```bash
cos doctor concurrency
```

or initial fallback:

```bash
bash scripts/cos-doctor-concurrency.sh
```

### Primitive 4 — Claim Verification Registry

A registry mapping high-stakes claim verbs to automated proof commands.

Examples:

| Claim | Required proof |
|---|---|
| archived | archive present AND original absent AND config refs absent |
| removed | path absent AND config refs absent |
| wired | registration exists AND target exists/resolves |
| done | every acceptance criterion command passed |

Purpose: make ADR-105 executable instead of relying on every orchestrator to remember the right inverse check.

### Primitive 5 — Approval and Override Ledger

A durable audit artifact for bypasses and approvals.

Purpose: if an agent bypasses a lock, approval gate, or destructive blocker, the event must be visible and reviewable.

Potential location:

```text
.cognitive-os/runtime/approvals/*.json
.cognitive-os/runtime/overrides.jsonl
```

## Automated Scenario Matrix

The testbed starts with three mandatory scenarios in this order. All must be automated. Manual proof is not sufficient.

| Priority | Scenario | Failure reproduced | Expected automated proof | Candidate test |
|---|---|---|---|---|
| 1 | Two agents edit the same file | Silent overwrite / last writer wins | second writer is blocked or parked; first edit survives | `tests/integration/test_concurrent_agent_same_file.py` |
| 2 | False done in plan | `[x]` becomes shared false truth | plan closure without bilateral proof is rejected/detected | `tests/behavior/test_plan_false_done_gate.py` |
| 3 | Stash leak | hidden auto-pre-agent stash persists across sessions | alarm appears; stale leak blocks dispatch in strict mode | `tests/behavior/test_stash_leak_alarm.py` |

Future scenarios:

| Scenario | Failure reproduced | Expected behavior |
|---|---|---|
| Concurrent commits | commits from different sessions become indistinguishable | each commit carries `X-COS-Session`; missing provenance fails. |
| Same logical primitive, different files | two agents mutate one primitive through different files | resource lease conflict is reported. |
| Out-of-scope edit | agent edits outside declared scope | post-agent verifier rejects or parks the change. |
| Approval bypass | agent uses override flag | override ledger records actor, reason, scope, and timestamp. |
| Cross-worktree divergence | two worktrees close conflicting plan state | reconciler reports divergence before merge. |
| Delete/recreate repair | small fix becomes destructive rewrite | destructive/high-blast gate blocks or requires approval. |

## Scenario 1 — Two Agents Edit the Same File

### Goal

Prove that concurrent writers cannot silently overwrite the same file.

### Automated setup

1. Create a temporary git repo or isolated scratch project.
2. Copy or invoke `scripts/edit-coop.sh` and the edit-lock hook contract.
3. Simulate Session A acquiring edit ownership of `target.txt`.
4. Simulate Session B attempting to acquire/write the same file.
5. Assert Session B receives structured conflict output.
6. Assert file contents are not overwritten by Session B.
7. Assert lock metadata includes holder session, target file, and recommended response.

### Acceptance Criteria

```bash
python3 -m pytest tests/integration/test_concurrent_agent_same_file.py -v
```

The test must run without real concurrent humans. It should simulate sessions via environment variables and subprocesses.

## Scenario 2 — False Done In Plan

### Goal

Prove that a plan checkbox cannot become accepted truth for a high-stakes claim unless bilateral proof is attached or independently produced.

### Automated setup

1. Create a scratch plan with `[ ] Archive hook X`.
2. Create the optimistic partial only: archive copy exists.
3. Keep the original file or config reference alive.
4. Attempt `[ ]` -> `[x]` transition without `(verified: ...)` proof.
5. Run the gate/checker.
6. Assert failure and diagnostic explaining the missing inverse proof.
7. Add valid proof and assert pass.

### Acceptance Criteria

```bash
python3 -m pytest tests/behavior/test_plan_false_done_gate.py -v
```

No manual review counts. The test must create both failing and passing fixtures.

## Scenario 3 — Stash Leak

### Goal

Prove that hidden auto-pre-agent stashes become visible and eventually block unsafe continuation.

### Automated setup

1. Create a scratch git repo.
2. Add a tracked file and dirty change.
3. Create a stash with message matching `auto-pre-agent-*`.
4. Run stash leak detector with TTL forced to zero.
5. Assert `.cognitive-os/runtime/stash-leak-alarm.json` exists.
6. Run again with block TTL forced to zero.
7. Assert blocking result and actionable instructions.

### Acceptance Criteria

```bash
python3 -m pytest tests/behavior/test_stash_leak_alarm.py -v
```

The test must not depend on waiting real time. TTLs are controlled via environment variables.

## Test Lane Placement

| Test type | Location | Why |
|---|---|---|
| Unit tests for lock/ledger parsers | `tests/unit/` | Fast deterministic helpers. |
| Behavior tests for gates | `tests/behavior/` | User-visible policy behavior. |
| Integration tests for concurrent subprocesses | `tests/integration/` | Real git and filesystem behavior. |
| Chaos scenarios | `tests/chaos/` | Fault injection, stale PIDs, corrupt locks, clock skew. |

## Implementation Strategy

Do not start with the broadest primitive. Start with the first scenario and let the primitive surface emerge from the test.

Recommended sequence:

1. Scenario matrix as this master document.
2. ADR for the Concurrent Agent Safety Layer.
3. Implement Scenario 1: two agents edit the same file.
4. Implement Scenario 2: false done in plan.
5. Implement Scenario 3: stash leak.
6. Add `cos doctor concurrency` once at least the three scenarios are automated.

## Definition of Done

- The three mandatory scenarios run automatically in pytest.
- Each scenario fails against an unsafe fixture and passes against the protected primitive.
- Runtime artifacts are produced in `.cognitive-os/runtime/` or scratch equivalents.
- No scenario depends on manual operator judgment.
- The ADR references this master document and the testbed plan.
- The master plan checklist tracks this work as product safety, not optional research.
