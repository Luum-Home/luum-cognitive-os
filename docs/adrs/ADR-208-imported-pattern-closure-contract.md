---
adr: 208
title: Imported Pattern Closure Contract
status: accepted
implementation_status: partial
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: packaging, memory, and review patterns, but deferred the consumer/scheduler/
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-208 — Imported Pattern Closure Contract

## Status
Accepted


<!-- SCOPE: OS -->

**Status**: Accepted — closure audit slice active  
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

0. [x] Add a dependency-adoption gate so staged dependency manifest additions require `/repo-scout`, `/repo-forensics`, or equivalent adoption evidence before commit.
1. [x] Add `manifests/imported-pattern-closures.yaml`.
2. [x] Add `scripts/cos-imported-pattern-closure-audit`.
3. [x] Seed initial dependency-adoption preuse loop with current closure status.
4. [x] Block promotion claims when closure is missing.
5. [ ] Feed missing closure into ADR-201 maintainer proposals.

The dependency gate is the first consumer loop: it wires the existing research
skills into the actual adoption path instead of relying on an operator to
remember them. It deliberately does not claim full closure-audit coverage yet.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_dependency_adoption_gate.py tests/behavior/test_dependency_adoption_gate_cli.py -q
scripts/cos dependency adoption-gate --audit --json
python3 -m pytest tests/unit/test_imported_pattern_closure.py -q
scripts/cos-imported-pattern-closure-audit --json
```

The tests must prove a producer-only imported pattern cannot be marked active or
core.

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
