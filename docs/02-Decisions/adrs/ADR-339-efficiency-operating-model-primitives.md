---
adr: 339
title: Cognitive OS Efficiency Operating Model Primitives
status: accepted
implementation_status: partial
date: '2026-06-15'
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-status
  - scripts/cos-adapter-capabilities
  - scripts/cos-projection-transaction
  - scripts/cos-skill-registry-refresh
  - scripts/cos-context-plan
  - scripts/cos-role-selection-report
  - scripts/cos-testing-capabilities
  - scripts/cos-tdd-evidence-verify
  - scripts/cos-review-workload-forecast
  - tests/unit/test_cos_efficiency_primitives.py
  - tests/red_team/portability/test_cos_efficiency_primitives.py
tier: maintainer
tags: [efficiency, adapters, context, tdd, roles, projection]
classification_basis: advisory JSON-first receipt primitives for status, adapters, context planning, role selection, testing capability detection, TDD evidence, and review workload forecasting
---

# ADR-339: Cognitive OS Efficiency Operating Model Primitives

## Status

Accepted. Initial primitives are advisory and receipt-oriented; runtime enforcement requires separate lifecycle promotion.

## Context

The product goal is to make agent work feel like an organized engineering system rather than a single chat: less wasted context, fewer unnecessary iterations, measurable token discipline, clearer work contracts, specialized roles, persistent process state, and stronger verification.

Cognitive OS already has many pieces: Graphify, context budgets, process loops, SO-wide impact eval, skill routing, tests, hooks, lifecycle metadata, and governance. The gap is a unified operator-facing layer that turns those pieces into computable status, planning, role selection, and evidence receipts.

## Decision

Adopt an advisory first slice of efficiency operating-model primitives:

- `cos-status`
- `cos-adapter-capabilities`
- `cos-projection-transaction`
- `cos-skill-registry-refresh`
- `cos-context-plan`
- `cos-role-selection-report`
- `cos-testing-capabilities`
- `cos-tdd-evidence-verify`
- `cos-review-workload-forecast`
- `cos-so-impact-eval catalog`

The primitives must be harness-neutral, JSON-first, and receipt-oriented. They are not blocking enforcement in this ADR. They are a portable contract layer that stronger hooks and workflow dispatchers can consume later.

## Consequences

- Product claims remain evidence-tiered: structural, directional, measured, then product.
- `cos-so-impact-eval` is the proof plane for measured claims.
- Adapter and projection claims must come from explicit capability and transaction receipts, not broad documentation language.
- Strict TDD is enabled by detected test capability, not as an always-on prompt rule.

## Alternatives rejected

- Add only prompt guidance. Rejected because the operating model needs computable receipts that CLIs, IDEs, and hooks can inspect.
- Make the whole slice blocking immediately. Rejected because adapter capabilities and cross-harness enforcement differ and must be promoted after evidence.
- Hardcode stack assumptions. Rejected because projects installing Cognitive OS may use any language, test runner, or IDE surface.

## Verification

```bash
python3 -m pytest tests/unit/test_cos_efficiency_primitives.py tests/red_team/portability/test_cos_efficiency_primitives.py -q
python3 -m pytest tests/contracts/test_primitive_scope_classification.py tests/contracts/test_primitive_harness_coverage_contract.py -q
scripts/cos-status --json
```

Implementation files include the `scripts/cos-*` efficiency primitives, their unit tests, lifecycle rows, and generated projection receipts.
