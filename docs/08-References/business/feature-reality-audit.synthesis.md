---
type: reference-synthesis
source: docs/08-References/business/feature-reality-audit.md
provenance: "Separates Cognitive OS's genuinely portable, high-value product core from adjacent subsystems and future-facing narratives that risk implying more runtime maturity than the product currently delivers."
---

## What it is

A feature-by-feature strategic audit that classifies every major Cognitive OS
subsystem along three axes — portability state, product value, and complexity
risk — to answer where the product should present itself as proven versus
aspirational. It concludes the repository has a real, defensible product core
but risks getting buried under adjacent control-plane and platform narratives.

## Key mechanics

- **Taxonomy inputs**: builds on `docs/product-zones.md` and
  `manifests/product-zones.yaml`, adding a feature-level lens on top of the
  core/compatibility/extension/experimental zone split.
- **Portability State** axis: `core-agnostic` (stable internal contract,
  harness-independent) → `driver-projected` (portable core, harness-specific
  install/UX) → `claude-advantaged` (works elsewhere, Claude Code is
  meaningfully better) → `claude-only` (not portable in practice).
- **Product Value** axis: high (strengthens the governable/verifiable/portable
  wedge) / medium (support capability) / low (interesting but unproven).
- **Complexity Risk** axis: low/medium/high, measuring whether cost is
  proportional to current value or drifts into platform sprawl.
- **Audit table** scores 12 feature areas. Rated strongest (core-agnostic,
  high value, low risk): canonical hook context/provider normalization,
  capability-centric routing. Rated for heavy demotion: squads/organizations/
  software-factory framing (`claude-only` to `claude-advantaged`, low-to-medium
  value, high risk) and the "13-layer operating system" framing (low value,
  high risk, `n/a` portability).
- Defines a **recommended product boundary** statement: "Cognitive OS is the
  operational layer for coding agents that makes governance, verification, and
  portability work in real repositories," with everything else framed as core
  runtime support, harness driver, optional package, or future architecture.
- Lists concrete **immediate actions**: keep kernel/portability/routing/
  verification surfaces central; move squad/org/control-plane language out of
  first-contact docs; mark remediation/dashboards/memory-heavy flows as
  optional; audit portability language to cover only `core-agnostic` and
  `driver-projected` surfaces; build demos around install/govern/verify/switch/
  inspect.

## Relations & where used

- Builds directly on `docs/product-zones.md` and
  `manifests/product-zones.yaml`.
- Its "Immediate Actions" are echoed as checklist items in
  `master-plan-checklist.md` (`## 6. Complexity Compression`) and align with
  the seven requirements in `master-plan-execution-requirements.md`
  (particularly Requirement 6, Complexity Must Be Deliberately Compressed).
  Its recommendation to demote squad/organization/control-plane framing
  directly contradicts the heavy squad/org/control-plane narrative built up in
  `kubernetes-for-agents.md` — the two documents represent opposing positions
  on how much weight that narrative should carry in top-level product
  messaging.

## Status / caveats

- This is a strategic/critique document, not an implementation-status ledger;
  it expresses recommendations and assessments rather than verified current
  state. Treat its portability/value/risk ratings as an audit opinion, cross-
  check against `docs/09-Quality/legal/h1-feature-status-audit.md` or the
  ACC/readiness ledgers for hard status.
- No internal inconsistency found within the document itself.
