# cos-dispatch Architecture Decision Records

This directory holds the ADRs for cos-dispatch — the vendor-agnostic hook dispatcher described in the parent [README](../README.md).

Each record captures one decision: the context, the decision, alternatives considered, and consequences. Records are immutable once accepted; supersession is recorded via a new ADR that references the old one.

## Naming Convention — `CD-NNN` prefix

These ADRs use a local `CD-NNN` numbering sequence (e.g. `CD-001-reuse-klaudiush-predicates.md`).

**They are NOT project-level ADRs** and must not be cited by bare `ADR-NNN` references in project files. The `CD-` prefix makes this isolation machine-readable: any tool performing a recursive ADR search that finds a `CD-NNN` file can identify it as a subsystem-internal record, not a project governance decision.

This convention was established by ADR-087 (ADR Namespace Consolidation, 2026-04-30). Files were renamed from `NNN-slug.md` to `CD-NNN-slug.md` as part of that migration.

If this subsystem is ever dissolved or fully absorbed into project core, a future project-level ADR must decide whether to promote these records to root namespace slots or archive them in place.

## Index

| # | Title | Status |
|---|-------|--------|
| [CD-001](CD-001-reuse-klaudiush-predicates.md) | Reuse klaudiush Predicate System | Accepted |
| [CD-002](CD-002-transformer-separate-interface.md) | Transformer as Separate Interface from Validator | Accepted |
| [CD-003](CD-003-sqlite-over-jsonl.md) | SQLite over JSONL for Pattern Storage | Accepted |
| [CD-004](CD-004-generated-artifacts-disabled.md) | Generated Artifacts Start Disabled | Accepted |
| [CD-005](CD-005-typed-provider-adapters.md) | Typed Provider Adapters over Generic JSON Mapper | Accepted |
| [CD-006](CD-006-override-result-type.md) | `override` Result Type in Executions | Accepted — 2026-04-16 |
| [CD-007](CD-007-eager-failure-sequences.md) | Eager Population of `failure_sequences` | Accepted — 2026-04-16 |
| [CD-008](CD-008-review-subcommand.md) | `cos-dispatch review` as Subcommand in Same Binary | Accepted — 2026-04-16 |
| [CD-009](CD-009-go-only-auto-generation.md) | Go-Only Auto-Generation in Phase 5 | Accepted — 2026-04-16 |
| [CD-010](CD-010-real-behavior-tests.md) | Real-Behavior Tests Required for Every Phase 5 Sub-Phase | Accepted — 2026-04-16 |
| [CD-011](CD-011-phase-5-sub-phase-ordering.md) | Phase 5 Sub-Phase Ordering (5.0 First) | Accepted — 2026-04-16 |

## Groupings

**Foundation (Phases 1-4):** CD-001, CD-002, CD-003, CD-005.

**Feedback loop and auto-generation (Phase 5):** CD-004, CD-006, CD-008, CD-009.

**Phase 5 process and ordering:** CD-007, CD-010, CD-011.
