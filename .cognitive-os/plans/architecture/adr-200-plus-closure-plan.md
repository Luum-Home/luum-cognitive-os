---
related-adrs: ADR-200, ADR-201, ADR-202, ADR-203, ADR-204, ADR-205, ADR-206, ADR-207, ADR-208, ADR-209, ADR-210, ADR-211
---

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

- [x] Create `docs/reports/adr-200-plus-closure-inventory-2026-05-06.md`.
- [x] Create this closure plan.
- [x] Keep `docs/business/master-plan-checklist.md` aligned after every slice in this session.

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
- [ ] Add run-id / event-id trace schema.
- [ ] Add flight-recorder latest report from cross-stream joins.
- [ ] Smoke-test a headless run that emits a joined trace without dashboard dependency.

## Phase 3 — Performance Ledger and Maintainer proposal loop (ADR-201)

- [x] Add SQLite-backed Performance Ledger.
- [x] Export audit JSONL and latest report artifacts.
- [x] Enforce signal-quality quarantine before rollups.
- [x] Add deterministic proposal id helper for deduplication.
- [x] Add `PromoteFromTelemetry` proposal generation gated by ADR-204 consumption policy.
- [x] Add dry-run Maintainer runner with lock, proposal cooldown schema, model-cost policy, and ADR-164 propose-only mutation boundary.
- [x] Smoke-test repeated telemetry producing one bounded human-approved proposal.

## Phase 4 — Domain closures (ADR-206, ADR-207, ADR-208)

- [ ] Gate public claims against current evidence and decommission unsupported claims.
- [ ] Add skill performance lifecycle states and demotion/archive receipts.
- [ ] Add imported-pattern closure audit proving producer, consumer, scheduler, evaluator, and tests.

## Phase 5 — Experiment and service launch gates (ADR-209, ADR-211)

- [ ] Add Maintainer experiment/canary schema.
- [ ] Add outcome-failure queue and regression handling.
- [ ] Add service-mode readiness CLI that composes private-content, retention, signal, trace, ledger, claims, skill, and experiment gates.

## Phase 6 — Fleet/cloud confidence boundary (ADR-210)

- [ ] Keep future-only until ADR-202 and ADR-201 enforcement is proven.
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
python3 -m pytest tests/behavior/test_service_mode_readiness_gate.py -q
```
