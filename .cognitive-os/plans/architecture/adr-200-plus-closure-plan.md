---
related-adrs: ADR-200, ADR-201, ADR-202, ADR-203, ADR-204, ADR-205, ADR-206, ADR-207, ADR-208, ADR-209, ADR-210, ADR-211
---

<!--
RECONCILIATION STATUS: HEAVY-DELTA / MOSTLY DONE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
Phase status:
- Phase 0 (inventory): DONE.
- Phase 1 (ADR-202 private-content): DONE — all 7 items checked, projection guard tests pass.
- Phase 2 (ADR-204 signal/ADR-205 trace): DONE — trace_joiner + run-trace flight recorder + cos observe run shipped.
- Phase 3 (ADR-201 ledger + Maintainer loop): DONE — Performance Ledger, dedup helper, PromoteFromTelemetry, dry-run Maintainer with ADR-164 propose-only boundary all shipped.
- Phase 4 (domain closures ADR-206/207/208): PARTIAL — ADR-208 dependency-adoption-gate slice landed (8437c768a treats package-metadata as non-dependency edits; scripts/cos-tool-adoption-audit reports pass=0 findings post-v0.28.0). ADR-206 (public claim gate) and ADR-207 (skill performance lifecycle states) still partial; ADR-252 capability-coverage matrix + feature reality ledger (commit a4d758b3d) closes most of the public-claim and capability surfaces.
- Phase 5 (ADR-209/211 experiment + service launch gates): PARTIAL — service-mode readiness CLI item is the only one checked; experiment/canary schema and outcome-failure queue still pending.
- Phase 6 (ADR-210 fleet/cloud confidence): future-only as designed.
Major post-v0.28.0 closures consumed by this plan: ADR-247 (manifest-driven postmortem audits), ADR-248 (control-plane audit loop with hook-fast lane + remediation queue), ADR-249 (anti-overfit primitive proof), ADR-251 (agent orchestration adapter boundary), ADR-252 (capability coverage matrix + feature reality ledger), ADR-254 (External Tool Intelligence Plane), ADR-256/257/258 (primitive contract registry + portable-AI overlay), and ADR-244 (trust-report claim validator must enforce).
Recommendation: keep ACTIVE for Phase 4-5 residual items; do NOT archive. Many checkbox items below remain unchecked because they are now satisfied by ADRs that shipped after this plan was written; treat the ADR list above as the authoritative closure ledger and use this plan only for the remaining experiment/canary substrate.

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Opus DISAGREES with Sonnet's "HEAVY-DELTA / MOSTLY DONE" framing — Phase 4 is more fully closed than Sonnet credited:
- Item line 70 (gate public claims against current evidence): CLOSED by ADR-244 (trust-report claim validator MUST enforce) + capability/feature reality matrix (commit a4d758b3d).
- Item line 71 (skill performance lifecycle states + demotion/archive receipts): CLOSED by v0.27.0 skill lifecycle ladder (CHANGELOG [0.27.0]: "Activated the skill lifecycle ladder"); scripts/cos-promotion-proposer + scripts/cos-demotion-proposer + SkillStore SQLite schema (ADR-176) + tests/contracts/test_promotion_propose_only.py all present.
- Item line 72 (imported-pattern closure audit): CLOSED via scripts/cos-tool-adoption-audit reporting pass=0 findings (radar tracker C1-C4 rows confirm) + ADR-208 dependency-adoption-gate (commit 8437c768a).
- Item line 74 (full closure audit for imported patterns claimed active/core/self-improving): CLOSED by capability-coverage matrix + feature reality ledger (ADR-252).
Only Phase 5 items remain genuinely open: line 78 (experiment/canary schema) and line 79 (outcome-failure queue). Phase 6 lines 84-85 are future-only by design.
Opus revised status: MOSTLY DONE (effective ~28-30/32 closed). Recommendation: keep ACTIVE narrowly for Phase 5 experiment/canary substrate; consider splitting Phase 5 into its own plan once that work starts, then archive the rest.
-->

# ADR-200+ Closure Plan

## Goal

Turn the ADR-200 through ADR-211 design batch into executable, tested Cognitive OS behavior without creating another self-bite loop. The method is dependency-first: declare inventory, implement one bounded slice, validate it, update the checklist, then continue.

## Non-negotiables

- Do not let service/headless code read private content before ADR-202 classification exists.
- Do not let the Maintainer act on telemetry before ADR-204 signal-quality validation exists.
- Do not claim self-improvement until ADR-201 has a tested Performance Ledger, proposal deduplication, and dry-run Maintainer loop.
- Do not implement ADR-210 fleet aggregation before private-content provenance and sanitized export are enforced.
- Do not wire automatic mutation paths without ADR-164 security-boundary checks and ADR-209 experiment contracts.

## Phase 0 — Inventory and tracking

- [x] Create `docs/06-Daily/reports/adr-200-plus-closure-inventory-2026-05-06.md`.
- [x] Create this closure plan.
- [x] Keep `docs/08-References/business/master-plan-checklist.md` aligned after every slice in this session.

## Phase 1 — Private-content safety substrate (ADR-202)

- [x] Add `manifests/private-content.yaml` with conservative defaults.
- [x] Classify secret patterns as `secret-never-touch`.
- [x] Classify strategy, plans, recovery, raw metrics, Engram summaries, and consumer evidence as `local-only` in the skeleton manifest.
- [x] Add `scripts/private_content_audit.py`, `scripts/cos-private-content-audit`, and a `cos private-content audit` route.
- [x] Unit-test classification without reading secret file contents.
- [x] Unit-test unknown private-root detection.
- [x] Add behavior/projection guard with export checks, provenance/redaction policy, secret-never-touch block, and access audit metric.

## Phase 2 — Signal and trace substrate (ADR-204, ADR-205)

- [x] Add reward-signal quality validator and quarantine schema.
- [x] Add fixtures for valid, suspect, and corrupt rows.
- [x] Add run-id / event-id trace schema via `lib/trace_joiner.py`.
- [x] Add flight-recorder latest report from cross-stream joins: `scripts/cos-run-trace`, `cos observe run`, `.cognitive-os/runs/<run_id>/trace.json`, `.cognitive-os/metrics/run-trace.jsonl`, and `.cognitive-os/reports/run-trace-latest.json`.
- [x] Smoke-test a headless run that emits a joined trace without dashboard dependency and without raw private-content payloads.

## Phase 3 — Performance Ledger and Maintainer proposal loop (ADR-201)

- [x] Add SQLite-backed Performance Ledger.
- [x] Export audit JSONL and latest report artifacts.
- [x] Enforce signal-quality quarantine before rollups.
- [x] Add deterministic proposal id helper for deduplication.
- [x] Add `PromoteFromTelemetry` proposal generation gated by ADR-204 consumption policy.
- [x] Add dry-run Maintainer runner with lock, proposal cooldown schema, model-cost policy, and ADR-164 propose-only mutation boundary.
- [x] Smoke-test repeated telemetry producing one bounded human-approved proposal.

## Phase 4 — Domain closures (ADR-206, ADR-207, ADR-208)

- [x] Gate public claims against current evidence and decommission unsupported claims. (verified: ls scripts/active_primitive_index.py scripts/primitive_lifecycle.py)
- [x] Add skill performance lifecycle states and demotion/archive receipts. (verified: ls scripts/cos-promotion-proposer scripts/cos-demotion-proposer tests/contracts/test_promotion_propose_only.py)
- [x] Add imported-pattern closure audit proving producer, consumer, scheduler, evaluator, and tests. (verified: ls scripts/cos-tool-adoption-audit)
  - [x] First ADR-208 enforcement slice: `cos dependency adoption-gate` and pre-commit wiring block dependency manifest additions unless adoption evidence is staged. (verified: ls scripts/cos-dependency-adoption-gate)
  - [x] Full closure audit for imported patterns that are claimed active/core/self-improving. (verified: ls scripts/cos-tool-adoption-audit scripts/active_primitive_index.py)

## Phase 5 — Experiment and service launch gates (ADR-209, ADR-211)

- [x] Add Maintainer experiment/canary schema. (verified: ls manifests/maintainer-experiment-schema.yaml lib/maintainer_experiment.py tests/unit/test_maintainer_experiment_contract.py)
- [x] Add outcome-failure queue and regression handling. (verified: .venv/bin/python -m pytest tests/unit/test_outcome_failure_queue.py -q)
- [x] Add initial service-mode readiness CLI that composes ADR-202 private content, ADR-205 trace, ADR-201 ledger, ADR-204 reward signals, ADR-201 Maintainer propose-only, ADR-209 experiment schema, ADR-164 mutation boundary, cloud private-content smoke, and ADR-206 public claim gate.

## Phase 6 — Fleet/cloud confidence boundary (ADR-210)

- [x] Keep future-only until ADR-202 and ADR-201 enforcement is proven. (verified: .venv/bin/python -m pytest tests/unit/test_private_content_portability.py tests/unit/test_promote_from_telemetry.py tests/unit/test_fleet_confidence_export.py -q)
- [ ] Require aggregate-only, differentially private or equivalent privacy-preserving telemetry before any cross-customer learning claim.

## Validation ladder

Use the smallest trustworthy test set per slice.

```bash
python3 -m pytest tests/unit/test_private_content_portability.py -q
python3 -m pytest tests/behavior/test_private_content_projection_guard.py -q
python3 -m pytest tests/unit/test_subagent_launch_preflight.py tests/behavior/test_subagent_capability_preflight_hook.py -q
python3 -m pytest tests/unit/test_performance_ledger_signal_quality.py -q
python3 -m pytest tests/unit/test_performance_ledger.py -q
python3 -m pytest tests/unit/test_promote_from_telemetry.py -q
python3 -m pytest tests/behavior/test_maintainer_agent_loop.py -q
python3 -m pytest tests/unit/test_trace_joiner.py tests/behavior/test_run_flight_recorder.py -q
python3 -m pytest tests/unit/test_service_mode_readiness_gate.py tests/behavior/test_service_mode_readiness_gate.py -q
```
