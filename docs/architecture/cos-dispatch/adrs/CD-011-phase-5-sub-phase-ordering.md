# ADR-011: Phase 5 Sub-Phase Ordering (5.0 First)

## Status

Accepted — 2026-04-16

## Context

Phase 5 was originally scoped as "auto-generator + remaining providers + last 3 detectors" over ~8 days. Planning-phase exploration surfaced two facts that invalidated the original ordering:

1. `SQLTracker` exists in `internal/pattern/` but was never wired into `cmd/cos-dispatch/main.go`. Phase 4 shipped a tracker, but no data is actually flowing into it.
2. `failure_sequences` is empty (see ADR-007) and `executions.result` lacks `override` (see ADR-006).

Any detector work in Phase 5.1 would therefore run against an empty database and fail silently. Any generator work in Phase 5.2 would be validated against synthetic fixtures rather than real data.

## Decision

Insert a new sub-phase 5.0 before 5.1, dedicated to unblocking end-to-end data flow. Phase 5 becomes six sub-phases:

| Sub-phase | Scope |
|-----------|-------|
| 5.0 | Schema migration (add `override` per ADR-006), eager `failure_sequences` per ADR-007, wire `SQLTracker` into `main.go`, E2E smoke test |
| 5.1 | Complete detectors (FalsePositive, MissingCoverage, SequenceCorrelation) |
| 5.2 | Generator core (Go-only per ADR-009) |
| 5.3 | Review CLI + `cos-dispatch` subcommand refactor per ADR-008 |
| 5.4 | Cursor and Windsurf provider hardening (building on ADR-005) |
| 5.5 | Final E2E verification |

## Alternatives Considered

1. **Include tracker wire-up inside 5.1** — 5.1 becomes a mixed change (infra wire-up + new detector logic). Reviews are harder and a failure in one motion stalls the other. Rejected.
2. **Wire tracker in 5.5, as originally planned** — sub-phases 5.1 through 5.4 proceed on an empty database. No real validation of data flow until the very end of the phase, when the cost of rework is highest. Rejected.

## Consequences

- Phase 5 grows from five sub-phases to six. Total effort is roughly unchanged; the work in 5.0 was already implicit in 5.5.
- The earliest possible signal that data flows end-to-end arrives after 5.0 rather than after 5.5.
- Detector implementation in 5.1 is validated against real populated tables, not synthetic fixtures.
- The review CLI in 5.3 has real artifacts to operate on during manual testing.
- This ADR depends on ADR-006, ADR-007, ADR-008, and ADR-009; if any of those change materially, the 5.0 scope should be revisited.
