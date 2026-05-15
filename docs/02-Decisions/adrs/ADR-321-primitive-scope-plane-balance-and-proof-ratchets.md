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
- scripts/primitive-scope-proof-audit
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
    project_min_warning: 4.5
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
- `scripts/primitive-scope-proof-audit` — proof-level budget ratchet for `proof_level: none`.

CI initially ran the balance/health audits in warning mode. After the first
health-dashboard review queue was triaged on 2026-05-15, the balance,
generic-`os-only`, and false-`both` audits became strict ratchets. Review findings
must now either be fixed or suppressed through explicit `review_exemptions` in
`manifests/primitive-scope-classification.yaml` with a path-specific rationale.
The remaining classifier ratchets stay strict too: unknown, contradictions, low
confidence, and medium confidence must stay at zero.

## Exemption and proof budgets

`review_exemptions` are allowed only as small, explicit review suppressions. They
are not a hidden allowlist: each entry must point at an existing primitive, carry
a path-specific rationale, still suppress an active review signal, and stay under
the per-code budget in `review_exemption_policy`. If a detector stops producing
the underlying signal, the exemption becomes stale and must be removed.

`proof_level: none` is now budgeted. Shared `both`, `project`, and `os-only`
primitives all have zero budget after the family proof closures. New primitives
must add paired proof instead of increasing a hidden baseline.

## 2026-05-15 ratchet promotion

The first health-dashboard queue produced three signals:

- `both-needs-specific-proof` falsely matched lowercase route examples such as
  `internal/users/` because source-checkout detection was case-insensitive for
  `/Users/`. The detector is now case-sensitive and only treats real local
  checkout paths like `/Users/...` or `matias.nahuel` as source-path evidence.
- `pattern-audit` was a true over-internalization finding. It is now `both`
  because its grep/regex sampling protocol is repo-agnostic and has no COS
  source-checkout dependency.
- Five generic-looking COS status/audit skills originally needed explicit review
  exemptions. The detector now treats broad Cognitive OS control-plane markers as
  internal evidence, so those exemptions were removed and the exemption budget is
  zero.

The skills `project_min_warning` threshold moved from `5` to `4.5` because the
current 4.9% project-skill ratio was a rounding-edge signal, not evidence of a
classification bug. Future project-skill growth should be evidence-led rather
than forced to satisfy a round number.

## 2026-05-15 controlled-debt closure

The follow-up closure pass removed the remaining active `review_exemptions` and
added a project-scope family proof for the 44 consumer-facing primitives that had
`proof_level: none`. The standing budgets are now:

```yaml
review_exemption_policy:
  max_active_by_code:
    os-only-generic-candidate: 0
    both-needs-specific-proof: 0
proof_level_budgets:
  none_by_scope:
    both: 0
    project: 0
    os-only: 459
```

The final closure pass then added an `os-only` family proof and lowered the
remaining `os-only` budget to zero. All scopes now have a zero `proof_level:none`
budget; future primitives must provide proof when classified.

## 2026-05-15 os-only proof closure

The final proof-debt pass added `tests/red_team/portability/test_os_only_scope_family.py`
and behavior-evidence rows for every remaining `os-only proof_level:none`
primitive. The test verifies that each baseline primitive still exists, remains
`os-only`, has maintainer-only consumer metadata, and is control/factory/runtime
plane rather than user-plane. While adding the proof, six stale lifecycle rows
that still declared `lifecycle-declared-consumer-candidate` were corrected to
`lifecycle-declared-maintainer` to match their maintainer-only consumer-availability
classification.

The standing proof budget is now:

```yaml
proof_level_budgets:
  none_by_scope:
    both: 0
    project: 0
    os-only: 0
```

## Consequences

- A high `os-only` count is acceptable only when those rows are explainable by
  plane and evidence.
- New primitives must declare or derive scope, plane, consumer surface, and proof
  level before they can be considered high-confidence.
- Scope health is judged by evidence + plane + expected family distribution, not
  by raw scope counts.
