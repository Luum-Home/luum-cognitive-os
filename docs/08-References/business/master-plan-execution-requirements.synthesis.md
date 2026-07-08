---
type: reference-synthesis
source: docs/08-References/business/master-plan-execution-requirements.md
provenance: "Translates the durable product master plan's strategic direction into seven concrete execution requirements with enforcement standards, so the plan becomes product discipline rather than a document that is merely agreed with."
---

## What it is

A seven-requirement execution contract that operationalizes the "durable
product master plan" strategy into enforceable standards, each with a
one-line enforcement checklist, plus an execution order and a
post-2026-05-07 sequence update layered on top after the orchestration
substrate (ADR-220 through ADR-236) landed.

## Key mechanics

- **The Seven Requirements**: (1) An Inviolable Product Promise — "Cognitive
  OS is the operational layer that makes coding agents more governable,
  verifiable, and portable in real repositories" acts as a filter for what
  becomes visible product center; (2) A Small and Protected Core — durable
  nucleus (canonical hooks, context model, policy engine, package spec,
  capability profiles, outcome metrics), everything else defaults to adapter/
  package/plugin/experimental zone; (3) Strategy Must Become Enforcement —
  capability-centric design must propagate beyond `lib/model_router.py` into
  dispatch, gateway selection, skill routing, execution records, metrics; (4)
  CI Must Prove the Real Product — default CI must cover the actual core
  (Python unit tests, Go kernel/provider tests, contract tests, behavior
  tests, doc-integrity checks) so no product claim outruns automation; (5)
  Onboarding and Operation Must Feel Simple on the Outside — one-pass
  install, strong defaults, autodetection, `hooks/self-install.sh` should
  feel like product behavior not internal plumbing; (6) Complexity Must Be
  Deliberately Compressed — four explicit zones (core/compatibility/
  extensions/experimental), non-core systems archived/frozen/de-emphasized;
  (7) Superiority Must Be Visible — proof points a new user can see quickly
  (provider switching, real quality gates, provider-agnostic metrics,
  minutes-to-install, resilience to churn).
- **Execution Order** (original): fix doc drift/redefine README+CONTRIBUTING
  → redesign CI around real core → extend capability-centric routing → optimize
  self-install/onboarding → classify/de-center non-core subsystems → prepare
  a five-minute demo.
- **Post-2026-05-07 sequence update**: explicitly states items 1–6 remain
  relevant but a new sequence interleaves: land the C1–C4 evaluation contract
  as a manifest before drafting new ADRs (done —
  `manifests/orchestration-research-evaluation.yaml`), substrate ADRs first/
  consumers second/adapters third (done — event bus → shadow-git →
  retry+budget → handoff envelope → consumers → opt-in adapters), an
  independent guardrail validator before consumers depend on substrate shape
  (done — `scripts/validate_substrate_consumers.py`, 14/14 PASS), public
  tracking with honest partial-implementation markers per ADR (done), then
  pending: hardening tier (T6–T10) before "production-ready" claims, and
  re-auditing ADR-211 service-mode readiness against the post-substrate
  state.
- States explicitly that the substrate landing is *evidence* for Requirement
  7 (Visible Superiority), not a new eighth requirement — the seven
  requirements are unchanged.

## Relations & where used

- Direct requirement-by-requirement source for the sections in
  `master-plan-checklist.md` (Product Promise, Protected Core, Capability-
  Centric Enforcement, CI and Validation Integrity, Onboarding and
  Operational Simplicity, Complexity Compression, Visible Proof map 1:1 onto
  these seven requirements).
- Requirement 6 (Complexity Compression) is the operational counterpart to
  `feature-reality-audit.md`'s recommendation to demote squad/organization/
  control-plane framing — both push toward the same subtraction discipline.
- Requirement 1's product promise wording matches the wording used in
  `product-messaging.md` and `product-answer-playbook.md`'s "north star."

## Status / caveats

- Coherent, single-purpose document; no internal inconsistency found.
- The "post-2026-05-07 sequence update" section is dated and describes a
  specific historical pivot point (the orchestration substrate landing);
  treat item-completion claims ("Done: ...") as accurate as of that update,
  not necessarily current — cross-check against `master-plan-checklist.md`
  for the latest state of pending items 11–12 (hardening tier, ADR-211
  re-audit).
