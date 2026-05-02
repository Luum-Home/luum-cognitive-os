# ADR-111: Core/Consumer Boundary for Concurrent-Agent Safety

## Status

Accepted — 2026-05-02. Related: ADR-108, ADR-110.

## Relationship to ADR-106, ADR-108, and ADR-110

ADR-111 is the boundary decision for where concurrent-agent safety lives. ADR-108 is the umbrella safety layer, ADR-106 specifies multi-session primitives, and ADR-110 specifies preserve-branch governance. This ADR decides that those safety primitives are core OS primitives with consumer-project configuration, not project-local rewrites. It does not change the mechanics owned by ADR-106 or ADR-110.

## Context

Cognitive OS can run multiple coding agents against the same worktree, plan, git state, stash, and runtime artifacts. The dangerous failure mode is not a single bad edit; it is an apparently useful agent flow that silently overwrites, hides, or misreports another agent's work.

The SO must protect itself and the projects that consume it. The boundary is explicit: universal safety behavior belongs in the SO core, while each consumer project supplies policy projection such as phase, critical domains, paths, harness support, and approval thresholds.

## Decision

Cognitive OS owns these universal agentic primitives in the core: `edit-coop`, `git-coop`, `stash-leak-alarm`, `plan-claim verifier`, `preserve-branch doctor`, `work inventory doctor`, `concurrency doctor`, `approval ledger`, `resource lease`, `agent work ledger`, and `cross-session reconciler`.

Consumer projects configure those primitives through `concurrency_safety` in `cognitive-os.yaml`. The core uses safe defaults when the section is missing or partial.

## Invariants

- A consumer project can relax or tighten policy, but it must not replace the core primitive implementation.
- Runtime ledgers are append-only; corrections are additional events, not mutation.
- Resource leases expire automatically and are scoped by project directory.
- A plan claim is not complete unless the verifier can prove the expected evidence.
- Preserve branches are not deleted until the doctor can prove manifest, scope, and integration state.
- Preserved work closure must inspect branches, the active worktree, linked worktrees, and stashes; branch-only review is incomplete.
- Doctors are read-only and safe to run in local, CI, and recovery sessions.

## Consequences

- The SO can self-host its concurrent safety layer and export it to consumers.
- Consumer adoption is incremental because missing config falls back to safe defaults.
- Safety behavior becomes testable by unit, behavior, integration, and chaos/scenario lanes.


## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Put concurrency safety only in consumer projects | Duplicates critical safety logic and lets consumers drift from the core guarantees. |
| Hardcode all policies in the SO core | Prevents consumers from setting phase, path, and approval thresholds appropriate to their risk. |
| Rely only on git conflicts and branch naming | Git does not model work claims, resource leases, stale stashes, or approval evidence. |


## Verification

```bash
python3 -m pytest tests/behavior/test_concurrency_safety_ledgers.py -q
python3 -m pytest tests/chaos/test_cross_session_reconciler.py -q
bash scripts/cos-doctor-work-inventory.sh --json
bash scripts/cos-doctor-concurrency.sh --strict
```
