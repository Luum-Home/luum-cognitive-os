# ADR-339: Cognitive OS Efficiency Operating Model Primitives

- Status: Accepted
- Date: 2026-06-15

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

## Validation

- Unit tests cover temporary consumer-project fixtures for stack detection, skill registry indexing, context planning, role selection, TDD evidence verification, projection transaction planning, status aggregation, and SO-impact catalog output.
- Lifecycle rows remain `candidate/advisory` until runtime projection and cross-harness enforcement are proven.
