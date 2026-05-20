---
related-adrs: ADR-116, ADR-118, ADR-121, ADR-132, ADR-201, ADR-203, ADR-228, ADR-326, ADR-328
source-ledger: docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md
status: active
created: 2026-05-20
---

# Implementation Backlog from Plan Closure — 2026-05-20

## Goal

Reopen the **real implementation work** hidden behind stale plan checkboxes,
without reviving every archived/deferred feature as urgent work and without
claiming that administrative checklist closure equals implementation.

This plan is the operational successor to
`docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md`.

## Ground rules

- Do not edit the closed legacy checklists as the source of truth for active
  work. Use this plan for live implementation.
- Do not implement Kubernetes, clustered workers, or fleet learning unless a
  Shape-B/external-buyer trigger exists per ADR-132.
- Do not revive `agent-escalation-capabilities` Phase 3; ADR-228 owns retry,
  budget, and escalation cost semantics.
- Every completed item below must include `(verified: <command-or-report>)` on
  the checkbox line.
- Prefer narrow slices that reduce real multi-agent loss, false-positive
  governance, or runtime drift.

## Priority 0 — Truth-control repair

These items keep the administrative closure honest.

- [x] Add a report or pending-truth adapter that distinguishes legacy-plan `closed_by_disposition` from `implemented`, so future dashboards do not read `100%` as shipped functionality. (work_id: plan-closure-p0-20260520) (verified: python3 scripts/plan_closure_disposition_audit.py --project-dir . --json --strict && .venv/bin/python -m pytest tests/unit/test_plan_closure_disposition_audit.py -q)
- [x] Add an audit that fails if a legacy checklist item is closed by disposition without referencing the disposition ledger or a successor active plan. (verified: python3 scripts/plan_closure_disposition_audit.py --project-dir . --json --strict && .venv/bin/python -m pytest tests/unit/test_plan_closure_disposition_audit.py -q) (work_id: plan-closure-p0-20260520)
- [x] Update `/session-backlog` or pending-truth docs to prefer this active successor plan over the closed legacy checklists. (work_id: plan-closure-p0-20260520) (verified: python3 scripts/plan_closure_disposition_audit.py --project-dir . --json --strict && .venv/bin/python -m pytest tests/unit/test_plan_closure_disposition_audit.py -q)

## Priority 1 — Multi-session coordination and silent-loss prevention

Rationale: this is the highest blast-radius remaining work. It prevents agents
from duplicating, overwriting, resetting, or losing each other's work.

### Slice 1A — Stable work identity

- [x] Implement commit `work_id` trailer support. (verified: .venv/bin/python -m pytest tests/behavior/test_commit_provenance_work_id.py tests/behavior/test_plan_false_done_gate.py -q) (work_id: 6f09ca3b89e3e474)
  - Source legacy item: multi-session P1.2.
  - Deliverable: `X-COS-Work-ID: <hash>` trailer generated from task fingerprint
    or explicit operator input.
  - Suggested files: `scripts/commit_provenance.py`, commit-message hook or
    projection driver, tests.
  - Acceptance: a COS-attributed test commit includes both `X-COS-Session` and
    `X-COS-Work-ID`.

- [x] Implement atomic plan-checkbox transition proof with work identity. (verified: .venv/bin/python -m pytest tests/behavior/test_commit_provenance_work_id.py tests/behavior/test_plan_false_done_gate.py -q) (work_id: 6f09ca3b89e3e474)
  - Source legacy item: multi-session P4.4.
  - Deliverable: plan transition parser validates `(verified: ...)` plus
    `work_id` for high-risk plan closures.
  - Suggested files: `scripts/verify_plan_claims.py`,
    `hooks/plan-claim-validator.sh`, tests.
  - Acceptance: high-stakes `[x]` without proof/work identity blocks; verified
    line passes; false-positive fixtures pass.

### Slice 1B — Duplicate-work and destructive-git prevention

- [x] Implement pre-commit patch-id dedupe. (verified: `.venv/bin/python -m pytest tests/unit/test_orchestrator_claim_gate_patch_id_dedupe.py -q`)
  - Source legacy item: multi-session P4.1.
  - Deliverable: staged diff patch-id comparison against recent `origin/main`.
  - Suggested files: `scripts/orchestrator_claim_gate.py` or importable helper.
  - Acceptance: duplicate staged diff returns a block/skip finding; unique diff
    passes.

- [ ] Wire destructive-git policy adoption into the active hard-blocking guard
      path where appropriate.
  - Source legacy items: multi-session P3.2 and governance policy adoption.
  - Deliverable: `destructive-git-blocker.sh` either delegates to
    `cos governance policy --category destructive-git` / policy eval or is
    explicitly superseded by policy-as-code projection.
  - Acceptance: `git reset --hard`, `git stash pop/apply/drop`, and unsafe
    force-push block through the same policy surface; `--force-with-lease` stays
    allowed.

### Slice 1C — Status, stale work, and recovery

- [x] Implement event-bus watcher contract. (verified: `.venv/bin/python -m pytest tests/unit/test_task_event_watcher_and_watermark.py -q`)
  - Source legacy item: multi-session P1.3.
  - Deliverable: documented JSONL schema and optional watcher summarizing
    `claim`, `complete`, and `conflict` events.
  - Acceptance: watcher reads fixture events and reports current claims,
    completions, and conflicts.

- [x] Implement stale-task watermark. (verified: `.venv/bin/python -m pytest tests/unit/test_task_event_watcher_and_watermark.py -q`)
  - Source legacy item: multi-session P1.4.
  - Deliverable: task reaper detects declared outputs landed in `main` and marks
    pending tasks completed/superseded when completed by another session.
  - Acceptance: fixture with landed outputs produces completed/superseded state
    without deleting evidence.

- [x] Implement orphan-commit notifier. (verified: `.venv/bin/python -m pytest tests/unit/test_orphan_commit_scan.py -q`)
  - Source legacy item: multi-session P3.1.
  - Deliverable: post-reset/rebase/pull/session-start scanner for unreachable
    commits not in `main`.
  - Acceptance: synthetic orphan commit produces an advisory with recovery
    command; clean repo reports none.

## Priority 2 — Worker leases and headless runtime hardening

Rationale: this makes unattended/headless work safer without jumping straight to
Kubernetes or clusters.

- [x] Implement worker lease tests. (verified: `.venv/bin/python -m pytest tests/contracts/test_headless_worker_lease_contract.py -q`)
  - Source legacy item: headless runtime Phase 2 worker lease tests.
  - Deliverable: acquire/release/renew/stale-recovery contract for queue workers.
  - Acceptance: two workers cannot own the same task concurrently; stale lease is
    recoverable with audit trail.

- [x] Implement VM/container restart idempotency proof. (verified: `.venv/bin/python -m pytest tests/contracts/test_headless_worker_lease_contract.py -q`)
  - Source legacy item: headless runtime Phase 1 VM-restart idempotency.
  - Deliverable: restart-safe receipt/lock behavior for an interrupted headless
    run.
  - Acceptance: simulated restart resumes or safely parks without duplicate
    execution.

- [x] Implement no-host-path proof for container mode. (verified: `.venv/bin/python -m pytest tests/contracts/test_headless_worker_lease_contract.py -q`)
  - Source legacy item: headless runtime Phase 3 no-host-path proof.
  - Deliverable: container run artifacts avoid developer-specific absolute paths.
  - Acceptance: smoke fixture fails if tracked/report artifacts contain host
    paths outside allowed redacted fields.

- [x] Add headless maintainer-agent dry-run smoke inside the service/container
      drill. (verified: `.venv/bin/python -m pytest tests/contracts/test_headless_worker_lease_contract.py -q`)
  - Source legacy item: ADR-201 maintainer telemetry Phase 4.
  - Deliverable: container/headless drill invokes `cos-maintainer-agent --once
    --dry-run --json` without dashboard dependency.
  - Acceptance: smoke exits 0 and emits propose-only boundary.

## Priority 3 — Governance/DX readiness surface

Rationale: this reduces governance friction and makes blocks explainable.

- [ ] Extend `cos governance readiness --json` with discovery-overload signal.
  - Source legacy items: DX Tax Phase 1 and External Review Readiness Phase 3.
  - Acceptance: JSON includes `discovery_overload` with threshold, current count,
    and recommended action.

- [ ] Add active safety layer summary for new operators.
  - Source legacy item: DX Tax Phase 1.
  - Acceptance: one command shows phase, active profile, hard-blocking guards,
    advisory guards, and maintainer/lab opt-ins without requiring ADR reading.

- [ ] Add token/context tax estimate or explicit unavailable signal.
  - Source legacy item: DX Tax Phase 2.
  - Acceptance: `cos governance readiness --json` includes either numeric
    estimate fields or `estimate_unavailable` with reason.

- [ ] Standardize block reports with repair command and owning ADR.
  - Source legacy item: DX Tax Phase 4.
  - Acceptance: representative hard-blocking guards emit primitive/policy/input,
    owning ADR, evidence, and repair command.

- [ ] Ensure archived/lab primitives remain recoverable while default discovery
      remains small.
  - Source legacy items: Governance Tools Consolidation Phase 8.
  - Acceptance: default discovery returns a bounded active set; explicit lab
    query returns archived/lab primitives with status markings.

## Priority 4 — Maintainer telemetry outcome loop

Rationale: telemetry proposals are useful only if accepted changes later measure
impact/regression.

- [ ] Add post-change impact records after accepted proposals land.
  - Source legacy item: ADR-201 Phase 5.
  - Acceptance: accepted proposal can record before/after metrics, source
    rollup, and operator decision.

- [ ] Implement outcome-failure protocol.
  - Source legacy item: ADR-201 Phase 5.
  - Acceptance: regressed/inconclusive outcome quarantines pattern, opens manual
    investigation, requires approval for rollback, and penalizes future
    maintainer confidence for similar patterns.

- [ ] Feed regressions back into `PromoteFromTelemetry` as first-class signals.
  - Source legacy item: ADR-201 Phase 5.
  - Acceptance: regression fixture produces a promotion finding/proposal or a
    deliberate quarantine report.

- [ ] Feed subagent capability mismatches into `PromoteFromTelemetry`.
  - Source legacy item: ADR-203 follow-up.
  - Acceptance: repeated `capability_contract_mismatch` rows produce a proposal
    to adjust routing confidence, docs, or subagent catalog.

## Priority 5 — Capability-aware escalation, scoped revival only

Rationale: ADR-326 parked Phases 1+2 but explicitly preserved their unique value.
Do not revive budget/retry work. Implement only if recurring capability-ceiling
incidents or operator priority justify it.

- [ ] Draft a new ADR or ADR amendment for typed capability-ceiling signals only.
  - Scope: `NEEDS_DEEPER_REASONING`, `NEEDS_TOOL_ACCESS`,
    `NEEDS_MORE_CONTEXT`, `NEEDS_DOMAIN_EXPERT`.
  - Non-scope: retry budgets, escalation cost reporting, generic failure retry
    taxonomy.
  - Acceptance: ADR references ADR-326 and ADR-228 boundaries.

- [ ] Implement read-only signal detection before auto re-dispatch.
  - Acceptance: detector can classify capability ceiling and produce structured
    handoff; no agent is re-launched automatically in the first slice.

## Priority 6 — Benchmarking, only workstation/container first

Rationale: benchmarking is useful, but Kubernetes/cluster benchmarks are noise
without a real worker runtime.

- [ ] Define two small benchmark fixture repositories/workloads.
  - Acceptance: fixtures are license-safe, deterministic enough to compare, and
    cover at least one bugfix and one multi-file refactor.

- [ ] Run workstation/container comparison only.
  - Acceptance: report compares vanilla Claude/Codex where manually available
    against COS-enabled runs, including overhead, catch value, and artifact
    quality.

## Explicitly deferred until Shape-B or external trigger

- Kubernetes manifests.
- Local cluster smoke tests.
- Multi-worker clustered repair/product-factory workflow.
- Cross-customer fleet learning without DP/equivalent privacy proof.
- Full prior-art runtime comparison matrix.

## Suggested first implementation sprint

1. `work_id` trailer + plan checkbox work identity.
2. pre-commit patch-id dedupe.
3. worker lease tests.
4. governance readiness discovery-overload signal.
5. maintainer outcome records.

This order maximizes silent-loss prevention before adding more autonomous runtime
surface.
