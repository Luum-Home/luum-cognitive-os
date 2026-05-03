# Headless Self-Improvement Proposer

The self-improvement proposer is the first closed-loop primitive between
Cognitive OS audits and operator-reviewable action.

It intentionally does **not** need a dashboard.

## Contract

```text
audit -> normalize finding -> proposal -> validation plan -> human review
```

The proposer reads existing control-plane outputs and emits a JSON plan:

```bash
scripts/cos-self-improvement-loop --profile core --json
```

To persist the plan for later review:

```bash
scripts/cos-self-improvement-loop --profile core --write
```

Plans are written under:

```text
.cognitive-os/improvements/proposals/
```

That path is non-runtime state. Writing a proposal does not change hook
projection, adoption tiers, rules, skills, or manifests.

## What the proposer may do

- Normalize findings from `cos-boring-reliability`.
- Normalize product-claim gaps from `cos-claim-signature-audit`.
- Describe candidate actions.
- Declare allowed write paths.
- Declare required tests.
- Preserve the approval requirement.

## What the proposer may not do

- Auto-merge.
- Auto-promote to `core` or `team`.
- Invent ROI evidence.
- Delete primitives.
- Extend warning budgets silently.
- Hide current false positives behind historical baselines.

## Growth discipline gate

`scripts/cos-self-improvement-discipline-gate` audits the generated proposal plan
itself. It exists because the main risk is not syntax or implementation; it is
proposal drift.

The gate fails when a proposal:

- enables auto-merge;
- enables auto-promotion to `core` or `team`;
- removes human approval;
- looks like default-surface expansion;
- allows direct writes to live runtime surfaces (`hooks/`, `rules/`, root
  `skills/`);
- omits blocked actions for `auto_merge`, `auto_promote_core_or_team`, or
  `invent_roi_evidence`.

This makes the compounding loop asymmetrical:

```text
detect more -> propose more -> refine/demote/document more
```

but blocks:

```text
detect more -> add more default-visible primitives
```

## Current proposal classes

| Finding | Candidate action |
|---|---|
| `roi-signed-demotion-missing` | Propose ROI evidence collection, explicit deferral, or reviewed demotion |
| `false-positive-ledger-open-events` | Classify historical events or refine parser semantics |
| `manifest-tier-claim-drift` | Add real evidence or demote/move primitive |
| `silent-failure-transferability-debt` | Reclassify allowlist entries or keep Shape-B debt visible |
| `autonomous-primitive-promotion-missing` | Draft a real harvester-signed sandbox→advisory promotion candidate |
| `bilateral-external-adoption-evidence-missing` | Request/import consumer evidence |

## Readiness position

This primitive upgrades the honest claim from:

> Cognitive OS audits itself.

to:

> Cognitive OS audits itself and proposes bounded, test-backed fixes for human
> review.

It does not yet sign the stronger claim:

> Cognitive OS autonomously builds itself.

That stronger claim still requires at least one harvester-proposed,
operator-approved sandbox→advisory promotion with evidence in
`manifests/primitive-lifecycle.yaml`.
