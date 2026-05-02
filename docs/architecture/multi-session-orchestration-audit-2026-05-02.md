# Multi-Session Orchestration Audit — Documented vs Implemented

> Date: 2026-05-02
> Scope: Cognitive OS primitives that coordinate multiple IDEs, sessions, worktrees, and agents.

## Verdict

Cognitive OS already has real coordination primitives: session identity, git-index coordination, file edit locks, claim verification, agent bus monitoring, sprint manifests, stash leak alarms, and harness projection. The missing layer is not another launcher; it is a unifying **Concurrent Agent Safety Layer** that composes those primitives into a ledger, resource leases, reconciliation, and cross-session status.

## Status Matrix

| Primitive | Primary docs | Implementation | Claude wired | Codex wired | Tests / proof | Status |
|---|---|---|---:|---:|---|---|
| Bilateral claim verification | `docs/adrs/ADR-105-claim-verification-contract.md`, `docs/architecture/claim-verification-matrix.md` | `lib/orchestrator_verify.py`, `hooks/claim-validator.sh`, `hooks/plan-claim-validator.sh`, `hooks/orchestrator-claim-gate.sh`, `scripts/orchestrator_claim_gate.py`, `scripts/verify_plan_claims.py` | ✅ | ✅ Bash baseline | `tests/contracts/test_orchestrator_verify.py`, `tests/contracts/test_orchestrator_claim_gate.py` | Real, recently expanded |
| Cross-IDE pre-commit/push claim gate | `docs/architecture/claim-verification-matrix.md` | `hooks/orchestrator-claim-gate.sh`, `scripts/orchestrator_claim_gate.py` | ✅ `.claude/settings.json` | ✅ `.codex/hooks.json` | `python3 -m pytest tests/contracts/test_orchestrator_claim_gate.py -q` | Real; profile regeneration now preserves it |
| Git-index coordination | `docs/adrs/ADR-089-multi-session-git-coordination.md` | `scripts/git-coop.sh`, `hooks/git-commit-scope-guard.sh` | ✅ | ✅ Bash baseline | `tests/unit/test_git_coop.py` | Real |
| File edit coordination | `docs/adrs/ADR-098-multi-agent-file-coordination.md` | `scripts/edit-coop.sh`, `hooks/edit-lock-pre-tool.sh`, `hooks/concurrent-write-guard.sh` | ✅ via `edit-lock-pre-tool.sh` | Limited by Codex hook surfaces | `tests/unit/test_edit_coop.py`, `tests/integration/test_concurrent_agent_same_file.py` | Real in Claude; partial cross-harness |
| Session identity and tracking | `docs/session-concurrency.md` | `hooks/session-init.sh`, `.cognitive-os/sessions/`, `.active-sessions.lock` | ✅ | ✅ where SessionStart projection exists | `tests/unit/test_session_lifecycle.py` | Real |
| Stash leak alarm | `docs/adrs/ADR-106-multi-session-safety-primitives.md` | `scripts/stash-leak-alarm.sh` | Partial | Partial | `tests/behavior/test_stash_leak_alarm.py` | Real detector; broader dispatch integration still partial |
| Plan closure validation | `docs/adrs/ADR-106-multi-session-safety-primitives.md`, `docs/architecture/claim-verification-matrix.md` | `hooks/plan-claim-validator.sh`, `scripts/verify_plan_claims.py` | ✅ | Limited by Codex Edit/Write hook support | `tests/behavior/test_plan_false_done_gate.py`, `tests/contracts/test_orchestrator_claim_gate.py` | Partial cross-harness |
| Provenance markers | `docs/adrs/ADR-088-provenance-trailer-ppid-chain.md` | `scripts/write_context_marker.py`, commit provenance helpers | Via agent preamble / hooks | Partial | `tests/unit/test_commit_provenance.py`, `tests/unit/test_commit_provenance_chain.py` | Real; needs end-to-end enforcement review |
| Agent bus monitoring | ADR-028 family, dogfood reports | `lib/agent_bus.py`, `lib/agent_bus_metrics.py`, `scripts/orchestrator.py` | Runtime, Valkey/file fallback | Runtime where invoked | `tests/unit/test_agent_bus.py`, `tests/integration/test_orchestrator_cli.py` | Real, not the full control plane |
| Sprint orchestration | `docs/adrs/ADR-036-sprint-orchestration-primitives.md` | `scripts/cos_sprint.py`, `lib/sprint_test_aggregator.py` | CLI/runtime | CLI/runtime | `tests/integration/test_cos_sprint_cli.py`, `tests/unit/test_sprint_orchestrator.py` | Real MVP |
| Harness adapters | `docs/architecture/harness-engineering.md`, `docs/architecture/cross-harness-authoring.md` | `lib/harness_adapter/*`, settings drivers | N/A | N/A | harness adapter tests and projection contracts | Real, but hook-surface parity varies |
| Concurrent Agent Safety Layer | `docs/adrs/ADR-108-concurrent-agent-safety-layer.md`, `docs/architecture/concurrent-agent-safety-master.md` | Composed from pieces above; no single composer yet | N/A | N/A | scenario tests exist for slices | Missing unified layer |
| Agent Work Ledger | `docs/adrs/ADR-108-concurrent-agent-safety-layer.md` | Not a unified runtime primitive yet | ❌ | ❌ | No full contract located | Aspirational |
| Resource Lease | `docs/adrs/ADR-108-concurrent-agent-safety-layer.md` | Not a unified runtime primitive yet | ❌ | ❌ | No full contract located | Aspirational |
| Read-only safety status composer | `docs/adrs/ADR-108-concurrent-agent-safety-layer.md`, `docs/adrs/ADR-111-core-consumer-concurrency-safety-boundary.md` | `lib/concurrent_agent_safety_status.py`, `scripts/cos-concurrent-status.py` | CLI/runtime | CLI/runtime | `tests/unit/test_concurrent_agent_safety_status.py` | Real initial slice |
| Cross-session reconciler | `docs/adrs/ADR-108-concurrent-agent-safety-layer.md`, `docs/adrs/ADR-111-core-consumer-concurrency-safety-boundary.md` | Read-only status composer exists; divergence policy/reconciliation loop not complete | Partial | Partial | `tests/chaos/test_cross_session_reconciler.py` exists as target surface | Partial |
| Squad runtime coordination | `rules/squad-protocol.md`, `squads/organization.yaml` | skills/docs, no confirmed session-level coordinator | ❌ | ❌ | Not proven in this audit | Dormant |

## Current Wiring Evidence

As of this audit, the cross-IDE claim gate is no longer stranded in code only:

- `.claude/settings.json` contains `hooks/orchestrator-claim-gate.sh` under `PreToolUse` Bash.
- `.codex/hooks.json` contains `hooks/orchestrator-claim-gate.sh` under the Codex Bash baseline.
- `scripts/generate-project-settings.sh` includes `orchestrator-claim-gate.sh` in the portable hook projection list.
- `cognitive-os.yaml` declares the `orchestrator-claim-gate` hook.
- `scripts/_lib/settings-driver-claude-code.sh` emits `orchestrator-claim-gate.sh` and `plan-claim-validator.sh` during Claude profile regeneration.
- `scripts/apply-efficiency-profile.sh` sanity-checks and summarizes those hooks after Claude projection.

## What Not To Rebuild

Do not create parallel implementations for these primitives:

1. Git-index lock / scoped commits: extend `scripts/git-coop.sh` and `hooks/git-commit-scope-guard.sh`.
2. File edit locking: extend `scripts/edit-coop.sh` and `hooks/edit-lock-pre-tool.sh`.
3. Claim verification: extend `lib/orchestrator_verify.py`, `scripts/orchestrator_claim_gate.py`, and the existing claim hooks.
4. Agent communication: extend `lib/agent_bus.py` and `lib/agent_bus_metrics.py`.
5. Sprint manifests: extend `scripts/cos_sprint.py` and `lib/sprint_test_aggregator.py`.
6. Harness projection: extend the settings drivers and `cognitive-os.yaml`, not ad hoc settings edits.

## Next Implementation Gap

The first read-only composer slice now exists in `lib/concurrent_agent_safety_status.py` with CLI `scripts/cos-concurrent-status.py`. Its responsibility is observation only:

- list active sessions;
- list edit/git/plan locks;
- list stash leak alarm state;
- list claim-gate/projection status;
- list recent agent bus heartbeats;
- report missing provenance or closure evidence;
- emit a single JSON status for CLI/dashboard use.

Do not start with auto-repair. The next milestone is to turn this status payload into a reconciler policy that compares divergent plan/claim/provenance state and still tells the truth without mutating state.

## Verification Commands

```bash
python3 -m pytest tests/contracts/test_orchestrator_claim_gate.py -q
python3 -m pytest tests/unit/test_concurrent_agent_safety_status.py -q
python3 -m pytest tests/unit/test_edit_coop.py tests/unit/test_git_coop.py -q
python3 -m pytest tests/integration/test_concurrent_agent_same_file.py tests/behavior/test_plan_false_done_gate.py tests/behavior/test_stash_leak_alarm.py -q
```
