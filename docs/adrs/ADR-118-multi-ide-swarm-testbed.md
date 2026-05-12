---
adr: 118
title: Multi-IDE Swarm Safety Testbed
status: accepted
implementation_status: partial
date: '2026-05-02'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit pending/deferred/planned scope
partial_remaining: Keep these as late contract tests only.** Rejected because registry/projection drift should be blocked before commit, not discovered after a long laptop run.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-118 — Multi-IDE Swarm Safety Testbed

<!-- SCOPE: OS -->

**Status**: Accepted — acceptance testbed  
**Date**: 2026-05-02  
**Related**: ADR-089, ADR-098, ADR-105, ADR-106, ADR-108, ADR-116

## Status

Accepted (2026-05-02). This is the automated acceptance-test umbrella for ADR-116 and its transactional coordination rollout.

## Context

Cognitive OS now has real concurrent-agent primitives: file locks, destructive
git blockers, resource leases, agent work ledgers, approval ledgers, memory
lifecycle hooks, session branches, and watermark reaping. The remaining risk is
not absence of primitives; it is false confidence that these primitives compose
across multiple IDEs and sessions.

The real failures to reproduce are race-shaped:

- two agents claim the same task;
- two agents edit the same file;
- two agents work on the same logical domain through different files;
- one session pulls/rebases/resets over another session's WIP;
- Codex and Claude project different hook surfaces;
- shared memory appears configured but is not doctor-proven;
- one agent completes a task while another still carries it as pending.

## Decision

Cognitive OS maintains a deterministic **multi-IDE swarm safety testbed**. The
testbed simulates agents and IDEs with subprocesses, scratch repositories, and
environment variables. It does not require real concurrent humans and must not
touch the developer's real stash, branches, or worktree.

The first executable surface is:

```bash
python3 -m pytest tests/chaos/test_multi_ide_swarm_safety.py -q
```

## Required Scenarios

| Scenario | Expected behavior | Primitive under test |
|---|---|---|
| Same task race | First claim wins; second live claim exits blocked with holder metadata. | ADR-116 P1.1 |
| Registry/projection drift | Changing `cognitive-os.yaml` requires hook-quality and harness projections to be regenerated and staged. | ADR-081, ADR-114, ADR-116 transactional rollout |
| Same file race | Second writer is blocked/advised and the first edit survives. | ADR-098, ADR-108 |
| Same domain lease | First critical-domain lease wins; competing session is blocked. | ADR-116 P5.2 |
| Direct-main concurrent landing | Merge queue serializes and revalidates against fresh HEAD. | ADR-116 P2.2 |
| Dirty worktree + pull/rebase | `git pull --rebase` over WIP is blocked in agent context. | ADR-099, ADR-106, ADR-117 |
| Agent B fix overwritten | `git reset`/fetch-reset/rebase over WIP is blocked or emits corruption evidence before the fix disappears. | ADR-116 P3.1/P3.2 |
| Cross-IDE parity | Claude/Codex shared gates are proven; known matcher gaps are explicit. | ADR-081, ADR-112, ADR-114 |
| Memory sharing | Portable memory doctor proves both harnesses project/run lifecycle hooks. | ADR-116 P5.1/P5.2 |
| Completed by other agent | Watermark/reaper marks pending work as `completed-by-watermark` or `done-by-other-session`. | ADR-102, ADR-116 P1.4 |

## Initial implementation slice

The first local, laptop-safe slice includes:

- `manifests/multi-ide-swarm-scenarios.yaml` and
  `tests/contracts/test_multi_ide_swarm_scenarios.py` for the ADR-118-S1
  machine-readable scenario contract.

- `scripts/derived_artifact_gate.py` for registry/projection closure.
- `lib/session_bus.py` and `scripts/session_event_bus.py` for append-only coordination events.
- `lib/task_claim_ledger.py` and `scripts/claim_task.py` for atomic task claims.
- `scripts/merge-to-main.sh` for single-writer landing.
- `scripts/orphan_overwrite_detector.py` for corruption evidence after unsafe history movement.

## Consequences

- The SO can claim controlled multi-session parallelism only when this lane
  passes.
- Codex parity gaps remain honest findings until Codex exposes equivalent
  `Agent`/`Edit` hook surfaces or `governed_runner` covers them.
- Task claiming becomes a first-class agentic primitive instead of relying on
  post-launch work ledgers.

## Alternatives rejected

1. **Rely on prose instructions to agents.** Rejected because concurrent agents fail by racing between instructions, not only by misunderstanding them.
2. **Keep these as late contract tests only.** Rejected because registry/projection drift should be blocked before commit, not discovered after a long laptop run.
3. **Use manual multi-IDE rehearsals as the acceptance gate.** Rejected because the failure classes are race conditions and need reproducible automated scenarios.

## Verification

```bash
python3 -m pytest tests/chaos/test_multi_ide_swarm_safety.py -q
python3 -m pytest tests/behavior/test_concurrency_safety_ledgers.py -q
python3 -m pytest tests/contracts/test_memory_lifecycle_portability.py -q
python3 -m pytest tests/unit/test_multi_agent_coordination_primitives.py -q
python3 scripts/derived_artifact_gate.py
```

## 2026-05-02 implementation update

ADR-116 P1.1 is now wired into the Claude-style Agent lifecycle:

- `hooks/agent-prelaunch.sh` resolves a canonical task id and calls
  `scripts/claim_task.py acquire` before recording or launching the agent.
- `hooks/completion-gate.sh` resolves the same task id and releases the claim on
  completion, while preserving the ADR-108 work-ledger and resource-lease flow.
- `scripts/cos-governed-agent.sh` provides the same claim/work-ledger guard for
  Codex or other harnesses without Agent hook parity.
- `scripts/cos-governed-edit.sh` wraps `scripts/edit-coop.sh` so Codex can take
  the same file-edit locks even without an Edit/Write hook matcher.

Canonical task id priority is explicit task id fields first, then a stable hash
of normalized prompt/description, then the native tool-use id as last-resort
correlation. This makes duplicate semantic tasks collide even when different
IDEs generate different native tool ids.

## 2026-05-05 reconciliation fixture update

ADR-118-S4 adds `lib/task_reconciliation.py` and scratch-repo tests that prove
a pending task in one session can be reconciled as `completed-by-watermark` or
`done-by-other-session` when another session writes the completion watermark.
The report names both the pending session and the completing session, avoiding
double implementation.
