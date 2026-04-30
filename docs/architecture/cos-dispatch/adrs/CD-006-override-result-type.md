# ADR-006: `override` Result Type in Executions

## Status

Accepted — 2026-04-16

## Context

The FalsePositive detector (Phase 5.1) needs a reliable signal for cases where a validator returned `warn` or `fail` and a human (or a downstream system) chose to proceed anyway. Without such a signal, there is no ground truth that distinguishes a genuinely useful warning from one that users consistently dismiss.

The existing `executions.result` CHECK constraint allowed only `pass`, `fail`, `warn`, and `transform`. None of these capture the dismissal event.

## Decision

Add `'override'` as a fifth allowed value in the `executions.result` CHECK constraint. It is populated by downstream systems (including agents, CLIs, and hook consumers) when they choose to proceed despite a validator's warn/fail result. The detector counts overrides per `validator_name` and flags artifacts whose dismissal rate exceeds a threshold as FalsePositive candidates.

## Alternatives Considered

1. **Inference heuristic** — infer dismissal from patterns like "warn-only result with no follow-up escalation". Rejected: no clean threshold; both false positives and false negatives are high, and the signal is indirect.
2. **Separate `overrides` table with FK** — store overrides as their own rows joined to executions. Rejected: an extra join per analysis cycle with no performance justification at current volume. A nullable column on the existing table is simpler.

## Consequences

- Schema change is additive; no existing rows are invalidated.
- Downstream systems must opt in to reporting overrides. Until they do, FalsePositive detection degrades to inference-only and loses quality. This is an acceptable short-term trade-off.
- The Phase 5 feedback loop (see ADR-005 typed provider adapters and ADR-004 generated artifacts disabled) has a concrete event it can record when a human dismisses a generated validator's output.
- The enum is now 5 values; any code that switches on `result` must handle `override` explicitly.
