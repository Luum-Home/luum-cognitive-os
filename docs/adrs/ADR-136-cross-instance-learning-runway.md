---
adr: 136
title: Cross-Instance Learning Runway
status: accepted
implementation_status: partial
date: '2026-05-03'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Reports Shape A `deferred` until Shape-B thresholds fire.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-136 — Cross-Instance Learning Runway

<!-- SCOPE: OS -->

**Status**: Accepted  
**Date**: 2026-05-03  
**Related**: ADR-132, ADR-134, ADR-135  
**Implementation**: `scripts/cos_cross_instance_learning.py`

---

## Context

Cross-instance learning is valuable, but full federation is not the next safe
step while Cognitive OS remains in Shape A:

```text
1 maintainer
1–2 machines
multiple IDEs/sessions/agents
one human authority
```

The target future Shape B is different:

```text
2+ maintainers
3+ active machines
consumer projects reporting their own evidence
remote/unsupervised agents
fragmented memory and runtime state
```

Building distributed locks, federated memory, and multi-maintainer quorum before
Shape B triggers fire would add speculative complexity. But doing nothing leaves
the SO without a path to prove that its learning transfers across projects and
machines.

## Decision

Implement a Shape-B runway with four non-speculative primitives:

1. **Consumer evidence exchange**
   - `scripts/cos-export-consumer-evidence`
   - `scripts/cos-import-consumer-evidence`
   - Feeds `manifests/external-adoption-evidence.yaml`.

2. **Deterministic registry locks**
   - `scripts/cos-registry-lock --write`
   - `scripts/cos-registry-lock --audit`
   - Writes `manifests/agentic-primitive-registry.lock.yaml`.
   - Writes `skills/REGISTRY.lock`.

3. **Portable Engram bundle**
   - `scripts/cos-engram-bundle`
   - `scripts/cos-engram-import-propose`
   - Import is propose-only and writes under
     `.cognitive-os/engram-import-proposals/`.

4. **Federation trigger audit**
   - `scripts/cos-federation-trigger-audit`
   - Reads `manifests/federation-triggers.yaml`.
   - Reports Shape A `deferred` until Shape-B thresholds fire.

## Non-goals

- No distributed lock service yet.
- No automatic Engram merge.
- No cross-machine memory consensus.
- No multi-maintainer permission model yet.
- No automatic promotion from consumer evidence into product claims.

## Consequences

### Positive

- The helps-projects claim can be signed by portable bilateral evidence before
  federation exists.
- Multiple machines can detect primitive/skill drift through lock files.
- Memory can move between instances as reviewable bundles without mutating the
  store.
- ADR-132 becomes operational: Shape B has explicit triggers instead of a vague
  future concern.

### Negative / Trade-offs

- Export/import is more manual than federation.
- Registry locks must be regenerated after legitimate primitive/skill changes.
- Engram imports require review; they do not make memory instantly shared.

## Acceptance Criteria

```bash
python3 -m pytest tests/unit/test_cross_instance_learning.py -q
python3 -m pytest tests/unit/test_cross_instance_drill.py -q
scripts/cos-export-consumer-evidence --project demo --reporter maintainer --maintainer-owned --cognitive-cost "local smoke"
scripts/cos-registry-lock --audit
scripts/cos-engram-bundle --project example-project
scripts/cos-federation-trigger-audit
scripts/cos-cross-instance-drill --scenario all
```

`cos-federation-trigger-audit` must report Shape A `deferred` until a configured
Shape-B trigger fires.

Manual drills must use temporary state and must not mutate real product evidence
or claim-signing manifests.

## Status

Accepted — structural contract normalized on 2026-05-04.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

