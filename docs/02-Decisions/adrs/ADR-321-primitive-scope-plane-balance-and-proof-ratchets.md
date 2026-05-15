---
adr: 321
title: Primitive Scope Plane Balance and Proof Ratchets
status: accepted
implementation_status: implemented
date: '2026-05-15'
supersedes:
- ADR-314
superseded_by: null
implementation_files:
- manifests/primitive-scope-classification.yaml
- scripts/primitive_scope_health.py
- scripts/primitive-scope-balance-audit
- scripts/primitive-scope-plane-audit
- scripts/primitive-scope-generic-os-only-audit
- scripts/primitive-scope-false-both-audit
- scripts/primitive-scope-health
- .github/workflows/scope-portability.yml
- scripts/cos-ci-local.sh
- tests/unit/test_primitive_scope_health.py
tier: project
authority: primitive scope classifier baseline, projection audits, and manual scope review
classification_basis: scope answers install surface; plane answers why the primitive exists; proof level answers how strong the portability evidence is
tags:
- primitive-scope
- taxonomy
- governance
- portability
- ratchet
---

# ADR-321 — Primitive Scope Plane Balance and Proof Ratchets

## Context

`SCOPE` answers where a primitive may live or be installed:

- `os-only` — maintainer/self-construction surface for Cognitive OS.
- `project` — consumer-project-only surface.
- `both` — shared surface for COS and consumer projects.

That is necessary but not sufficient. During the primitive classification cleanup,
we found two recurring failure modes:

1. **Over-internalization** — generic primitives marked `os-only` because they lack
   positive consumer evidence yet.
2. **False `both`** — COS-internal primitives marked portable because they look
   useful or have weak/batch proof.

The COS repository also contains more than runtime primitives. It contains the
source, factory, control plane, reports, migrations, audits, and projection
machinery needed to build and govern the OS itself. A high count of `os-only`
primitives can therefore be healthy, but only when those primitives are truly
control-plane/factory-plane surfaces.

## Decision

Cognitive OS will control primitive classification with four orthogonal concepts:

1. **Scope** — install/projection surface: `os-only`, `project`, `both`.
2. **Plane** — why the primitive exists:
   - `control-plane` — maintains, audits, classifies, publishes, or governs COS.
   - `user-plane` — helps ordinary repository work such as review, tests,
     security, documentation, delivery, and quality.
   - `factory-plane` — creates, repairs, scaffolds, harvests, or promotes other
     primitives or project overlays.
   - `runtime-plane` — participates in hook/runtime execution or local services.
3. **Consumer surface** — how the primitive reaches consumers:
   `projected`, `shared`, `maintainer-only`, or `project-generated`.
4. **Proof level** — strength of evidence:
   `none`, `batch`, `family`, or `primitive-specific`.

`SCOPE` must not be used as a proxy for `plane`. A classifier can be `os-only`
+ `control-plane`; a project scaffold template can be `project` + `user-plane`;
a secret detector can be `both` + `user-plane`; a primitive harvester can be
`both` or `project` + `factory-plane` depending on projection evidence.

## Balance policy

COS will not enforce a fixed majority of `both`, `project`, or `os-only`. Instead,
it will monitor expected ratios by primitive family:

```yaml
expected_scope_distribution:
  hooks:
    os-only_max_warning: 60
    both_min_warning: 25
  skills:
    os-only_max_warning: 70
    both_min_warning: 15
    project_min_warning: 5
  scripts:
    os-only_expected_high: true
  templates:
    project_expected_high: true
```

Out-of-range ratios are review signals first, not automatic failures.

## Proof policy

`both` requires positive consumer/shared evidence and portability proof.
High-confidence `both` requires proof level at least `family`:

```text
both requires proof_level >= family
high confidence requires lifecycle + consumer evidence + proof >= family
```

Batch proof remains useful as a migration aid but is not enough to establish high
confidence. This is enforced by the classifier ratchet from the previous phase.

## Enforcement

The implementation provides these audit surfaces:

- `scripts/primitive-scope-balance-audit` — scope distribution and plane balance.
- `scripts/primitive-scope-plane-audit` — strict plane derivation/validity audit.
- `scripts/primitive-scope-generic-os-only-audit` — over-internalization review queue.
- `scripts/primitive-scope-false-both-audit` — false-`both` review queue.
- `scripts/primitive-scope-health` — stable combined dashboard.

CI runs the balance/health audits in warning mode first. The strict ratchets remain:
unknown, contradictions, low confidence, and medium confidence must stay at zero.

## Consequences

- A high `os-only` count is acceptable only when those rows are explainable by
  plane and evidence.
- New primitives must declare or derive scope, plane, consumer surface, and proof
  level before they can be considered high-confidence.
- Scope health is judged by evidence + plane + expected family distribution, not
  by raw scope counts.
