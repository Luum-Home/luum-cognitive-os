---
adr: 317
title: COS Falsification Before Promotion
status: accepted
implementation_status: implemented
date: '2026-05-15'
extends:
  - ADR-316
  - ADR-314
supersedes: []
superseded_by: null
implementation_files:
  - docs/08-References/business/cos-vs-ai-slop-falsification.md
  - docs/09-Quality/manual-tests/cos-vs-ai-slop-falsification.md
  - scripts/cos-falsification-benchmark
  - scripts/cos_falsification_benchmark.py
tier: core
tags:
  - product-boundary
  - falsification
  - anti-slop
classification_basis: COS profiles and primitives should be promoted by falsifiable outcome evidence, not by taxonomy size.
verification:
  level: medium
  commands:
    - scripts/cos-falsification-benchmark --json --write-report
    - scripts/cos-public-claim-gate --json
  proves:
    - deterministic A/B/C benchmark produces an explicit product verdict
    - public high-risk claims remain bounded
---

# ADR-317 — COS Falsification Before Promotion

## Status

Accepted and implemented as product-governance doctrine — 2026-05-15.

<!-- SCOPE: both -->

## Decision

Promote COS primitives and profiles only when they improve measurable outcomes over a harness-literate baseline, or when they preserve a documented safety/recovery property that the baseline lacks. If minimal COS ties full COS, minimal COS wins the default because the smaller surface has lower cognitive and operational cost.

## Context

Promotion of COS primitives and tiers can drift into breadth theater if the project only counts installed surface area. The SO needs falsifiable benchmark evidence before claiming that a profile is better than minimal or vanilla operation.

## Consequences

The OS must preserve benchmarkable outcomes, publish negative results, and avoid promoting more mesh unless it improves measured reliability or developer workflow. This adds maintenance cost but keeps product claims falsifiable.

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.

## Evidence

- Command: `scripts/cos-boring-reliability --profile core --json`
- Output: `docs/06-Daily/reports/boring-reliability-audit-2026-05-03.md`

## Verification

```bash
scripts/cos-falsification-benchmark --json --write-report
scripts/cos-public-claim-gate --json
```
