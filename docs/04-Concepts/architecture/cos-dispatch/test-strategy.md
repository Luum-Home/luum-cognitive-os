# cos-dispatch Test Strategy (Phase 5)

## Overview

This document is the operational companion to
[ADR-010: Real-Behavior Tests Required for Every Phase 5 Sub-Phase](adrs/010-real-behavior-tests.md).
It is the working reference for anyone implementing a Phase 5 sub-phase — the
checklist your PR must satisfy before it can be reviewed. Authors should treat
the per-sub-phase lists below as acceptance criteria in the sense of
`rules/acceptance-criteria.md`: measurable, verifiable, and complete.

## Test Layers

We use four distinct test layers. Each has a different scope, speed, and
failure-mode footprint. All four exist in the repo simultaneously — they are
not substitutes.

| Layer | Scope | Tools | Example |
|---|---|---|---|
| **Unit** | Pure functions, table-driven, no I/O | `testing` | `detector.detectMissingCoverage` on in-memory input structs |
| **Component** | One Go package against a real DB file | `testing` + `os.TempDir` | `tracker_test.go` opens SQLite at `t.TempDir() + "/patterns.db"` |
| **Integration** | Full pipeline via `dispatcher.Dispatch` | `testing` + synthetic hook events | provider → validator → tracker chain with a temp DB |
| **Binary** | Exec the compiled binary, verify stdout + exit code + DB state | `testing` + `os/exec` + `testdata/` | `main_test.go` runs `cos-dispatch` with a fixture event |

Unit tests are milliseconds and catch pure-logic regressions. Component tests
catch driver, schema, and connection-pool issues (the class of defect that
`:memory:` hides). Integration tests catch wire-up misses (the Phase 4 defect).
Binary tests catch flag parsing, exit codes, stdout format, and packaging.
Each layer catches what the layer below cannot.

## Per-Sub-Phase Test Requirements

Minimum tests required before a sub-phase can be marked complete. "Minimum"
means PR review blocks without these; authors may (and should) add more.

### 5.0 — Schema Migration + Tracker Wire-Up

- [ ] **Component**: `tracker_test.go` opens a real SQLite file at
  `t.TempDir() + "/p.db"`, records an `ExecutionRecord` with
  `result = "override"`, flushes, and asserts the row is present with
  `SELECT result FROM executions WHERE id = ?` returning `"override"`.
- [ ] **Component**: eager `failure_sequences` — three flush scenarios:
  (a) empty batch → zero rows; (b) single failure → zero rows; (c) two
  consecutive failures in the same session with distinct error codes → one
  row with `count = 1`; (d) same pair flushed twice → `count = 2` via upsert;
  (e) two failures in different sessions → zero rows.
- [ ] **Integration**: construct `dispatcher.New(...)` with
  `WithTracker(trackerFromTempFile)`, call `Dispatch(ctx, rawEvent)`, then
  `SELECT COUNT(*) FROM executions` returns the expected row count.
- [ ] **Binary**: `main_test.go` runs `go run ./cmd/cos-dispatch` as a
  subprocess with a synthetic stdin event and `CLAUDE_PROJECT_DIR` pointed at
  `t.TempDir()`. Asserts the binary exits 0 AND `patterns.db` exists in the
  temp project dir AND contains at least one row in `executions`.
- [ ] **Negative**: malformed hook JSON on stdin → binary exits 0 (fail-open,
  per `main.go`) BUT writes no partial DB row. Verify with
  `SELECT COUNT(*) FROM executions` → 0.

### 5.1 — Complete Detectors (FalsePositive, MissingCoverage, SequenceCorrelation)

- [ ] **Unit**: each detector runs against a pre-populated SQLite fixture in
  `internal/pattern/testdata/` covering at least one positive and one
  zero-pattern case per detector.
- [ ] **Integration**: same-process test writes records via `SQLTracker`, then
  opens a `SQLDetector` against the same temp DB file and asserts the
  expected pattern appears in the result. No mocks, no separate fixture.
- [ ] **Behavior**: confidence threshold is respected. A pattern with
  `confidence = 0.6` must NOT appear when the detector is invoked with
  `threshold = 0.7`; it must appear at `threshold = 0.5`.
- [ ] **Negative**: empty DB (schema only, no rows) returns an empty pattern
  slice and no panic. Malformed `error_code` values (e.g. empty strings) are
  skipped, not crashed on.

### 5.2 — Generator Core

- [ ] **Unit**: generator with synthetic `Pattern` structs emits Go source
  text. The test writes that output to `t.TempDir()` and runs `go build` on
  it via `os/exec`; build must exit 0. A test that only string-diffs the
  output is insufficient.
- [ ] **Component**: after generation, `generated_artifacts` contains a row
  with `enabled = 0` (per ADR-004), correct `language = 'go'` (per ADR-009),
  and a non-null `source_pattern_id`.
- [ ] **Behavior**: `MaxPerSession` cap is enforced. Given 5 eligible
  patterns with `MaxPerSession = 3`, exactly 3 artifacts are created.
- [ ] **Behavior**: `ConfidenceThreshold` is enforced. Patterns below the
  threshold produce no artifacts and no files on disk.
- [ ] **Negative**: template rendering error on a malformed pattern returns
  an error to the caller and writes nothing (neither file nor DB row).
  Assert DB row count is unchanged and the target file does not exist.

### 5.3 — Review CLI Subcommand

- [ ] **Binary**: `cos-dispatch review --list` against a temp DB pre-seeded
  with two artifacts exits 0 and stdout contains both artifact names.
- [ ] **Binary**: `cos-dispatch review --enable NAME` flips `enabled` from 0
  to 1 for that row; verify via direct SQL query on the temp DB after the
  subprocess exits.
- [ ] **Binary**: `cos-dispatch review --disable NAME` sets
  `feedback = 'disabled'` and leaves `enabled = 0`.
- [ ] **Binary**: default subcommand (no args, stdin event) preserves the
  Phase 4 dispatch path — a regression test that matches the existing
  `main_test.go` happy path.
- [ ] **Negative**: `cos-dispatch review --enable DOES_NOT_EXIST` exits
  non-zero, writes nothing to the DB, and emits a diagnostic to stderr.

### 5.4 — Cursor / Devin Provider Hardening

- [ ] **Unit**: each provider's `Detect()` runs against vendor-shaped fixture
  JSON committed under `internal/provider/testdata/providers/`
  (`cursor-beforeshellexecution.json`, `devin-pretool.json`, etc.).
- [ ] **Unit**: `BuildResponse()` emits a spec-conformant envelope compared
  against a golden file in `testdata/` — diff-testable, regenerate with an
  explicit `-update` flag.
- [ ] **Integration**: full pipeline run with each provider selected via
  `dispatcher.WithProviderOverride(...)`; tracker records the correct
  `tool_type` for the synthesized event.
- [ ] **Negative**: malformed Cursor and malformed Devin payloads each
  return a provider error; the dispatcher falls open with no DB write and
  exit code 0.

### 5.5 — Final End-to-End

- [ ] **Binary**: feed four identical failure events into `cos-dispatch` as
  separate subprocess invocations sharing the same temp DB; verify a row
  appears in `detected_patterns` with `occurrence_count >= 4`.
- [ ] **Binary**: when the resulting pattern has `confidence >= 0.7`, a row
  appears in `generated_artifacts` with `enabled = 0` after the generator
  runs.
- [ ] **Binary**: run `review --enable <name>`, then `SELECT enabled,
  feedback FROM generated_artifacts` returns `(1, 'enabled')`.
- [ ] **Regression**: all acceptance checks from 5.0 through 5.4 still pass
  in the same `go test ./...` run.

## Fixtures Policy

- Fixtures live under `testdata/` inside the package that owns them
  (Go's convention; the test tooling ignores these directories).
- **Schema snapshots**: an empty SQLite database with the current schema
  applied, committed as a binary file. Regenerate on any schema change; the
  PR that changes the schema updates the fixture in the same commit.
- **Hook event fixtures**: one JSON file per provider
  (`claude.json`, `cursor.json`, `devin.json`, `codex.json`,
  `gemini.json`) representing a canonical `PreToolUse`-equivalent event.
- **Golden files**: response envelopes the binary is expected to emit,
  compared byte-for-byte. Golden files are updated with an explicit
  `-update` flag, never silently.

## CI Integration

- All tests run on every pull request: `go test ./...` with no build tags
  and no `-short` flag.
- Target budget: full suite under 60 seconds on CI. If we exceed this, the
  remediation is parallelization (`go test -parallel`), not skip-gating
  integration tests.
- Flake policy: a test that flakes must be fixed or deleted in the same
  week it was reported. Silent retries are forbidden. A flaky test is a
  broken test.

## Anti-Patterns

- DO NOT mock `SQLTracker` in tests written for any of the layers above
  Unit. The tracker is the system under test for half of Phase 5; mocking
  it reproduces the Phase 4 wire-up defect.
- DO NOT assert "no error" as a success condition. Assert observable state:
  DB row counts, file contents, exit codes, stdout bytes.
- DO NOT skip negative paths. Every sub-phase ships at least one error-case
  test. Reviewers will block PRs that omit this.
- DO NOT use `:memory:` for Component, Integration, or Binary layer tests.
  In-memory SQLite hides driver, schema-apply, and connection-pool issues.
  `:memory:` is permitted only for pure unit tests of query logic that do
  not exercise the lifecycle of the database.
- DO NOT add `-tags=integration` gating to hide slow tests. Opt-in is
  opt-out in practice.
