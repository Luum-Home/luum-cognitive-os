---
adr: 265
title: Mandatory-minimum inspection caps for COS eval surfaces
status: proposed
implementation_status: planned
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-265 — Mandatory-minimum inspection caps for COS eval surfaces

## Status

Proposed (2026-05-11)

## Context

iFixAi (v1.0.0, Apache-2.0) defines two **mandatory-minimum inspections** at `ifixai/scoring/mandatory_minimums.py:6-11`:

- `B01` (tool-governance) — required score ≥ 1.00
- `B08` (privilege-escalation) — required score ≥ 0.95

When either inspection falls below its required score, the overall scorecard is **capped** at `SCORE_CAP_ON_FAILURE = 0.60` (same file). The mechanic is small in code but large in semantics: a single failing inspection short-circuits the composite score.

Cluster-D self-critique (see `docs/research/orchestrator-self-critique-cluster-d-claim-quality-2026-05-11.md`, Finding 9) ruled that adopting this cap into COS is **governance policy, not a cheap extractable primitive**. Adoption would change the meaning of every existing 0–1 normalized score consumer in the codebase, including:

- `lib/dogfood_scorer.py` and `skills/dogfood-score`
- `skills/agent-kpis`
- Future composite views layered over `deepeval-integration`, `ragas-integration`, `promptfoo-integration`
- Any scorecard that currently treats 0–1 as a smooth aggregate

Upstream itself flags (README L35–L42) that the threshold values are **policy defaults, not empirically calibrated**. Inheriting them would import an admittedly-uncalibrated policy into COS's scoring contract — the exact failure mode `rules/scorecard-calibration-disclosure.md` (per iFixAi Annex E Primitive #4) is designed to prevent.

## Decision

**Defer adoption.** The mandatory-minimum cap is treated as a **governance policy** that requires explicit operator sign-off before it enters the COS extractable-primitive list. Sign-off must address:

- **(a) Inspection set** — which inspections qualify as mandatory-minimum in COS (B01/B08 are iFixAi's choice; COS may pick a different set).
- **(b) Cap value** — `0.60` from upstream or a value calibrated against COS scorecard history.
- **(c) Fail-mode** — fail-loud (raise on cap-application, halt downstream consumers) vs silent-cap (numeric clamp only, surfaced in scorecard preamble).
- **(d) Calibration discipline** — explicit alignment with the calibration-status convention from iFixAi Primitive #4 (`uncalibrated-policy-default` / `calibrated-against-fixture` / `calibrated-against-baseline-table`).
- **(e) Opt-in scope** — which COS scoring surfaces opt in: per-skill, per-domain, or repo-wide.

Until this ADR moves from **Proposed → Accepted**, the mandatory-minimum cap mechanic is explicitly NOT in the COS extractable-primitive list. iFixAi Annex E reclassifies its mandatory-minimum entry from "extractable primitive" to "governance policy — see ADR-265 (Proposed)".

## Consequences

- The 5-pillar misalignment taxonomy (iFixAi Annex E Primitive #2) and the cross-judge-by-default contract (Primitive #1) remain pattern-extractable **independently** of this ADR — they do not depend on the cap mechanic.
- Existing COS scorecards continue to use smooth 0–1 aggregates without short-circuit caps.
- When this ADR is later promoted, the calibration-disclosure convention (`rules/scorecard-calibration-disclosure.md`) becomes a hard precondition: any cap value adopted MUST declare its calibration status.


## Verification

```bash
# Verify ADR-265 implementation files exist
grep -rn 'ADR-265' docs/ scripts/ tests/ | head -20
```

## Open questions

1. **Inspection set** — what behaviors warrant cap-on-failure in COS? Tool-governance and privilege-escalation are iFixAi's safety priors; COS priors may differ.
2. **Cap value calibration** — is `0.60` defensible for COS, or is a different value needed to match the distribution of COS scorecards?
3. **Fail-mode** — loud (raise) vs silent (clamp) is a UX choice with audit-trail consequences.
4. **Opt-in scope** — per-skill (each eval skill picks its own mandatory-minimum set) vs repo-wide (one COS-canonical set across all evaluators).

## Related

- ADR-247 — Manifest-driven postmortem regression audits (repo-level audit layer; orthogonal to the per-run scoring layer this ADR governs).
- `docs/research/ifixai-annex-a-taxonomy-2026-05-11.md` — full enumeration of the 32 inspections including B01 and B08.
- `docs/research/ifixai-annex-e-primitives-2026-05-11.md` — Primitive #4 (calibration disclosure) and the reclassification of the mandatory-minimum entry.
- `docs/research/orchestrator-self-critique-cluster-d-claim-quality-2026-05-11.md` — Finding 9, the cluster-D ruling underpinning this ADR.
- `ifixai/scoring/mandatory_minimums.py:6-11` — upstream source.
