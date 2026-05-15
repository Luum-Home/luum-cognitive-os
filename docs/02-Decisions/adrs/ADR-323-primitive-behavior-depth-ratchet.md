---
adr: 323
title: Primitive Behavior Depth Ratchet
status: accepted
implementation_status: implemented
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- manifests/primitive-scope-classification.yaml
- manifests/primitive-behavior-evidence.yaml
- scripts/primitive_behavior_depth_audit.py
- scripts/primitive-behavior-depth-audit
- tests/unit/test_primitive_behavior_depth_audit.py
- tests/red_team/portability/test_primitive_behavior_depth_audit.py
- .github/workflows/scope-portability.yml
- scripts/cos-ci-local.sh
tier: project
authority: ADR-321 scope/proof ratchets and primitive behavior evidence
classification_basis: proof_level says a primitive is covered; behavior_depth says how deep that coverage is
tags:
- primitive-scope
- behavior-proof
- ratchet
- governance
---

# ADR-323 — Primitive Behavior Depth Ratchet

## Status

Accepted.

## Context

ADR-321 closed classification debt: all primitives have scope, plane, consumer
surface, and proof coverage. The remaining ambiguity was semantic: a `family`
proof is not the same thing as a deep individual behavior test.

Without a separate dimension, we could accidentally claim that every primitive is
functionally tested when some are only proven structurally or through projection
surface checks.

## Decision

Cognitive OS separates proof presence from proof depth.

`proof_level` answers: **is this primitive covered by a paired/family proof?**

`behavior_depth` answers: **what kind of behavior does that proof exercise?**

Allowed depths, from shallowest to deepest:

1. `none` — no behavior/proof test found.
2. `structural` — metadata, parser, registry, lifecycle, or scope/surface proof.
3. `projection` — install/projection/portability/render/scaffold surface proof.
4. `smoke` — executable smoke or command/run proof.
5. `functional` — behavior/unit/integration/contract proof of expected behavior.
6. `adversarial` — falsification, negative, chaos, security, or guard-boundary proof.

The audit intentionally treats `tests/red_team/portability/*` as projection by
default, not adversarial by name alone. A portability test only becomes
`adversarial` when its filename/content category indicates a negative/security/
chaos/falsification boundary.

## Enforcement

`scripts/primitive-behavior-depth-audit --strict` emits a stable dashboard and
fails if:

- any primitive has `behavior_depth: none`,
- any primitive falls below the configured minimum depth, or
- the configured shallow-depth budget is exceeded.

Initial policy:

```yaml
behavior_depth_policy:
  minimum_by_scope:
    both: structural
    project: structural
    os-only: structural
  max_by_depth:
    none: 0
    structural: 471
```

The `structural` budget is a ratchet. It prevents adding new structural-only
coverage while allowing future work to spend the budget down by replacing shallow
family/surface proofs with smoke, functional, or adversarial proofs.

## Consequences

- It is now safe to say all primitives are controlled by classification/proof
  ratchets.
- It is not yet correct to say all primitives have deep functional individual
  tests.
- The next maturity frontier is reducing the `structural` budget and increasing
  smoke/functional/adversarial coverage by primitive family.

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.

## Verification

```bash
.venv/bin/python -m pytest tests/unit/test_primitive_behavior_depth_audit.py tests/red_team/portability/test_primitive_behavior_depth_audit.py -q
scripts/primitive-behavior-depth-audit --project-dir . --json
```
