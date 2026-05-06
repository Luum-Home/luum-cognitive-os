# ADR-210 — Fleet-Aggregated Confidence Boundary

<!-- SCOPE: OS -->

**Status**: Proposed  
**Date**: 2026-05-06  
**Related**: ADR-136, ADR-201, ADR-202, ADR-204, ADR-209  
**Source**: `.cognitive-os/strategy/research/06-external-patterns-benchmark.md`, `.cognitive-os/strategy/research/08-self-improvement-roadmap.md`

---

## Context

External systems such as Renovate show that fleet-aggregated confidence can be a
valuable commercial boundary: one install's outcome improves confidence for
another without sharing source code. Cognitive OS may eventually learn from
multiple projects or tenants, but ADR-202 requires strict private-content
boundaries.

## Decision

Fleet learning is allowed only over sanitized, provenance-carrying aggregate
confidence rows. Raw code, raw prompts, private strategy, secrets, and local-only
content never participate.

Fleet rows must include:

- primitive/surface id;
- version/fingerprint;
- outcome class;
- confidence band;
- test/verification class;
- anonymized environment class;
- tenant/project boundary id hash;
- redaction/provenance receipt;
- opt-in status.

## Boundary

OSS maintainer remains single-tenant and local. Cloud may aggregate only
`sanitized-export` rows that satisfy ADR-202 and ADR-204. Fleet confidence may
raise or lower proposal priority, but it must not auto-apply changes in a
customer environment without local approval and local experiment contract.

## Consequences

### Positive

- Defines a privacy-preserving commercial seam.
- Prevents accidental cross-customer leakage.
- Lets cloud improve confidence without centralizing raw project data.

### Negative / trade-offs

- Fleet value requires opt-in and enough volume.
- Aggregates can be biased by tenant mix.
- Redaction/provenance infrastructure becomes mandatory.

## Implementation slices

1. Add `manifests/fleet-confidence-schema.yaml`.
2. Add local exporter that emits dry-run aggregate rows only.
3. Add ADR-202 guard: only `sanitized-export` can leave.
4. Add cloud import contract later; no local dependency on cloud.
5. Add bias/coverage fields to summaries.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_fleet_confidence_export.py -q
scripts/cos-fleet-confidence-export --dry-run --json
```

The tests must prove `local-only` and `secret-never-touch` content cannot be
included in fleet confidence exports.
