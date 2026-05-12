# ADR-200+ Closure Inventory — 2026-05-06

## Purpose

Track what is already executable, what is only declared, and the safest order for closing ADR-200 through ADR-211. This report is intentionally operational: it exists so the implementation does not depend on an agent remembering scattered conversation state.

## Current state matrix

| ADR | Runtime status | Evidence today | Remaining closure work |
|---|---|---|---|
| ADR-200 State Retention Controller | Implemented | `manifests/state-retention.yaml`, `scripts/state_retention_audit.py`, Stop/prelaunch integration, unit and behavior smoke tests | Keep monitoring worktree and metrics surfaces before promoting them out of observe mode |
| ADR-201 Maintainer Agent Telemetry Promotion Loop | Proposed | ADR and plan exist | Performance Ledger blocker, signal-quality quarantine, proposal schema validation, `PromoteFromTelemetry`, maintainer runner, dry-run smoke |
| ADR-202 Private Content Cross-Harness Portability Boundary | Proposed | ADR exists | Skeleton manifest, audit CLI, unknown-surface detection, projection guard, service smoke |
| ADR-203 Subagent Capability Contract and Launch Preflight | Implemented as standalone CLI | `manifests/subagent-capabilities.yaml`, `scripts/subagent_launch_preflight.py`, unit tests | Wire into every launch path that programmatically selects subagent type |
| ADR-204 Signal Quality and Reward Integrity Boundary | Proposed | ADR exists | Shared reward-signal validator and quarantine fixtures |
| ADR-205 Cross-Stream Trace Joiner and Flight Recorder | Proposed | ADR exists; older trace tests exist for selected paths | Run-id schema, joiner, latest run report, service/headless smoke |
| ADR-206 Aspirational Claim Decommission Gate | Proposed | ADR exists; claim-audit tooling exists for older claim classes | Public claim manifest, launch gate, demotion receipts for unsupported claims |
| ADR-207 Skill Ecosystem Performance and Lifecycle Closure | Proposed | ADR exists | Skill performance projection from ADR-201/204, lifecycle states, demotion/archive flow |
| ADR-208 Imported Pattern Closure Contract | Proposed | ADR exists | Pattern-import manifest and audit proving producer + consumer + scheduler + evaluator |
| ADR-209 Maintainer Reconciler Experiment Contract | Proposed | ADR exists | Experiment schema, canary runner, outcome-failure integration |
| ADR-210 Fleet-Aggregated Confidence Boundary | Proposed/future | ADR exists | Do not implement until ADR-202 sanitized-export/provenance and ADR-201 ledger quality are enforced |
| ADR-211 Service-Mode Readiness Gate | Proposed | ADR exists; service tests exist for older control-plane paths | Readiness CLI combining ADR-200/202/201/205/206/207/209 gates |

## Dependency order

1. **Safety substrate**: close ADR-202 Slice 2a first so private content is classified before service/headless observability reads it.
2. **Signal substrate**: close ADR-204 before ADR-201 rollups so the Maintainer does not learn from corrupt rows.
3. **Trace substrate**: close ADR-205 before treating performance ledger rows as run-complete evidence.
4. **Ledger and proposals**: close ADR-201 Performance Ledger, then `PromoteFromTelemetry` and the dry-run Maintainer.
5. **Domain projections**: close ADR-207 skill lifecycle, ADR-208 imported-pattern closure, and ADR-206 claim decommission using the ledger substrate.
6. **Experiment safety**: close ADR-209 before any executable Maintainer change path.
7. **Launch/service gate**: close ADR-211 after the substrate gates compile.
8. **Cloud/fleet**: keep ADR-210 last; fleet aggregation is unsafe before private-content and provenance enforcement.

## First executable slice

Start with **ADR-202 Slice 2a: skeleton private-content manifest and audit**.

Rationale:

- It is independent of the Maintainer ledger.
- It reduces the risk that later service-mode telemetry or trace work reads private strategy, recovery, or secret surfaces by accident.
- It has straightforward unit tests and a small CLI surface.
- It keeps `.cognitive-os/strategy/` in place and changes only classification, not path layout.

## Operating checklist

- [ ] Add or update one durable plan/report before implementation work.
- [ ] Implement one bounded slice at a time.
- [ ] Add unit tests for every new parser/classifier/gate.
- [ ] Add at least one behavior/smoke test before calling a full ADR closed.
- [ ] Update `docs/08-References/business/master-plan-checklist.md` after each closed slice.
- [ ] Run targeted tests first, then expand only when the changed surface justifies it.
- [ ] Keep untracked unrelated local files out of commits unless explicitly approved.
- [ ] Persist session summary in Engram before ending the session.
