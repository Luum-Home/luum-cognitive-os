# ADR-207 — Skill Ecosystem Performance and Lifecycle Closure

<!-- SCOPE: OS -->

**Status**: Proposed  
**Date**: 2026-05-06  
**Related**: ADR-090, ADR-095, ADR-174, ADR-180, ADR-188, ADR-201, ADR-204  
**Source**: `.cognitive-os/strategy/research/07-skill-ecosystem-evolution.md`, `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md`

---

## Context

The skill ecosystem has scaffolding for creation, rewrite, promotion, demotion,
and router confidence, but the loops are open. No skill has been auto-generated
and promoted, no skill rewrite has been observed, router confidences are static,
and skill-feedback input is corrupted.

ADR-201 provides the maintainer loop. ADR-204 protects reward quality. This ADR
applies both specifically to skills.

## Decision

Introduce a canonical **Skill Performance Ledger** as a projection of the ADR-201
performance ledger, with explicit lifecycle actions for skills.

Every skill lifecycle proposal must be based on validated rows for:

- invocation count;
- accepted/ignored/overridden router suggestions;
- success/failure outcomes;
- verification pass rate;
- trust report quality;
- time/cost;
- operator feedback;
- known corrupt/suspect input count.

## Lifecycle outcomes

Allowed outcomes are:

- `maintain`;
- `rewrite-proposal`;
- `router-confidence-change-proposal`;
- `promote-sandbox-to-advisory-proposal`;
- `demote-or-deprecate-proposal`;
- `quarantine-signal-source`.

No skill is auto-promoted, auto-deprecated, or auto-rewritten without human
approval and tests.

## Consequences

### Positive

- Skill evolution becomes measurable instead of aspirational.
- Router calibration gains real feedback inputs.
- Corrupt skill metrics stop poisoning downstream lifecycle decisions.

### Negative / trade-offs

- Existing skills may have insufficient data and remain unscored.
- The first useful output may be signal repair, not skill improvement.

## Implementation slices

1. Fix skill-feedback identity extraction and validate against known skill ids.
2. Add `scripts/cos-skill-performance-ledger`.
3. Record structured router accept/ignore/override events.
4. Generate one rewrite proposal from validated evidence in dry-run mode.
5. Add deprecation proposal path with archive/tombstone requirements.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_skill_performance_ledger.py -q
python3 -m pytest tests/behavior/test_skill_lifecycle_closure.py -q
scripts/cos-skill-performance-ledger --json
```

The tests must prove corrupt `skill` identities are quarantined and cannot
produce rewrite or confidence-change proposals.
