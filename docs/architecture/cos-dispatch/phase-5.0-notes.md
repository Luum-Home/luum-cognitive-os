# Phase 5.0 Implementation Notes

## What Was Changed

### 1. `override` result type added to schema

- `docs/architecture/cos-dispatch/schema.sql`: Added a `CHECK` constraint to `executions.result` that lists all valid values: `pass`, `fail`, `warn`, `transform`, `override`.
- `internal/pattern/tracker.go` (`schemaSQL`): Mirrored the same CHECK constraint in the embedded Go schema string.
- `internal/pattern/types.go`: Added `ResultOverride = "override"` constant alongside the existing four result constants.

### 2. `failure_sequences` populated eagerly in `flushLocked()`

- `internal/pattern/tracker.go`: Added `insertFailureSequences(*sql.Tx, []ExecutionRecord)` helper. Called inside `flushLocked()` after the `executions` INSERT loop, within the same transaction.
- Logic: scans adjacent pairs in the flush buffer where both records share the same `session_id` and both are failures (`fail` or `warn`) with non-empty `ErrorCode`. On a match, UPSERTs into `failure_sequences` (INSERT … ON CONFLICT DO UPDATE SET count = count + 1).
- Cross-session sequences are intentionally excluded — the pair check requires `prev.SessionID == cur.SessionID`. Phase 5.1 can extend this with cross-session windowing.

### 3. SQLTracker wired in `main.go`

- `cmd/cos-dispatch/main.go`: Added pattern tracker construction when `cfg.Patterns.Enabled && cfg.Patterns.DBPath != ""`. Non-fatal: logs a warning and proceeds without tracking if `pattern.NewTracker` fails.
- Refactored `main()` → delegates to `run() int`. This ensures `defer tracker.Close()` executes before `os.Exit` is called. The original code used `os.Exit` directly in `main()`, which bypasses defers — meaning the tracker buffer would never flush and the schema would never be written to disk.
- Also wired `impl.RegisterDefaults()` to register the six built-in Phase-3 validators. Without this, the tracker would never receive records (dispatcher skips `recordExecutions` when no validators matched).

## `override` Semantics for Phase 5.1

The `override` result type signals that a `warn` or `fail` validator result was explicitly dismissed by a human operator or a downstream system (e.g., a CI bypass flag, an interactive approval in the hook UI). It is NOT emitted automatically by any current validator — callers must explicitly set `Result: pattern.ResultOverride` when recording an overridden execution.

In Phase 5.1, the `FalsePositive` detector will query the ratio of `override` rows to `fail`+`warn` rows for each `validator_name`. A high ratio (many overrides, few true blocks) is a strong signal that the validator is miscalibrated. The `first_seen`/`last_seen` timestamps on those rows enable time-window analysis.

## Design Decisions

- **Same-transaction sequence insert**: `insertFailureSequences` runs inside the same `flushLocked()` transaction as the `executions` INSERT. This ensures atomicity: if the sequence upsert fails, the whole batch rolls back. No partial state.
- **Empty ErrorCode skipped**: pairs where either record has an empty `ErrorCode` are skipped for sequences. Without a stable code, the source/target pair is not meaningfully queryable by Phase 5.1 detectors.
- **`warn` counts as failure for sequences**: the pair-detection treats `warn` as a failure alongside `fail`. This is intentional — a sequence of warnings is as indicative of a cascading issue as a sequence of hard failures.
- **`run()` returns int**: the refactor from `os.Exit` in `main()` to `return` in `run()` is a permanent improvement. All future exit points should add cases to `run()`, not call `os.Exit` directly.
