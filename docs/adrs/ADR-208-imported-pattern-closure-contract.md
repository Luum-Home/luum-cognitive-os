# ADR-208 — Imported Pattern Closure Contract

<!-- SCOPE: OS -->

**Status**: Proposed  
**Date**: 2026-05-06  
**Related**: ADR-074, ADR-076, ADR-078, ADR-080, ADR-095, ADR-096, ADR-102, ADR-201  
**Source**: `.cognitive-os/strategy/research/05-hermes-imitation-forensics.md`, `.cognitive-os/strategy/research/06-external-patterns-benchmark.md`

---

## Context

The Hermes forensics found a repeated pattern: Cognitive OS imported provider,
packaging, memory, and review patterns, but deferred the consumer/scheduler/
evaluator that closes the loop. Imported producers are useful, but producers
without consumers become dormant surface.

## Decision

Every imported external pattern must ship with a **Closure Contract** before it
can be promoted beyond lab/sandbox.

The contract must name:

- imported source and license posture;
- COS target primitive;
- producer;
- consumer;
- scheduler or trigger;
- evaluator/reward signal;
- lifecycle owner;
- contract tests;
- demotion path if closure does not happen.

## Enforcement

A new pattern may land as research or lab code without closure. It may not be
claimed as active, core, blocking, default-visible, or self-improving until the
closure contract passes.

## Consequences

### Positive

- Prevents supplier-only imitation.
- Forces every imported loop to name how it will be consumed and evaluated.
- Reduces dormant primitive growth.

### Negative / trade-offs

- Slows incorporation of external ideas.
- Some imported utilities remain lab-only longer.

## Implementation slices

1. Add `manifests/imported-pattern-closures.yaml`.
2. Add `scripts/cos-imported-pattern-closure-audit`.
3. Seed historical Hermes-derived patterns with current closure status.
4. Block promotion claims when closure is missing.
5. Feed missing closure into ADR-201 maintainer proposals.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_imported_pattern_closure.py -q
scripts/cos-imported-pattern-closure-audit --json
```

The tests must prove a producer-only imported pattern cannot be marked active or
core.
