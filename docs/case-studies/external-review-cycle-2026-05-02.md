# Case Study — Absorbing an External Senior Review Without Collapse

**Date:** 2026-05-02 → 2026-05-03
**Audience:** External adopters and future contributors evaluating whether the boring-reliability doctrine actually behaves as advertised.
**Companion docs:** [`boring-reliability-control-plane.md`](../architecture/boring-reliability-control-plane.md), [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md), [ADR-126](../adrs/ADR-126-agentic-primitive-lifecycle-governor.md), [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md), [ADR-133](../adrs/ADR-133-expansion-without-monsterization.md).

## Why this exists

The boring-reliability doctrine claims that Cognitive OS can absorb external critique by converting it into ADRs, manifest changes, and CI-enforced gates rather than into defensiveness or feature sprawl. That claim is hard to evaluate from the doctrine alone. This document captures one concrete cycle so readers can decide for themselves whether the doctrine behaves as written.

The cycle is preserved as a worked example, not as a marketing artefact. The interesting property is **traceability**: every step links to an artefact in the repository.

## The cycle

### Step 1 — External SR review (input)

A senior/Solutions-Architect read of the repository was solicited explicitly. The review asserted, in summary:

- Surface area (162 skills, 188 hooks, 112 rules, 1.6K-line `cognitive-os.yaml`) presents as framework, not guardrail.
- Token tax of the default profile was non-trivial; full profile was near context-window saturation.
- ADR programme had volume but no demonstrated retirement discipline; lifecycle states were paper.
- Recommendation: a `--minimal` tier and a hard threshold on default-visible primitives, or the surface would re-inflate within sprints.

Captured at: [`docs/business/cos-vs-vanilla-dx-review.md`](../business/cos-vs-vanilla-dx-review.md), [`docs/reports/dx-assessment-2026-05-02.md`](../reports/dx-assessment-2026-05-02.md).

### Step 2 — Strategic reframing (decision capture)

Instead of treating the review as a request for cosmetic surface reduction, the response framed it as a distribution problem and a lifecycle problem:

- [ADR-124](../adrs/ADR-124-cos-distribution-boundaries.md) — distribution tiers (`core` / `team` / `maintainer` / `lab`) so the small surface and the full surface can coexist.
- [ADR-125](../adrs/ADR-125-governance-tools-value-boundary.md) — explicit value boundary: governance must earn its runtime cost; low-ROI primitives are demoted, not preserved by inertia.
- [ADR-126](../adrs/ADR-126-agentic-primitive-lifecycle-governor.md) — eight lifecycle states (`candidate` → `sandbox` → `advisory` → `blocking` → `default-on` → `demoted` → `archived` → `deleted`) with required metadata.

The review was not absorbed as an opinion. It was absorbed as an obligation to make existing doctrine machine-checkable.

### Step 3 — Structural enforcement (the part that matters)

Three primitives were added to make the framing self-policing rather than aspirational:

- [`scripts/active_primitive_index.py`](../../scripts/active_primitive_index.py) — hard thresholds on the default-visible surface (`VISIBLE_WARN_THRESHOLD = 12`, `VISIBLE_FAIL_THRESHOLD = 25`), wired into CI through [`scripts/cos-ci-local.sh`](../../scripts/cos-ci-local.sh).
- [`scripts/lab_first_promotion_gate.py`](../../scripts/lab_first_promotion_gate.py) — every new primitive starts in `lab`/`sandbox`; promotion to `core` / `team` / `default-on` requires a machine-readable evidence block. See [ADR-133](../adrs/ADR-133-expansion-without-monsterization.md).
- [`scripts/session_start_budget.py`](../../scripts/session_start_budget.py) — measures and budgets what gets injected into the session preamble, attacking the runtime token cost the review named.

These exist so the next person who proposes adding a primitive must first explain why it does not start in `lab`. The default direction of travel was inverted.

### Step 4 — Demote with evidence (the first real test)

The review observed that `lifecycle_state: demoted` did not appear anywhere in the manifest, leaving ADR-126 as paper. A demotion was performed against `hooks/task-completed.sh` — not by deletion, but by lifecycle state transition with an explicit evidence block:

```yaml
lifecycle_state: demoted
demotion_evidence:
  demoted_on: '2026-05-03'
  reason: COS extension hook is not required for default team/core adoption;
    demotion proves ADR-126 inactive lifecycle semantics without deleting the primitive.
sunset_criteria: archive after 90 days with no opt-in use
```

Proof artefact: [`docs/reports/lifecycle-demotion-task-completed-2026-05-03.md`](../reports/lifecycle-demotion-task-completed-2026-05-03.md). Implementation commit: `97307e34 feat: prove lifecycle demotion semantics`.

The demotion is intentionally small. It exercises the semantics without asking for organisational courage. The next demotions are expected to be larger and ROI-driven.

### Step 5 — Doctrine update (closing the loop)

The rationale layer was extended so future readers do not have to re-derive the framing:

- [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md) — companion doc to the control plane: why the system has the shape it has, including the explicit naming of the velocity-vs-durability tradeoff that ADR-132's trigger conditions sit on top of.
- [ADR-132](../adrs/ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — strategic decision left open: at what point the present single-maintainer calibration should be re-shaped for wider adoption.

The cycle ended with an open question documented as such, not with a claim of completion.

## What made the cycle possible

The cycle is not a heroics story. It is the predictable output of having the following properties already in place:

1. **A persistent decision substrate.** ADRs and Engram make it cheap to capture a decision now that future-self can read later. Without that, critique evaporates within a session.
2. **Bilateral verification primitives.** ADR-105 (claim verification) and `aspirational_audit.py` mean a claim like "we archived these hooks" can be falsified mechanically. That eliminates the most expensive failure mode — wishful self-reporting.
3. **A doctrine that named retirement as a first-class action.** ADR-125 and ADR-126 existed *before* the review; the review's pressure was to operationalise them, not to invent them.
4. **CI as the durable surface.** Wiring the new thresholds into `cos-ci-local.sh` (commit `d368a324`) means the discipline survives the moment of attention that produced it.

If any of those four are missing, the same external review absorbs as defensiveness or feature-add, not as doctrine clarification.

## What the cycle does not prove

Stated honestly so the artefact is useful:

- **One demotion is not a discipline.** The discipline is the second, third, and tenth demotion, especially when one of them must be defended against the cost of building it. Re-read this document after the lifecycle manifest holds three or more `lifecycle_state: demoted` entries before drawing conclusions about durability.
- **The ROI dashboard has not yet signed a decision.** The first demotion was justified by portability, not by `cos_governance_roi.py` output. The dashboard is instrument, not cutting tool, until a demotion's stated reason is "ROI dashboard reported sustained net-negative".
- **Single-maintainer absorption is not multi-maintainer absorption.** The cycle completed inside one operator's continuous attention. The same shape under two contributors with disagreement would expose coordination costs this cycle did not pay. ADR-132 names that gap.

## Replication template

If another project wants to run a comparable cycle, the minimum scaffolding is:

1. A persistent decision log with stable identifiers (ADRs, Engram, equivalent).
2. At least one mechanical falsifier of self-reports (claim verification, aspirational audit, or equivalent).
3. A lifecycle vocabulary that includes a demotion state distinct from delete.
4. A CI gate that fails the build when the default surface grows past a declared threshold.
5. An explicit doctrine that declares retirement (not addition) as the dominant operation in the current phase.

Items 1–3 are paper without item 4. Item 4 is performative without item 5. Item 5 is a slogan without items 1–3. The combination is what makes the cycle reproducible rather than dependent on any one operator's diligence.

## How to read this document over time

This is a snapshot of one cycle. The reproducible value is the structure of the cycle, not its specific findings. If a later review produces a different reframing or a different set of artefacts, that is expected and welcome. The point of preserving this is so the *shape* of the response — capture, reframe, enforce, test, document — has a worked example to compare against, not a procedure to comply with.
