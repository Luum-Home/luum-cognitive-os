# ADR-007: Eager Population of `failure_sequences`

## Status

Accepted — 2026-04-16

## Context

The `failure_sequences` table exists in `schema.sql` (see ADR-003 for the SQLite-over-JSONL choice), but `SQLTracker.flushLocked()` never inserts into it. The table is the primary input for the SequenceCorrelation detector scheduled in Phase 5.1, which identifies cases where fixing error A consistently causes error B (for example, adding a lint fix that breaks a test).

Without this data, the detector has nothing to analyze. Two natural strategies exist: write to `failure_sequences` at flush time, or reconstruct sequences on demand from the `executions` table.

## Decision

Populate `failure_sequences` eagerly from `Tracker.flushLocked()`. On each flush batch, scan for consecutive failure pairs within the same `session_id`, and upsert `(source_code, target_code)` rows with an incrementing `count` and an updated `last_seen`.

"Consecutive" here means adjacent entries in the same flush batch with the same session. Sequences that span multiple flushes in the same session are out of scope for Phase 5 and will be revisited if detector quality suffers.

## Alternatives Considered

1. **Lazy reconstruction from `executions`** in the Detector — re-query the execution log every analysis cycle. Rejected: time-window drift between runs, repeated scans of a growing table, and harder-to-reason-about correctness (what counts as "consecutive" when executions flow in from multiple sessions?).
2. **Separate async processor** that tails `executions` and writes `failure_sequences` — rejected: premature operational complexity. A dedicated process adds failure modes (process crash, lag, restart semantics) without a proven performance need.

## Consequences

- The write path does marginally more work per flush: one additional scan over the batch plus the upserts. Measured overhead is expected to be negligible at current flush sizes.
- Cross-session sequences and cross-batch sequences are missed until a future ADR addresses multi-flush tracking.
- The SequenceCorrelation detector in Phase 5.1 can be implemented against a pre-computed table rather than re-deriving from `executions`, keeping the detector logic simple.
- If flushLocked becomes a hotspot, the sequence computation is easy to extract into a separate goroutine.
