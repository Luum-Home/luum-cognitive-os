# ADR-108 — Concurrent Agent Safety Layer

<!-- SCOPE: OS -->

**Status**: Proposed
**Date**: 2026-05-02
**Author**: Matias Nahuel Améndola + Cognitive OS
**Related**: ADR-088 (provenance markers), ADR-089 (multi-session git coordination), ADR-098 (multi-agent file coordination), ADR-105 (bilateral claim verification), ADR-106 (multi-session safety primitives), [Concurrent Agent Safety Master](../architecture/concurrent-agent-safety-master.md), [Concurrent Agent Scenario Test Matrix](../architecture/concurrent-agent-scenario-test-matrix.md), [Concurrent Agent Safety Testbed Plan](../../.cognitive-os/plans/architecture/concurrent-agent-safety-testbed-plan.md)

## Status

Proposed. This ADR decides the layer and invariants. Implementation is tracked in the testbed plan and must be proven by automated tests, not manual checks.

## Context

Cognitive OS is expected to support multiple agents, harness sessions, worktrees, and background hooks working at the same time. That concurrency is valuable, but it creates distributed-systems failure modes inside a local repository:

- two agents can edit the same file and silently overwrite each other;
- two sessions can update the same plan and create false shared state;
- an auto-pre-agent stash can hide uncommitted work from later sessions;
- commits can land without identifying which session produced them;
- a high-stakes claim can be accepted after only the optimistic half was checked;
- agents can mutate different files that represent the same logical primitive.

ADR-089 covers git-index coordination. ADR-098 covers file-level edit locks. ADR-105 covers bilateral claim verification. ADR-106 covers stash leaks, plan locks, provenance, and bilateral orchestration. These are necessary but currently read as separate primitives. The operating system needs a named layer that composes them and requires scenario tests for realistic failures.

## Decision

Cognitive OS owns a **Concurrent Agent Safety Layer**.

The layer's purpose is:

> Permit productive concurrent agent work while preventing silent state corruption, false completion, invisible work loss, and untraceable commits.

This layer is not a single hook. It is a contract composed of primitives, runtime artifacts, and automated scenario tests.

## Required Primitives

### 1. Agent Work Ledger

An append-only ledger of active and completed agent work.

Minimum fields:

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
- produced commits;
- status.

Suggested path:

```text
.cognitive-os/runtime/agent-work-ledger.jsonl
```

### 2. Resource Lease

A logical-resource lock for domains that span multiple files.

Examples:

- `primitive/session-start-hooks`;
- `primitive/auto-rollback`;
- `runtime/settings-projection`;
- `domain/auth`;
- `domain/test-runner`;
- `docs/master-plan`.

Suggested path:

```text
.cognitive-os/runtime/resource-leases/<resource>.lock/
```

### 3. File/Git/Plan Locks

The layer adopts existing and proposed locks:

- file-level locks from ADR-098;
- git-index locks from ADR-089;
- plan-file locks from ADR-106.

These locks must expose holder metadata, stale detection, and conflict response guidance.

### 4. Stash Leak Alarm

Auto-pre-agent stashes must never remain invisible indefinitely. Stash leak detection must warn after a short TTL and block strict dispatch after a longer TTL.

### 5. Claim Verification Registry

High-stakes claim verbs must map to executable bilateral proof commands. ADR-105 defines the policy; this layer requires a registry or helper library that makes the checks reusable.

### 6. Commit Provenance

Concurrent work must be traceable through commit metadata. Commits produced under a Cognitive OS session should carry session provenance such as `X-COS-Session`.

### 7. Approval and Override Ledger

Bypasses, overrides, and human approvals must be recorded as durable runtime artifacts.

### 8. Cross-Session Reconciler

A read-only reconciler should compare active sessions, ledgers, locks, stashes, plans, and commits to surface divergence.

Future command:

```bash
cos doctor concurrency
```

Shell fallback may land first:

```bash
bash scripts/cos-doctor-concurrency.sh
```

## Invariants

1. Concurrency is allowed, but silent damage is not.
2. Prompt-only coordination is insufficient; safety must be enforced or detected at runtime.
3. Every lock conflict must provide enough metadata for the blocked agent to park, retry, negotiate, or escalate.
4. High-stakes plan closure requires bilateral proof.
5. Hidden work, especially stashes and parked edits, must be surfaced automatically.
6. Commits from concurrent sessions must be attributable.
7. Bypasses must be auditable.
8. Every primitive in this layer must have an automated scenario test.
9. Manual verification does not satisfy the safety contract.

## Mandatory Automated Scenarios

The first implementation slice is fixed:

1. Two agents edit the same file.
2. False done in plan.
3. Stash leak.

The scenario matrix is canonicalized in [Concurrent Agent Scenario Test Matrix](../architecture/concurrent-agent-scenario-test-matrix.md).

## Consequences

### Positive

- Concurrent agent workflows remain possible.
- State corruption becomes visible or blocked.
- False-done propagation is harder to commit.
- Safety claims become testable through reproducible scenarios.
- Future doctors can report real concurrency posture instead of isolated hook status.

### Negative

- More runtime state is created under `.cognitive-os/runtime/`.
- Some workflows will block or park instead of racing ahead.
- Tests require scratch repos, subprocess simulation, and careful isolation.

### Neutral

- This ADR does not require CRDT/OT. Locking plus worktrees remains the right default for current 2-4 concurrent agent workflows. CRDT/OT can be reconsidered if same-file contention becomes frequent or concurrent writers exceed the existing ADR-098 threshold.

## Alternatives Rejected

| Alternative | Why rejected |
|---|---|
| Ban concurrent agents | Discards real productivity gains and conflicts with the intended workflow. |
| Trust agents to coordinate via prompts | The repo has already seen prompt-level scope guards fail. |
| Rely only on git conflicts | Git does not detect logical conflicts, false plan state, or hidden stashes. |
| Manual operator review only | Too slow and unreliable; the user explicitly requires automatic proof. |
| Build CRDT first | Overbuilt for current scale; lock/ledger/reconciler primitives are simpler and testable now. |

## Verification

This ADR is considered implemented only when these commands exist and pass:

```bash
python3 -m pytest tests/integration/test_concurrent_agent_same_file.py -v
python3 -m pytest tests/behavior/test_plan_false_done_gate.py -v
python3 -m pytest tests/behavior/test_stash_leak_alarm.py -v
```

A later slice should add:

```bash
bash scripts/cos-doctor-concurrency.sh --strict
python3 -m pytest tests/behavior/test_cos_doctor_concurrency.py -v
```

## References

- [Concurrent Agent Safety Master](../architecture/concurrent-agent-safety-master.md)
- [Concurrent Agent Scenario Test Matrix](../architecture/concurrent-agent-scenario-test-matrix.md)
- [Concurrent Agent Safety Testbed Plan](../../.cognitive-os/plans/architecture/concurrent-agent-safety-testbed-plan.md)
- ADR-089 — Multi-Session Git Coordination
- ADR-098 — Multi-Agent File Coordination
- ADR-105 — Bilateral Claim Verification Contract
- ADR-106 — Multi-Session Safety Primitives
