---
adr: "174c"
title: Validator Advisory-to-Blocking Promotion After Soak
status: proposed
date: 2026-05-12
implementation_status: deferred
supersedes: []
superseded_by: null
parent_adr: ADR-174b
implementation_files: []
tier: maintainer
tags: [skills, routing, validator, promotion, soak]
---

# ADR-174c — Validator Advisory-to-Blocking Promotion After Soak

## Status

Proposed. This ADR is intentionally not accepted until soak data proves the
validator is precise enough and the operator explicitly approves promotion.

## Context

ADR-174 accepted auto-derived primitive routing for skills. ADR-174b accepted
two concrete prevention mechanisms:

1. auto-generated skills include `routing_patterns:` frontmatter; and
2. a propose-only soak evaluator reads validator metrics and emits a human-
   reviewable promotion proposal.

The remaining decision is narrower: whether the `skill-md-routing-validator`
should move from advisory warnings to blocking enforcement after enough soak data
shows low false-positive risk.

## Decision

Do not promote automatically. Promotion to blocking mode may happen only when all
of the following are true:

1. the soak evaluator has at least 30 entries in its 30-day window;
2. false-positive rate is below 5%;
3. the generated proposal is reviewed by the operator;
4. rollback is documented and tested; and
5. tests prove both advisory and blocking paths.

Until those conditions are met, validator behavior remains advisory/propose-only.

## Consequences

- ADR-174b can remain `accepted` without carrying a nested `status` map.
- The future runtime behavior change has a dedicated proposed ADR and cannot be
  mistaken for already-approved enforcement.
- The ADR index can route accepted work and proposed promotion work separately.

## Alternatives rejected

- **Keep nested `status: {part_a, part_b}` in ADR-174b** — rejected because ADR
  tooling needs a single decision lifecycle state.
- **Mark all of ADR-174b proposed** — rejected because the generator and
  propose-only evaluator already exist and are accepted.
- **Auto-promote when metrics pass** — rejected because blocking validators can
  halt authoring workflows and require operator approval.

## Verification

```bash
python3 -m pytest tests/contracts/test_validator_promotion_trigger.py -q
```
