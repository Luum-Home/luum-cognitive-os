---
type: concept-synthesis
source: docs/04-Concepts/architecture/cos-dispatch/test-strategy.md
provenance: "Operational companion to ADR-010 (Real-Behavior Tests Required for Every Phase 5 Sub-Phase), guarding against Phase-4-style wire-up defects that mocking would hide."
---

## What it is
The mandatory PR-acceptance test checklist for each cos-dispatch Phase 5 sub-phase (5.0-5.5), built on four non-substitutable test layers.

## Key mechanics
- Four layers: Unit (pure functions, `testing`, milliseconds), Component (one package against a real SQLite file via `t.TempDir()`), Integration (full pipeline via `dispatcher.Dispatch` with synthetic events), Binary (exec compiled binary, verify stdout/exit code/DB state via `os/exec` + `testdata/`).
- 5.0 Schema Migration + Tracker Wire-Up: Component test on real SQLite asserting row persistence; eager `failure_sequences` upsert scenarios (a-e, count increments on repeat pairs); Integration test via `dispatcher.New(WithTracker(...))`; Binary test running `cos-dispatch` subprocess and checking `patterns.db` row count; Negative test - malformed JSON exits 0 (fail-open) with zero DB rows.
- 5.1 Detectors (FalsePositive, MissingCoverage, SequenceCorrelation): Unit tests against `internal/pattern/testdata/` fixtures; Integration same-process SQLTracker->SQLDetector; Behavior test proves confidence threshold gating (0.6 pattern absent at threshold 0.7, present at 0.5); Negative - empty DB / malformed error_code doesn't panic.
- 5.2 Generator Core: Unit test compiles generated Go source via `go build` (string-diff alone is insufficient); Component test asserts `generated_artifacts` row has `enabled=0` per ADR-004 and `language='go'` per ADR-009; Behavior tests enforce `MaxPerSession` cap and `ConfidenceThreshold`; Negative - template render error writes neither file nor DB row.
- 5.3 Review CLI: Binary tests for `cos-dispatch review --list/--enable/--disable`, regression test for default subcommand happy path, Negative test for nonexistent artifact name.
- 5.4 Cursor/Devin Provider Hardening: Unit tests against vendor fixture JSON in `internal/provider/testdata/providers/`; golden-file `BuildResponse()` comparison (regenerate via `-update` flag); Integration via `dispatcher.WithProviderOverride`; Negative - malformed payloads fail open with no DB write.
- 5.5 End-to-End: 4 identical failure events across subprocess invocations sharing a temp DB assert `occurrence_count >= 4`; confidence>=0.7 pattern produces `generated_artifacts` row with `enabled=0`; `review --enable` flips to `(1, 'enabled')`; full regression of 5.0-5.4.
- Fixtures policy: live in package-owned `testdata/`; schema snapshots are committed binary SQLite files regenerated on schema change; one hook-event JSON fixture per provider; golden files updated only via explicit `-update` flag.
- CI: `go test ./...` on every PR, no build tags, no `-short`; target under 60s (remediate via `-parallel`, not skip-gating); flaky tests must be fixed or deleted within the week.
- Anti-patterns: never mock `SQLTracker` above Unit layer; never assert "no error" as success (assert observable state); never skip negative paths; never use `:memory:` SQLite above Unit layer; never gate slow tests behind `-tags=integration`.

## Relations & where used
Companion to ADR-010 (real-behavior tests); references ADR-004 (generated artifacts disabled by default) and ADR-009 (Go-only generation). Applies to the Phase 5 work tracked in cos-dispatch/README.md.

## Status / caveats
Presented as a binding checklist - "PR review blocks without these." No sub-phase completion status stated in this doc itself.
