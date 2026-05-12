---
adr: 135
title: Self-Evolving Doctrine Proposals
status: accepted
implementation_status: partial
date: '2026-05-03'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: Generated doctrine still needs human judgment.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-135 — Self-Evolving Doctrine Proposals

<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-03  
**Related**: ADR-083, ADR-126, ADR-132, ADR-133, ADR-134  
**Implementation**: `scripts/cos-doctrine-proposer`

---

## Context

ADR-134 lets the SO convert audit findings into bounded improvement proposals.
That covers operational fixes, but not doctrine evolution.

The remaining gap: when repeated evidence shows a rule is too strict, too weak,
too maintainer-specific, or producing false positives, the SO should be able to
propose an amendment to its own doctrine without the operator hand-writing the
first draft.

This must not become autonomous policy mutation. Doctrine is governance surface.
Changing it affects how future agents reason and what they are allowed to do.

## Decision

Add a headless doctrine proposer:

```bash
scripts/cos-doctrine-proposer --profile core --json
scripts/cos-doctrine-proposer --profile core --write
```

The proposer reads control-plane evidence and emits proposed doctrine amendments
under:

```text
docs/proposals/
```

Generated proposals are markdown with:

- `status: proposed`;
- `runtime_effect: none`;
- trigger evidence;
- proposed rule;
- non-goals;
- required follow-up.

The proposer may not edit live rules, hooks, skills, ADR statuses, or manifests.

## Current evidence sources

- direct-main bypass metrics;
- false-positive ledger;
- demotion loop maturity;
- silent-failure transferability debt;
- self-improvement proposal policy.

## Consequences

### Positive

- Doctrine drift becomes reviewable evidence instead of conversational memory.
- The SO can propose amendments to its operating rules without mutating them.
- Repeated friction can become a proposed rule change, not another ad hoc fix.

### Negative / Trade-offs

- Proposal volume can grow if not reviewed.
- Generated doctrine still needs human judgment.
- This does not sign autonomous self-building; it signs self-reflection under
  review.

## Alternatives rejected

- **Auto-edit doctrine**: rejected because doctrine is governance surface.
- **Leave doctrine static**: rejected because evidence can show that a rule has
  become counterproductive.
- **Wait for dashboard**: rejected because the control loop is CLI-first.

## Acceptance Criteria

```bash
python3 -m pytest tests/unit/test_doctrine_proposer.py -q
scripts/cos-doctrine-proposer --profile core --json
```

`--write` must write only under `docs/proposals/`.

## Cross-instance learning boundary

This ADR does not implement cross-instance learning or federation. ADR-132 keeps
that work behind Shape-B triggers. Until those triggers fire, consumer-project
evidence may be collected manually, but locks, memory, and skill registries do
not become distributed systems.

## Status

Accepted — structural contract normalized on 2026-05-04.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

