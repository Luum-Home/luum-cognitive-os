# ADR-118 — Multi-IDE Swarm Safety Testbed

<!-- SCOPE: OS -->

**Status**: Proposed  
**Date**: 2026-05-02  
**Related**: ADR-089, ADR-098, ADR-105, ADR-106, ADR-108, ADR-116

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

| Scenario | Expected behavior |
|---|---|
| Same task race | First claim wins; second live claim exits blocked with holder metadata. |
| Same file race | Second writer is blocked/advised and the first edit survives. |
| Same domain lease | First critical-domain lease wins; competing session is blocked. |
| Dirty worktree + pull/rebase | `git pull --rebase` over WIP is blocked in agent context. |
| Agent B fix overwritten | `git reset`/fetch-reset/rebase over WIP is blocked before the fix disappears. |
| Cross-IDE parity | Claude/Codex shared gates are proven; known matcher gaps are explicit. |
| Memory sharing | Portable memory doctor proves both harnesses project/run lifecycle hooks. |
| Completed by other agent | Watermark/reaper marks pending work as `completed-by-watermark`. |

## Consequences

- The SO can claim controlled multi-session parallelism only when this lane
  passes.
- Codex parity gaps remain honest findings until Codex exposes equivalent
  `Agent`/`Edit` hook surfaces or `governed_runner` covers them.
- Task claiming becomes a first-class agentic primitive instead of relying on
  post-launch work ledgers.

## Verification

```bash
python3 -m pytest tests/chaos/test_multi_ide_swarm_safety.py -q
python3 -m pytest tests/behavior/test_concurrency_safety_ledgers.py -q
python3 -m pytest tests/contracts/test_memory_lifecycle_portability.py -q
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
