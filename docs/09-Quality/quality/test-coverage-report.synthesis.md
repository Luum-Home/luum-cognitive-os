---
type: quality-synthesis
source: docs/09-Quality/quality/test-coverage-report.md
provenance: "Point-in-time test coverage and status audit (run 2026-05-07, updated 2026-05-08) produced for pre-public-readiness checklist item C4, documenting suite-by-suite pass/fail/timeout state and blocking recommendations."
---

## What it is
A dated audit report (commit `418fb217`, branch `session/1ad21811-c5h2-rescue`, run 2026-05-07) covering the full Python/Go test estate — roughly 17,519 collected Python tests plus three Go test trees — for pre-public-readiness checklist item C4.

## Key mechanics
- **Executive summary**: all Go suites pass green (root, `cmd/cos`, `cmd/cos-test`); `go vet` clean; `gofmt -l` flags one file; the portability red-team lane is 165/0 passed/failed (updated 2026-05-08, resolving 5 prior failures); the audit lane and full `pytest` collection both hit resource-exhaustion timeouts and cannot complete single-shot at default settings; `ruff check` reports 1,494 findings (1,277 `F401` unused-import, 217 `F841` unused-local), none runtime errors.
- **Per-suite table**: full pytest INCOMPLETE (collection interrupt + timeouts, 17,519 collected); relaxed full pytest PARTIAL (>12 min, not finished in harness window); `tests/audit/` INCOMPLETE (timeout inside `glob.scandir`, ~1,500+ observed passing before kill); `tests/red_team/portability/` PASS (165/165, resolved 2026-05-08); all three Go trees PASS (cached); `gofmt -l` WARN (1 file); `go vet` PASS; `ruff check` WARN (1,494 findings).
- **Known long-runners**: `tests/architecture/test_wiring.py::test_no_new_unwired_libs` (subprocess-heavy, exceeds 30s default) and an unidentified `tests/audit/` test that times out inside an unbounded `glob.scandir` walk.
- **Failure inventory — portability lane (historical, resolved 2026-05-08)**: 5 original failures — a `concurrent_write` key contract-drift assertion, a `baseline`→`base` string-comparison drift in a falsification test, and 3 `cos-coordination-status.sh`/`.py` subprocess timeouts (15s wall). 4 fixed by upstream commits; 1 (`ancestry-gate proof`) fixed by pinning `COS_QUEUE_AUTO_REBASE=0` in the test env to actually exercise the gate-fail path.
- **Full pytest collection error**: duplicate basename `test_cos_work_inventory.py` exists in both `tests/behavior/` and `tests/red_team/portability/`, causing an import-file-mismatch collection error; workaround is `--continue-on-collection-errors`.
- **Lint/format detail**: `cmd/cos/internal/security/license.go` is the one `gofmt`-flagged file (pre-existing, unrelated to recent work); `ruff` top offenders by unused-import volume are `os` (156), `pytest` (150), `pathlib.Path` (81), `unittest.mock.patch` (71); 1,260 of 1,494 findings are auto-fixable via `ruff check --fix`.
- **Coverage caveats**: no actual line-coverage instrumentation was run (no `coverage.xml`/`.coverage` artifact produced); Go `cached` results mean `go test` short-circuited without recompilation.
- **Recommendations (BLOCKER tier)**: resolve the duplicate-basename collection error; document the relaxed `pytest` invocation in `CONTRIBUTING.md`; run `gofmt -w` on the flagged file. (Recommended, non-blocking): `ruff check . --fix`; mark/refactor the long-running tests; bring the 5 historical portability failures under contract. (Deferrable): produce real line-coverage numbers via `pytest-cov`/`go test -coverprofile`.
- **Reproduction**: exact copy-paste commands are given for the relaxed full Python suite, per-file audit-lane iteration, the portability lane, fresh (non-cached) Go runs, and format/vet/lint.

## Relations & where used
Produced for `docs/09-Quality/legal/pre-public-readiness-checklist.md` item C4; its recommendations feed directly into pre-public-release blocker triage.

## Status / caveats
This is an explicit point-in-time snapshot dated 2026-05-07, with one embedded update dated 2026-05-08 (portability lane resolution) layered on top of the original failure inventory — the source itself instructs re-running on every release branch rather than trusting this snapshot as current. The full Python suite and the audit lane were never observed to complete in one run during the audit (both marked INCOMPLETE/PARTIAL); their true pass/fail state beyond the reported partial samples is unknown. Referenced local log paths (`/tmp/c4-*.log`) are explicitly local-only and not committed, so they cannot be used to independently re-verify this report's numbers.
