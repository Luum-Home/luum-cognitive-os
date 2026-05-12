# SDD Tasks: test-runner-ergonomics

## Metadata

- **Total tasks**: 27
- **Critical path**: T0.1 → T0.2 → T1.1 → T1.2 → T1.3 → T4.1 → T4.2 → T4.3 → T5.1 → T5.2 → T6.1 → T6.2 → T6.3 → T8.1 → T8.2 → T8.3
- **Parallelizable batches**: Batches 1, 2, and 3 can all land concurrently after Batch 0 completes
- **Estimated total effort**: 0 × L (2), 7 × M (7), 11 × S (11) → approximately 5 developer-days
- **Apply phase strategy**: 1 sub-agent per batch; batches are sequential where cross-batch dependencies exist; Batches 1+2+3 run in parallel after Batch 0; Batches 4+5+6+7 run sequentially; Batch 8 is final validation

---

## Batch 0 — Prerequisites (serial, must land first)

- T0.1
  - **Title**: Fix `test_global_verify.py` shared-state write
  - **Deliverable**: `tests/contracts/test_global_verify.py` (lines 29-33 rewritten to use `tmp_path` or `COGNITIVE_OS_VERIFY_BASELINE_DIR` env pointing to `tmp_path`)
  - **Dependencies**: none
  - **Verify**: `pytest tests/contracts/test_global_verify.py -n 4` exits 0 across 3 consecutive runs with no `FileExistsError` or `JSONDecodeError` in output; real repo path `.cognitive-os/runtime/verify-baseline/` unchanged after run
  - **Model**: sonnet
  - **Effort**: S

- T0.2
  - **Title**: Register `audit` and all path-derived lane markers in `pytest.ini`
  - **Deliverable**: `pytest.ini` — `markers` key updated; duplicate conftest marker registrations removed from `tests/conftest.py` and `tests/audit/conftest.py` if present
  - **Dependencies**: none (parallel with T0.1, but both must complete before Batch 1)
  - **Verify**: `pytest --markers | grep -E "^@pytest.mark.(audit|hook|chaos|contract|behavior|e2e|integration|unit|architecture)"` shows 9+ rows; `pytest --collect-only --strict-markers -q 2>&1 | grep -i "PytestUnknownMarkWarning"` returns 0 lines
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 1 — Lane registry + auto-marker injection (parallel-safe with Batches 2 and 3, after Batch 0)

- T1.1
  - **Title**: Create `.cognitive-os/test-lanes.yaml` lane registry
  - **Deliverable**: `.cognitive-os/test-lanes.yaml` — `version: 1` + `lanes:` map with 9 entries (unit, audit, contract, architecture: `parallel: true`; integration: `parallel: marker`, `marker_serial: docker`; behavior, e2e, hook, chaos: `parallel: false`). Each entry has: `paths`, `parallel`, `typical_wall_time_s`, `stateful_reason` (where applicable)
  - **Dependencies**: T0.2 (marker names confirmed)
  - **Verify**: `python3 -c "import yaml; d=yaml.safe_load(open('.cognitive-os/test-lanes.yaml')); assert len(d['lanes']) == 9, d['lanes'].keys()"` exits 0
  - **Model**: sonnet
  - **Effort**: S

- T1.2
  - **Title**: Implement `pytest_collection_modifyitems` auto-marker injection in `tests/conftest.py`
  - **Deliverable**: `tests/conftest.py` — new `pytest_collection_modifyitems` hook using `LANE_PATH_MAP` (9 lanes, longest-prefix match). Additive-only: inject marker only when item has no existing marker for that lane. Idempotent across re-collection
  - **Dependencies**: T1.1 (YAML registry used for path mapping), T0.2 (markers registered)
  - **Verify**: `pytest tests/unit/ --collect-only -q -m unit 2>/dev/null | wc -l` prints ≥ 270; `pytest tests/audit/ --collect-only -q -m audit 2>/dev/null | wc -l` prints ≥ 1; `pytest --collect-only --strict-markers -q 2>&1 | grep -i error` returns 0 lines
  - **Model**: sonnet
  - **Effort**: M

- T1.3
  - **Title**: Add unit test for auto-marker injection in `tests/unit/test_conftest_automarker.py`
  - **Deliverable**: `tests/unit/test_conftest_automarker.py` — tests: (a) marker injected for file in known lane path, (b) existing marker not duplicated on re-collection, (c) unknown path gets no marker, (d) all 9 lanes covered
  - **Dependencies**: T1.2
  - **Verify**: `pytest tests/unit/test_conftest_automarker.py -v` exits 0 with ≥ 4 passing tests
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 2 — Test relocation (parallel-safe with Batches 1 and 3, after Batch 0)

- T2.1
  - **Title**: Move `TestRealFilesIntegration` from unit to integration
  - **Deliverable**: NEW `tests/integration/test_decision_triage_real_files.py` (contains `TestRealFilesIntegration`, lines 307-413 from source, plus hoisted imports and fixtures; adds `pytestmark = pytest.mark.integration`); `tests/unit/test_decision_triage.py` (class removed, no orphan references)
  - **Dependencies**: T0.2 (integration marker registered)
  - **Verify**: `grep -n "TestRealFilesIntegration" tests/unit/test_decision_triage.py` returns 0 lines; `pytest tests/integration/test_decision_triage_real_files.py -v` exits 0 with ≥ 6 passing tests
  - **Model**: sonnet
  - **Effort**: M

- T2.2
  - **Title**: Confirm unit file is intact after relocation
  - **Deliverable**: No file changes — verification run only
  - **Dependencies**: T2.1
  - **Verify**: `pytest tests/unit/test_decision_triage.py -v` exits 0; `pytest tests/unit/ -x -q 2>/dev/null | tail -3` shows 0 failures
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 3 — `cmd/cos-test` extension (parallel-safe with Batches 1 and 2, after Batch 0)

- T3.1
  - **Title**: Document `cmd/cos-test` extension points
  - **Deliverable**: `.cognitive-os/plans/features/cos-test-extension-notes.md` — short notes file: existing cobra command tree, internal Runner package interface, how existing `run/coverage/watch/dashboard` subcommands register, proposed hook points for focused/cluster/broad
  - **Dependencies**: none (can start immediately after Batch 0 starts, no hard dependency)
  - **Verify**: `ls .cognitive-os/plans/features/cos-test-extension-notes.md` exits 0; file is ≥ 20 lines
  - **Model**: sonnet
  - **Effort**: S

- T3.2
  - **Title**: Implement `cmd/cos-test/internal/cli/focused.go` — git-diff-aware mode
  - **Deliverable**: `cmd/cos-test/internal/cli/focused.go` — cobra subcommand `focused` with flags: `--since <ref>`, `--include-uncommitted`, `--testmon`, `--workers N`, `--dry-run`. Algorithm: git diff → same-name heuristic → testmon union (if fresh) → empty fallback to `--lf --ff -x`. Prints 5-line banner per design §9
  - **Dependencies**: T3.1
  - **Verify**: `go build ./cmd/cos-test/...` exits 0; `cos-test focused --help` shows usage text including `--since`, `--dry-run`; `cos-test focused --dry-run` on a synthetic diff (set up via env or temp git repo) prints expected test candidate list
  - **Model**: opus
  - **Effort**: L

- T3.3
  - **Title**: Implement `cmd/cos-test/internal/cli/cluster.go` — lane-scoped mode
  - **Deliverable**: `cmd/cos-test/internal/cli/cluster.go` — cobra subcommand `cluster` with required `--lane <name>` flag. Validates name against `.cognitive-os/test-lanes.yaml`. Resolves workers per lane `parallel` policy (parallel-safe → `detect_runner_capacity.py`; serial → `-n 0`). Prints banner
  - **Dependencies**: T3.1, T1.1 (test-lanes.yaml schema)
  - **Verify**: `go build ./cmd/cos-test/...` exits 0; `cos-test cluster --help` shows `--lane` flag; `cos-test cluster --lane unit --dry-run` prints pytest invocation including `-n <N>` workers; `cos-test cluster --lane nonexistent --dry-run` exits 1 with "unknown lane" error
  - **Model**: sonnet
  - **Effort**: M

- T3.4
  - **Title**: Implement `cmd/cos-test/internal/cli/broad.go` — all-lanes orchestration
  - **Deliverable**: `cmd/cos-test/internal/cli/broad.go` — cobra subcommand `broad` with flags: `--skip-docker`, `--skip-slow`. Iterates lanes in fixed order from design §2: unit+audit+contract+architecture (parallel) → integration-isolated (parallel) → integration-shared (serial) → behavior → hook → e2e → chaos. Aggregates exit codes (OR). Prints per-lane banner
  - **Dependencies**: T3.1, T1.1 (test-lanes.yaml), T3.3 (cluster subcommand reused per lane)
  - **Verify**: `go build ./cmd/cos-test/...` exits 0; `cos-test broad --dry-run` output lists each of the 9 lanes in correct order; `cos-test broad --skip-docker --dry-run` omits integration-shared and chaos from output
  - **Model**: sonnet
  - **Effort**: M

- T3.5
  - **Title**: Implement banner module `cmd/cos-test/internal/banner/`
  - **Deliverable**: NEW package `cmd/cos-test/internal/banner/` — reads `.cognitive-os/reports/test-runs/*/inventory.md` (last 10 runs per lane), computes p50 ETA, formats the 5-line banner string per design §9 sample. Exported `Format(lane, paths, workerCount, workerReason, eta)` function
  - **Dependencies**: T3.2, T3.3, T3.4 (consumers of banner)
  - **Verify**: `go test ./cmd/cos-test/internal/banner/...` exits 0; unit test asserts banner output matches expected 5-line format with `[cos-test cluster]` prefix
  - **Model**: sonnet
  - **Effort**: M

- T3.6
  - **Title**: Wire focused/cluster/broad subcommands into root cobra command
  - **Deliverable**: `cmd/cos-test/main.go` or root command file updated to register `focused`, `cluster`, `broad` subcommands
  - **Dependencies**: T3.2, T3.3, T3.4, T3.5
  - **Verify**: `go build ./cmd/cos-test/...` exits 0; `cos-test --help` output contains `focused`, `cluster`, `broad` in subcommand list
  - **Model**: sonnet
  - **Effort**: S

- T3.7
  - **Title**: Add Go tests for focused/cluster/broad subcommands
  - **Deliverable**: `cmd/cos-test/internal/cli/focused_test.go`, `cmd/cos-test/internal/cli/cluster_test.go`, `cmd/cos-test/internal/cli/broad_test.go` — table-driven tests: cluster lane resolution (valid/invalid lane names, parallel vs serial policy), focused mode diff parsing (synthetic git diff → expected test set), broad mode lane ordering (--skip-docker omits expected lanes)
  - **Dependencies**: T3.2, T3.3, T3.4, T3.6
  - **Verify**: `go test ./cmd/cos-test/...` exits 0 with ≥ 10 test cases passing
  - **Model**: sonnet
  - **Effort**: M

---

## Batch 4 — Lane parallelization flip (depends on T0.1, T1.1; serial after Batches 0+1 complete)

- T4.1
  - **Title**: Refactor `scripts/pytest-with-summary.sh` serial-lane guard
  - **Deliverable**: `scripts/pytest-with-summary.sh` — line 95 guard that forces `_workers=0` for audit/contracts rewritten. New logic: accept explicit `--workers N` argument from caller (cos-test). When `--workers N` is provided, use it directly; when absent, apply existing heuristic. Remove hard-coded lane names from this file (lane policy lives in `test-lanes.yaml`, resolved by cos-test)
  - **Dependencies**: T0.1 (parallel-safe contracts), T1.1 (lane registry defines workers per lane)
  - **Verify**: `bash scripts/pytest-with-summary.sh tests/audit/ -n 4` exits 0 with `-n 4` visible in pytest invocation in output; `bash scripts/pytest-with-summary.sh tests/contracts/ -n 4` exits 0 (after T0.1)
  - **Model**: sonnet
  - **Effort**: M

- T4.2
  - **Title**: Smoke run: `pytest tests/audit/ -n 4` stability check
  - **Deliverable**: No file changes — 3× stability verification run
  - **Dependencies**: T4.1
  - **Verify**: Run `pytest tests/audit/ -n 4` 3 times; all 3 exit 0; no `FAILED`, `ERROR`, or `ResourceWarning` in any run output
  - **Model**: sonnet
  - **Effort**: S

- T4.3
  - **Title**: Smoke run: `pytest tests/contracts/ -n 4` stability check
  - **Deliverable**: No file changes — 3× stability verification run
  - **Dependencies**: T4.1, T0.1 (contracts now parallel-safe)
  - **Verify**: Run `pytest tests/contracts/ -n 4` 3 times; all 3 exit 0; `.cognitive-os/runtime/verify-baseline/` is not written during any run
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 5 — Integration sub-lane markers (after Batch 1 fully completes)

- T5.1
  - **Title**: Audit `tests/integration/` and add `docker` markers to shared-fixture tests
  - **Deliverable**: `tests/integration/*.py` files that use session-scoped Docker fixtures (PostgreSQL, Valkey, ClickHouse from `tests/integration/conftest.py`) updated to add `pytestmark = pytest.mark.docker` or per-test `@pytest.mark.docker`. Files using only `tmp_path` get no `docker` marker. Also add `xdist_group("git-installer")` to `tests/integration/test_installer.py::TestProjectGitignore` (EC-5 from spec)
  - **Dependencies**: T1.1 (test-lanes.yaml defines integration sub-lanes), T0.2 (docker marker registered)
  - **Verify**: `pytest tests/integration/ -m "not docker" --collect-only -q 2>/dev/null | wc -l` prints ≥ 1 (isolated subset exists); `pytest tests/integration/ -m "docker" --collect-only -q 2>/dev/null | wc -l` prints ≥ 1 (docker subset exists); `pytest --collect-only --strict-markers -q tests/integration/ 2>&1 | grep error` returns 0 lines
  - **Model**: sonnet
  - **Effort**: M

- T5.2
  - **Title**: Smoke run: `pytest tests/integration/ -m "not docker" -n 2` stability check
  - **Deliverable**: No file changes — 3× stability verification run
  - **Dependencies**: T5.1
  - **Verify**: Run `pytest tests/integration/ -m "not docker" -n 2` 3 times without Docker; all 3 exit 0; no `FAILED` or `ERROR` lines in output
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 6 — Redirection and deprecation (after Batch 3 fully completes; T6.3 also needs T0.1)

- T6.1
  - **Title**: Update `Makefile` legacy targets to deprecation shims
  - **Deliverable**: `Makefile` — targets `test-fast`, `test-no-docker`, `test-no-docker-shard-a`, `test-no-docker-shard-b` each print `[deprecated] use: cos-test <equivalent>` to stderr then proxy to `cos-test cluster/broad` equivalent per design §8 mapping. Underlying tests still run
  - **Dependencies**: T3.6 (cos-test subcommands available)
  - **Verify**: `make test-fast 2>&1 | head -2` contains word "deprecated"; `make test-fast 2>&1 | grep -ic deprecated` ≥ 1; make target exits with same code as underlying pytest run
  - **Model**: sonnet
  - **Effort**: S

- T6.2
  - **Title**: Update `skills/run-tests/SKILL.md` to invoke `cos-test`
  - **Deliverable**: `skills/run-tests/SKILL.md` — primary invocation updated to `cos-test focused` (single-file/small diff) or `cos-test cluster --lane <detected>` (explicit lane). Legacy detection described as fallback only. Skill file references cos-test as canonical entry point
  - **Dependencies**: T3.6 (cos-test subcommands available)
  - **Verify**: `grep -c "cos-test" skills/run-tests/SKILL.md` ≥ 2; `grep -c "focused\|cluster\|broad" skills/run-tests/SKILL.md` ≥ 1
  - **Model**: sonnet
  - **Effort**: S

- T6.3
  - **Title**: Update `test_local_connected_systems_validation_docs.py:112` to accept both commands
  - **Deliverable**: `tests/contracts/test_local_connected_systems_validation_docs.py` — line 112 regex updated to accept `pytest-with-summary.sh|cos-test (cluster|broad|focused)` pattern per design §6.2. Both old and new canonical commands pass during deprecation window
  - **Dependencies**: T0.1 (contracts parallel-safe), T3.6 (cos-test available)
  - **Verify**: `pytest tests/contracts/test_local_connected_systems_validation_docs.py -v` exits 0
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 7 — ADR and docs (parallel-safe with Batch 6, after Batch 3+5 complete)

- T7.1
  - **Title**: Write `docs/02-Decisions/adrs/ADR-069-test-lane-taxonomy.md`
  - **Deliverable**: `docs/02-Decisions/adrs/ADR-069-test-lane-taxonomy.md` — sections per design §10: context, decision (cos-test canonical, YAML registry, marker auto-inject, escalation ladder), lane taxonomy table (9 lanes), parallel-safe contract definition, why marker-based not file-based split, consequences, rollout cross-reference, status: Proposed. File is ≥ 150 lines
  - **Dependencies**: T1.1 (YAML schema finalized), T3.6 (cos-test interface finalized)
  - **Verify**: `ls docs/02-Decisions/adrs/ADR-069-test-lane-taxonomy.md` exits 0; `wc -l docs/02-Decisions/adrs/ADR-069-test-lane-taxonomy.md | awk '{print $1}'` ≥ 150
  - **Model**: opus
  - **Effort**: M

- T7.2
  - **Title**: Add lane taxonomy entry to `rules/RULES-COMPACT.md`
  - **Deliverable**: `rules/RULES-COMPACT.md` — new entry under §15 (or new §16 if §15 is occupied) referencing the 9-lane taxonomy, cos-test canonical entry point, and ADR-069
  - **Dependencies**: T7.1 (ADR number confirmed)
  - **Verify**: `grep -c "ADR-069\|lane-taxonomy\|cos-test" rules/RULES-COMPACT.md` ≥ 1
  - **Model**: sonnet
  - **Effort**: S

- T7.3
  - **Title**: Add deprecation note to Makefile comments and CHANGELOG
  - **Deliverable**: `Makefile` (comment block near deprecated targets documenting the one-release-cycle policy and removal date); `CHANGELOG.md` (entry for test-runner-ergonomics: new cos-test subcommands, lane registry, deprecated Makefile targets, marker auto-injection, test relocation)
  - **Dependencies**: T6.1 (Makefile targets finalized)
  - **Verify**: `grep -c "deprecated\|cos-test\|ADR-069" Makefile` ≥ 1; `grep -c "test-runner-ergonomics\|cos-test" CHANGELOG.md` ≥ 1
  - **Model**: sonnet
  - **Effort**: S

---

## Batch 8 — Verification (after all Batches 0-7 complete)

- T8.1
  - **Title**: Full broad suite via `cos-test broad`; capture wall time vs baseline
  - **Deliverable**: `.cognitive-os/plans/features/cos-test-broad-timing.md` — records: timestamp, total wall time, per-lane wall time, comparison vs baseline (pre-change `make test-no-docker` run), pass/fail per lane
  - **Dependencies**: All previous tasks
  - **Verify**: `cos-test broad --skip-docker` exits 0; total wall time printed in timing doc; wall time ≤ 10 min on reference hardware OR deviation documented with justification
  - **Model**: sonnet
  - **Effort**: M

- T8.2
  - **Title**: Flake detection: 5× per-lane runs, assert 0 flakes
  - **Deliverable**: No file changes — flake verification runs
  - **Dependencies**: T8.1 (broad run confirms baseline passes)
  - **Verify**: Run `cos-test cluster --lane unit` 5 times; run `cos-test cluster --lane audit` 5 times; run `cos-test cluster --lane contract` 5 times; all 15 runs exit 0; failure rate = 0 across all runs
  - **Model**: sonnet
  - **Effort**: M

- T8.3
  - **Title**: Update Engram session summary with measured deltas
  - **Deliverable**: Engram observation saved at `sdd/test-runner-ergonomics/verify-baseline` — records: pre-change unit lane wall time, post-change unit lane wall time (should drop ≥ 90s per AC2), broad suite wall time, flake counts, acceptance criteria pass/fail status for AC1-AC10
  - **Dependencies**: T8.1, T8.2
  - **Verify**: `mem_search("sdd/test-runner-ergonomics/verify-baseline")` returns an observation with AC status for ≥ 8 of the 10 acceptance criteria
  - **Model**: sonnet
  - **Effort**: S

---

## Acceptance Criteria Reference (from spec)

- AC1: `pytest -n auto tests/audit/ tests/contracts/` exits 0 across 3 consecutive runs
- AC2: Unit lane wall-time drops ≥ 90s after relocation; `cos-test cluster --lane unit` < 30s on reference HW
- AC3: `cos-test focused` < 30s for typical 1-3 file diff
- AC4: `cos-test cluster --lane unit` < 2min; stateful lanes < 5min each
- AC5: `cos-test broad` < 10min end-to-end
- AC6: 100% of test files under `tests/{unit,integration,audit,contracts,behavior,e2e,hooks,chaos}/` have ≥ 1 path-derived marker
- AC7: All markers registered in `pytest.ini`; `pytest --collect-only --strict-markers` exits 0
- AC8: `TestRealFilesIntegration` not in `tests/unit/test_decision_triage.py`; new file has ≥ 6 tests; all pass
- AC9: Every `cos-test` invocation prints lane/worker/reason/ETA banner BEFORE pytest output
- AC10: Makefile targets work with deprecation warnings on stderr; `make test-fast 2>&1 | grep -i deprecat` matches
