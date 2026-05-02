# ADR-111: Core/Consumer Boundary for Concurrent-Agent Safety

## Status

Accepted — Implemented 2026-05-02. Related: ADR-108, ADR-110.

Consumer projection of the four Claude-only safety gates to Codex is complete.
See §Per-Gate Status Table below for implementation details.

## Relationship to ADR-106, ADR-108, and ADR-110

ADR-111 is the boundary decision for where concurrent-agent safety lives. ADR-108 is the umbrella safety layer, ADR-106 specifies multi-session primitives, and ADR-110 specifies preserve-branch governance. This ADR decides that those safety primitives are core OS primitives with consumer-project configuration, not project-local rewrites. It does not change the mechanics owned by ADR-106 or ADR-110.

## Context

Cognitive OS can run multiple coding agents against the same worktree, plan, git state, stash, and runtime artifacts. The dangerous failure mode is not a single bad edit; it is an apparently useful agent flow that silently overwrites, hides, or misreports another agent's work.

The SO must protect itself and the projects that consume it. The boundary is explicit: universal safety behavior belongs in the SO core, while each consumer project supplies policy projection such as phase, critical domains, paths, harness support, and approval thresholds.

## Decision

Cognitive OS owns these universal agentic primitives in the core: `edit-coop`, `git-coop`, `stash-leak-alarm`, `plan-claim verifier`, `preserve-branch doctor`, `work inventory doctor`, `worktree triage doctor`, `concurrency doctor`, `approval ledger`, `resource lease`, `agent work ledger`, `cross-session reconciler`, and `session filesystem reaper`.

Consumer projects configure those primitives through `concurrency_safety` in `cognitive-os.yaml`. The core uses safe defaults when the section is missing or partial.

## Invariants

- A consumer project can relax or tighten policy, but it must not replace the core primitive implementation.
- Runtime ledgers are append-only; corrections are additional events, not mutation.
- Resource leases expire automatically and are scoped by project directory.
- A plan claim is not complete unless the verifier can prove the expected evidence.
- Preserve branches are not deleted until the doctor can prove manifest, scope, and integration state.
- Preserved work closure must inspect branches, the active worktree, linked worktrees, and stashes; branch-only review is incomplete.
- Linked worktrees are not removed until triage proves no unapplied commits, dirty files, or stashes remain.
- Session filesystem cleanup is archive-first and content-aware; pending requests/tasks keep the session directory.
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


## Per-Gate Status Table

This table records the Codex consumer projection outcome for the four gates
identified in the ADR-111 projection task (2026-05-02).

| Gate | Hook | Claude Event | Codex Projection | Status | Notes |
|---|---|---|---|---|---|
| Gate-1 | `symlink-mutation-guard.sh` | `PreToolUse[Bash]` | Native bash matcher | **Projected** | Already in `.codex/hooks.json` PreToolUse bash. Portability test: `tests/red_team/portability/test_symlink-mutation-guard.py`. |
| Gate-2 | `scope-marker-portability-gate.sh` | `PreToolUse[Bash]` | Native bash matcher | **Projected** | Already in `.codex/hooks.json` PreToolUse bash. Portability test: `tests/red_team/portability/test_scope-marker-portability-gate.py`. |
| Gate-3 | `concurrent-write-guard.sh` | `PreToolUse[Edit\|Write]` | `UserPromptSubmit` via `concurrent-write-guard-codex-proxy.sh` | **Projected (degraded)** | Codex does not expose `PreToolUse[Edit\|Write]`. Proxy fires at prompt time and scans for cross-session live locks (warning only). Mutual-exclusion invariant is harness-advantaged for Claude Code. Portability test: `tests/red_team/portability/test_concurrent-write-guard.py`. |
| Gate-4 | `claim-validator.sh` | `PostToolUse[Agent]` | **Gap** — no Codex `PostToolUse[Agent]` | **Gap — commit-time fallback** | Codex v0.126.0-alpha.8 fires `PostToolUse` only for Bash. Per-agent response validation is not natively projectable. Fallback: `orchestrator-claim-gate.sh` (`PreToolUse[Bash]`, already projected) enforces claim verification at `git commit` time. Full parity requires upstream Codex hook expansion. Gap documented in `cognitive-os.yaml` and `manifests/harness-driver-capabilities.yaml`. Portability test: `tests/red_team/portability/test_claim-validator.py`. |

### Projection Classification (cross-harness-authoring taxonomy)

| Gate | Classification |
|---|---|
| Gate-1: symlink-mutation-guard | `core-agnostic` — bash-projectable without modification |
| Gate-2: scope-marker-portability-gate | `core-agnostic` — bash-projectable without modification |
| Gate-3: concurrent-write-guard | `harness-advantaged` — prompt-level scan projected, per-file locking Claude-only |
| Gate-4: claim-validator | `harness-only` (for per-response granularity) — commit-time fallback projected |

## Verification

```bash
python3 -m pytest tests/behavior/test_concurrency_safety_ledgers.py -q
python3 -m pytest tests/chaos/test_cross_session_reconciler.py -q
bash scripts/cos-doctor-work-inventory.sh --json
python3 -m pytest tests/behavior/test_cos_worktree_triage.py -q
bash scripts/cos-doctor-concurrency.sh --strict

# ADR-111 consumer projection tests (all 4 gates)
python3 -m pytest tests/red_team/portability/test_symlink-mutation-guard.py -q
python3 -m pytest tests/red_team/portability/test_scope-marker-portability-gate.py -q
python3 -m pytest tests/red_team/portability/test_concurrent-write-guard.py -q
python3 -m pytest tests/red_team/portability/test_claim-validator.py -q
```
