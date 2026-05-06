# ADR-206 — Aspirational Claim Decommission Gate

<!-- SCOPE: OS -->

**Status**: Proposed  
**Date**: 2026-05-06  
**Related**: ADR-031, ADR-061, ADR-133, ADR-198, ADR-201  
**Source**: `.cognitive-os/strategy/research/03-aspirational-dormant.md`, `.cognitive-os/strategy/00-first-approach.md`, `.cognitive-os/strategy/02-pre-launch-playbook.md`

---

## Context

Research found a high dormant/aspirational ratio and dangerous public-facing
claims around autonomous MAPE-K loops, weekly self-improvement, and automatic
reconfiguration. ADR-031 classifies reality, but classification alone does not
remove unsafe product claims from public docs or launch surfaces.

A trust product cannot launch with claims that its own evidence classifies as
aspirational or dormant.

## Decision

Add a release-facing **Aspirational Claim Decommission Gate**.

Any public claim that references autonomous self-improvement, automatic
reconfiguration, MAPE-K control, cross-instance learning, or skill evolution must
link to evidence classified `REAL`. If evidence is `DORMANT` or `ASPIRATIONAL`,
the claim must be either:

- removed from public docs;
- demoted to future work;
- rewritten as propose-only / manual / experimental;
- backed by new evidence and reclassified.

## Gate behavior

The gate scans public docs, README, landing-copy candidates, and release notes.
It fails release-readiness if high-risk phrases appear without a valid evidence
reference.

Private strategy docs are excluded from public-claim enforcement but may seed the
claim inventory.

## Consequences

### Positive

- Marketing aligns with runtime truth.
- ADR-031 evidence becomes operational, not just descriptive.
- Launch risk drops before public repo release.

### Negative / trade-offs

- Some compelling claims must be delayed.
- Docs may become less ambitious until evidence improves.

## Implementation slices

1. Add `manifests/public-claim-evidence.yaml`.
2. Add `scripts/cos-public-claim-gate`.
3. Seed high-risk claims from the strategy research top-danger list.
4. Wire into release/readiness checks, not every local edit.
5. Add suppression format requiring expiry and evidence owner.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_public_claim_gate.py -q
scripts/cos-public-claim-gate --json
```

The test fixture must prove unbacked MAPE-K/autonomous self-improvement claims
fail and propose-only claims pass.
