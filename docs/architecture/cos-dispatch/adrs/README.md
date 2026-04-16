# cos-dispatch Architecture Decision Records

This directory holds the ADRs for cos-dispatch — the vendor-agnostic hook dispatcher described in the parent [README](../README.md).

Each record captures one decision: the context, the decision, alternatives considered, and consequences. Records are immutable once accepted; supersession is recorded via a new ADR that references the old one.

## Index

| # | Title | Status |
|---|-------|--------|
| [001](001-reuse-klaudiush-predicates.md) | Reuse klaudiush Predicate System | Accepted |
| [002](002-transformer-separate-interface.md) | Transformer as Separate Interface from Validator | Accepted |
| [003](003-sqlite-over-jsonl.md) | SQLite over JSONL for Pattern Storage | Accepted |
| [004](004-generated-artifacts-disabled.md) | Generated Artifacts Start Disabled | Accepted |
| [005](005-typed-provider-adapters.md) | Typed Provider Adapters over Generic JSON Mapper | Accepted |
| [006](006-override-result-type.md) | `override` Result Type in Executions | Accepted — 2026-04-16 |
| [007](007-eager-failure-sequences.md) | Eager Population of `failure_sequences` | Accepted — 2026-04-16 |
| [008](008-review-subcommand.md) | `cos-dispatch review` as Subcommand in Same Binary | Accepted — 2026-04-16 |
| [009](009-go-only-auto-generation.md) | Go-Only Auto-Generation in Phase 5 | Accepted — 2026-04-16 |
| [010](010-real-behavior-tests.md) | Real-Behavior Tests Required for Every Phase 5 Sub-Phase | Accepted — 2026-04-16 |
| [011](011-phase-5-sub-phase-ordering.md) | Phase 5 Sub-Phase Ordering (5.0 First) | Accepted — 2026-04-16 |

## Groupings

**Foundation (Phases 1-4):** ADR-001, ADR-002, ADR-003, ADR-005.

**Feedback loop and auto-generation (Phase 5):** ADR-004, ADR-006, ADR-008, ADR-009.

**Phase 5 process and ordering:** ADR-007, ADR-010, ADR-011.
