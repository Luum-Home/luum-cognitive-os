# ADR-010: Real-Behavior Tests Required for Every Phase 5 Sub-Phase

**Status**: Accepted (2026-04-16)

## Context

During Phase 4 (Pattern Tracking) we landed `SQLTracker` and `SQLDetector`, wired
the tracker into `dispatcher.Dispatcher` via `WithTracker(...)`, and shipped 11
passing unit tests. All tests were green. Yet a latent defect remained: the
production entry point (`cmd/cos-dispatch/main.go`) was never actually passing
the tracker into the dispatcher in a way the end-to-end binary exercised. The
tracker existed, the dispatcher accepted it, the tests mocked the glue — and the
integration path between the two was dead. Unit tests did not surface this
because every test constructed its own in-process dispatcher with an in-memory
tracker; nobody ran the compiled binary and asked the database "did you observe
this session?"

This is the canonical failure mode of mock-heavy test suites: each layer is
individually correct, the glue is nobody's responsibility, and the system ships
broken.

The user's directive for Phase 5 is unambiguous: *"tests automatizados que
prueben el comportamiento real"* — automated tests that verify real behavior.
Not mock-based. Not `:memory:`-only (which hides driver, schema-apply and
connection-pool issues). Not happy-path-only.

Phase 5 is higher risk than Phase 4. It introduces:

- **5.0** — Schema migration (`override` result, eager `failure_sequences`
  flushing) plus the `SQLTracker` wire-up we just caught missing.
- **5.1** — `FalsePositive`, `MissingCoverage`, `SequenceCorrelation` detectors
  that read the schema produced by 5.0.
- **5.2** — Code generator that writes Go files to disk under
  `generated/` and inserts rows into `generated_artifacts` with `enabled=0`
  (per ADR-004, ADR-009).
- **5.3** — `cos-dispatch review` subcommand with CLI-observable state
  transitions on the `enabled` column (per ADR-008).
- **5.4** — Cursor and Windsurf provider adapters that must conform to the
  typed envelope contract (per ADR-005).
- **5.5** — Final end-to-end: failure events → detected patterns → generated
  artifacts → human review → enabled.

Every one of these sub-phases has a unit-test-vs-real-behavior gap identical in
shape to the Phase 4 defect. Closing that gap across the board is not optional.

## Decision

Every Phase 5 sub-phase (5.0 through 5.5) MUST include real-behavior tests
that satisfy ALL of the following:

1. **At least one test per sub-phase executes the actual compiled binary**
   (via `os/exec` from a `_test.go` file) OR exercises the full
   `dispatcher.Dispatch(ctx, raw)` pipeline against a **real temp-file SQLite
   database** (not `:memory:`). The test writes to a path produced by
   `t.TempDir()` and the cleanup removes the file.
2. **Observable state is verified, not inferred.** A test is not allowed to
   assert only "no error returned." It must query the DB with SQL, stat the
   generated file on disk, or parse the binary's stdout — and compare against
   an expected value.
3. **At least one negative path per sub-phase.** Error case, permission denied,
   malformed input, constraint violation, missing file, nonexistent record.
   Happy-path-only is forbidden.
4. **Deterministic fixtures.** No network, no wall-clock dependencies that
   flake, no reliance on external binaries. Provider payloads, hook events,
   and schema snapshots live in `testdata/` and are committed to the repo.
5. **Runs in CI by default.** No `-tags=integration` gating. No
   `if testing.Short() { t.Skip() }` wrapping the integration tests. Opt-in
   integration is opt-out integration in practice.

## Alternatives

- **Unit tests with mocks only, integration as a follow-up epic** — rejected.
  This is exactly the model that produced the Phase 4 wire-up miss. Follow-up
  integration epics slip; the gap goes to production.
- **End-to-end tests only, drop unit tests** — rejected. Unit tests catch
  pure-logic regressions in milliseconds (e.g. confidence-threshold math,
  template rendering). Losing them would slow the tight-loop feedback that
  makes Go development productive.
- **Integration tests behind a build tag (`-tags=integration`) defaulted off** —
  rejected. Opt-in CI steps are routinely forgotten, misconfigured, or silently
  removed during refactors. The tests must run on every PR with zero ceremony.
- **Mock `SQLTracker` in higher-level tests** — rejected. `SQLTracker` IS the
  system under test for half of Phase 5. Mocking it reproduces the Phase 4
  defect one layer up.

## Consequences

- **Each sub-phase delivery is larger.** Tests ship alongside code, not in a
  follow-up PR. This is the intended cost: defects surface hours after they
  are written, not weeks.
- **CI time grows.** Acceptable at current volume. Budget: full suite under 60
  seconds on CI. If we exceed it, the response is to parallelize Go tests
  (`go test -parallel`) or split packages, not to skip coverage.
- **`testdata/` directories are committed.** Schema snapshots, hook-event
  fixtures, and provider-response golden files become part of the repo.
  Regenerate on schema change and review the diff as part of the PR.
- **Auto-generated artifacts (Phase 5.2) inherit this rule.** Generator output
  is verified by compiling and running the generated code (e.g. `go build` on
  the emitted file), not by string-comparing against a snapshot. A test that
  only diffs strings accepts generated garbage.
- **Negative-path coverage becomes a reviewable PR artifact.** Reviewers are
  expected to ask "where is the error-case test?" and block the PR if absent.
- **The policy outlives Phase 5.** Post-Phase-5 features (additional detectors,
  new providers) adopt the same rule. `docs/architecture/cos-dispatch/test-strategy.md`
  is the operational companion to this ADR.

## Cross-References

- [ADR-005: Typed provider adapters](005-typed-provider-adapters.md) — typed
  envelope contract verified by binary tests in Phase 5.4.
- [ADR-006 / ADR-007] — pattern detector additions covered by Phase 5.1 tests.
- [ADR-008: Review subcommand](008-review-subcommand.md) — CLI behavior
  verified end-to-end in Phase 5.3.
- [ADR-009: Go-only auto-generation](009-go-only-auto-generation.md) —
  generated Go must build, enforced by Phase 5.2 tests.
- [test-strategy.md](../test-strategy.md) — concrete per-sub-phase test plan
  implementing this policy.
