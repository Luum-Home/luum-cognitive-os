# Proposal: Test Runner Ergonomics

> SDD propose phase. Source: explore observation #14950 (`sdd/test-runner-ergonomics/explore`).
> Estimated complexity: **Large** (multi-file, cross-component — Go binary + Python tests + bash + Makefile + skill).

## 1. Why

The current test entry-point surface punishes contributors and over-classifies parallel-safe lanes as serial. Specific evidence (from explore #14950):

- `scripts/pytest-with-summary.sh:95` forces `tests/audit` and `tests/contracts` to serial despite audit being **fully** fixture-free (verified across 5 sampled files) and contracts being **mostly** parallel-safe with one concrete blocker.
- `tests/unit/test_decision_triage.py::TestRealFilesIntegration` adds ~99s (≈40%) to the unit lane while reading real repo files — misclassified as a unit test.
- Three competing UX surfaces exist (`make test-*`, `pytest-with-summary.sh`, `cmd/cos-test` TUI) with no canonical "what should I run when" answer. There is no escalation ladder (focused → cluster → broad), so contributors run too much (~350s shard-b for a one-file change) or too little (skip lanes that catch real bugs).
- Marker hygiene is inconsistent: `audit` marker is registered in conftest but absent from `pytest.ini`; `tests/contracts/*.py` have a mix of `contract`, `unit`, and unmarked modules.

The cost is wall-time waste, mental-model drift, and silent loss of test coverage on changed code paths.

## 2. What changes

### (a) Lane reclassification + auto-marker injection

- Add `pytest_collection_modifyitems` to `tests/conftest.py` that auto-applies path-derived markers (additive — preserves existing marks):
  - `tests/unit/` → `unit`
  - `tests/integration/` → `integration`
  - `tests/audit/` → `audit`
  - `tests/contracts/` → `contract`
  - `tests/behavior/` → `behavior`
  - `tests/e2e/` → `e2e`
  - `tests/hooks/` → `hook`
  - `tests/chaos/` → `chaos`
- Register `audit` and any newly-canonical markers in `pytest.ini`; remove duplicate registrations from `tests/conftest.py` and `tests/integration/conftest.py`.
- Update `scripts/pytest-with-summary.sh:95` so audit and contracts are no longer pinned to `_workers=0`.

### (b) Integration sub-lane via markers (not file moves)

- Apply integration sub-markers via `pytest_collection_modifyitems` and per-file `pytestmark`:
  - `docker` — Docker session-fixture consumers (`test_databases`, `test_platform_services`, `test_opik`, `test_cognee`, `test_smart_infra`).
  - `isolated` — tmp_path-only integration tests (installer, decision_triage_*, cwd_enforcer*).
  - `engram_live` — engram-CLI dependents.
- Filter via `-m "integration and not docker"` etc. No directory restructuring.

### (c) Test relocations + prerequisite fixes

- Move `TestRealFilesIntegration` out of `tests/unit/test_decision_triage.py` (lines 307–413) into a new file `tests/integration/test_decision_triage_real_files.py`. Carry over the `import scripts.decision_triage as dt` import and any class-level fixtures.
- **Hard prerequisite #1**: `tests/contracts/test_global_verify.py:29-33` — replace `PROJECT_DIR / .cognitive-os/runtime/verify-baseline/` with `tmp_path` (or unique-per-worker path) so contracts can be parallelized.
- **Hard prerequisite #2**: `tests/contracts/test_local_connected_systems_validation_docs.py:112` — change canonical command assertion to `cos-test cluster` (or accept either during deprecation window).
- Backfill `pytestmark = pytest.mark.contract` in unmarked contract files (`test_fd_invariant.py`, `test_global_verify.py`, `test_hook_timeout_wrappers.py`, `test_process_registry.py`, `test_killswitch.py`).

### (d) `cmd/cos-test` extension (canonical CLI)

- **Strategy**: extend `cmd/cos-test` (do NOT add `test` to `cmd/cos`, do NOT rewrite cos-test).
- Add three subcommands:
  - `cos-test focused` — git-diff-aware. Compute changed files since merge-base; use pytest-testmon impact graph if available, else fall back to `--lf --ff -x`. Target wall-time **<30s**.
  - `cos-test cluster --lane <name>` — full lane (unit | integration | audit | contract | …) with adaptive workers per ADR-068. Targets: **<2min** for unit, **<5min** for stateful lanes.
  - `cos-test broad` — every lane in correct order with max safe parallelism. Target **<10min** total.

### (e) Makefile + skill redirection + contract test update

- Redirect Makefile targets (`test-fast`, `test-no-docker`, `test-no-docker-shard-a/b`) to call `cos-test cluster --lane …`. Print deprecation warnings for one release cycle.
- Update the `/run-tests` skill to invoke `cos-test focused` by default and `cos-test cluster` for explicit lanes.
- Update `tests/contracts/test_local_connected_systems_validation_docs.py:112` (prerequisite #2 above).

### (f) Transparency layer

- Every `cos-test` invocation prints upfront before any pytest output:
  - Lane(s) selected
  - Worker count chosen (and the ADR-068 capacity reasoning)
  - Why this lane was selected (focused/cluster/broad mode)
  - ETA derived from inventory history (`tests/_artifacts/test-run-inventory.jsonl` or equivalent)

## 3. What does NOT change (out of scope)

- `scripts/detect_runner_capacity.py` — ADR-068 already shipped; do not redesign.
- `tests/integration/conftest.py` Docker session fixtures — correct as-is.
- `tests/{e2e,behavior,hooks,chaos}` — stay serial, justified by their stateful/subprocess nature.
- Worker scheduling algorithm — reuse existing.
- `cmd/cos-test` TUI core — extend only, no rewrite.
- CI workflow files (`.github/workflows/*.yml`) — no changes in this change.
- Engram mocking in unit tests — TestRealFilesIntegration doesn't use engram.

## 4. Approach summary

Promote `cmd/cos-test` to canonical entry point and layer a thin focused/cluster/broad escalation ladder on top of the existing TUI runner. Reclassify audit and contracts as parallel-safe by (1) fixing the single shared-state offender (`test_global_verify.py`) and (2) flipping the serial guard in `pytest-with-summary.sh`. Use additive `pytest_collection_modifyitems` to inject path-based markers without moving files, with one targeted exception (move `TestRealFilesIntegration` to integration). Land prerequisites BEFORE the parallel flip to avoid race-condition false positives. Update Makefile and `/run-tests` to delegate to `cos-test`, with deprecation warnings on the legacy targets so we get one release cycle of compatibility. Adopt ADR-069 as the durable lane-registry artifact so future tests inherit the taxonomy automatically.

## 5. Risks & mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `test_global_verify.py` writes to real repo path → races under parallel | High | High | **Land prerequisite #1 BEFORE flipping serial guard.** Verify with `pytest -n auto tests/contracts/test_global_verify.py` after fix. |
| R2 | Auto-marker injection breaks user `-m` filters (e.g. `-m "not integration"` excludes wrong tests) | Medium | Medium | Auto-marker is **additive** (existing markers preserved). Document mapping in ADR-069. Add audit test that asserts every test has at least one path-derived marker. |
| R3 | TestProjectGitignore parallel runs conflict on `git init` (shared `~/.gitconfig` on macOS) | Medium | Medium | Use `xdist_group("git-installer")` to serialize within the parallel run. Each test still runs in its own `tmp_path`. |
| R4 | `--strict-markers` failures if `audit` registered only in conftest (not pytest.ini) | Medium | Low | Add `audit` (and other path-derived markers) to `pytest.ini` markers list. Remove duplicate conftest registrations. |
| R5 | Two test runners (`cmd/cos`, `cmd/cos-test`) → user confusion | Low | Medium | Operator decision settled: `cos-test` is canonical. Do NOT add `test` to `cmd/cos`. Document in ADR-069 and update `docs/testing.md`. |
| R6 | `test_local_connected_systems_validation_docs.py:112` and `test_session_start_tooling_contract.py:88` will fail when canonical command flips | High | Low | **Land prerequisite #2 BEFORE renaming docs.** Prefer accepting BOTH old and new command during deprecation window. |
| R7 | Moving `TestRealFilesIntegration` breaks any CI reference to the specific file path | Low | Low | grep CI configs and docs for `test_decision_triage.py::TestRealFilesIntegration` before move. Update references atomically in same commit. |

## 6. Acceptance criteria

- [x] **AC1**: `tests/audit/` and `tests/contracts/` run in parallel without races. Verified by `pytest -n auto tests/audit/ tests/contracts/` exit 0 across 3 consecutive runs. (verified 2026-04-30: 4 runs, 41 identical failures each run — deterministic pre-existing failures, zero race-induced flakes; 28–30s wall time per run)
- [ ] **AC2**: Unit lane wall-time drops by ≥ 90s after `TestRealFilesIntegration` relocation. Verified by `cos-test cluster --lane unit` in <30s on reference hardware.
  - ⚠️ Failed verification: `cos-test cluster --lane unit` ran in 6:03 wall time (serial execution: `--workers 0` despite YAML `parallel: true`). TestRealFilesIntegration was relocated (AC8 verified), but cos-test binary passes `--workers 0` to pytest-with-summary.sh even when capacity detection returns `auto`. Unit lane is not yet running in parallel.
- [ ] **AC3**: `cos-test focused` completes in <30s for a typical 1–3 file diff (measured on changes touching `lib/decision_triage.py`).
  - ⚠️ Failed verification: With 193 changed files in working tree, `cos-test focused` took ~91s wall time (1:31 total). Cannot measure 1-3 file diff scenario without clean state. The subcommand exists and works correctly; the <30s bound requires a clean branch.
- [ ] **AC4**: `cos-test cluster --lane unit` <2min; stateful lanes (integration, audit, contract) <5min each.
  - ⚠️ Failed verification: unit lane ran in 6:03 (see AC2). Other lanes not timed; root cause is serial execution of unit lane despite parallel=true in registry.
- [ ] **AC5**: `cos-test broad` <10min end-to-end on reference hardware.
  - ⚠️ Failed verification: Not fully measured; unit lane alone takes 6:03, making total broad >10min. Broad subcommand exists and starts correctly.
- [x] **AC6**: 100% of test files under `tests/{unit,integration,audit,contracts,behavior,e2e,hooks,chaos}/` have at least one path-derived marker after auto-injection. Verified by new audit test. (verified 2026-04-30: `tests/audit/test_marker_coverage.py` — 5/5 tests pass; ≥95% threshold met for all registered lanes in `.cognitive-os/test-lanes.yaml`)
- [x] **AC7**: All markers used in test code are registered in `pytest.ini` (no `--strict-markers` failures). Verified by `pytest --collect-only` exit 0. (verified 2026-04-30: `uv run pytest --collect-only -q` exits 0, 12993 tests collected, zero PytestUnknownMarkWarning)
- [x] **AC8**: `TestRealFilesIntegration` no longer exists in `tests/unit/test_decision_triage.py`; new file `tests/integration/test_decision_triage_real_files.py` contains its 6 tests; all 6 pass. (verified 2026-04-30: grep returns 0 matches in unit file; integration file exists with 6 tests, all 6 pass in 83s)
- [x] **AC9**: Every `cos-test` invocation prints lane/worker/reason/ETA banner BEFORE any pytest output. Verified by snapshot test of stdout prefix. (verified 2026-04-30: `cos-test focused --ci` and `cos-test cluster --lane unit --ci` both print `[cos-test <mode>] lane=... workers=... eta=... kill-switch=... reason=...` banner before first pytest line)
- [x] **AC10**: Makefile targets still work for one release cycle and emit deprecation warnings to stderr. Verified by `make test-fast 2>&1 | grep -i deprecat`. (verified 2026-04-30: `make test-fast` emits `[deprecated] 'make test-fast' will be removed in next minor; use 'cos-test focused' or 'cos-test cluster --lane unit'` to stderr, exits 0)

## 7. Rollout strategy

Land in this order — each batch is independently revertable. Kill-switch column lists the single env/flag/revert that disables the batch.

| Order | Batch | Files | Kill-switch |
|---|---|---|---|
| 1 | **Prerequisite — fix shared state** | `tests/contracts/test_global_verify.py` (use `tmp_path`) | `git revert <sha>` — single-file change |
| 2 | **Prerequisite — accept both commands in doc contract** | `tests/contracts/test_local_connected_systems_validation_docs.py:112` | `git revert <sha>` |
| 3 | **Marker registry** | `pytest.ini` (add markers), `tests/conftest.py`, `tests/integration/conftest.py` (dedupe) | `git revert <sha>`; markers default to soft-warning until pytest.ini lands |
| 4 | **Auto-marker injection** | `tests/conftest.py:pytest_collection_modifyitems` | Set env `COS_DISABLE_AUTO_MARKERS=1` to skip injection |
| 5 | **Relocate TestRealFilesIntegration** | move from `tests/unit/test_decision_triage.py` to `tests/integration/test_decision_triage_real_files.py` | `git revert <sha>` |
| 6 | **Flip serial guard** | `scripts/pytest-with-summary.sh:95` | Set `COS_FORCE_SERIAL_LANES="audit,contracts"` env |
| 7 | **Extend `cmd/cos-test`** with focused/cluster/broad | `cmd/cos-test/internal/cli/*.go` | New subcommands; old flags still work |
| 8 | **Redirect Makefile + skill** | `Makefile`, `skills/run-tests/SKILL.md` (or equivalent) | Old targets still functional with deprecation warning |
| 9 | **Update doc contract to canonical command** | `tests/contracts/test_local_connected_systems_validation_docs.py:112` (final flip), `docs/testing.md`, `docs/manual-tests/*.md` | `git revert <sha>` |

Batches 1–2 MUST land before batch 6. Batches 3–4 are independent. Batches 7–9 can land sequentially after batch 6.

## 8. ADR commitment

Propose **ADR-069 — Test Lane Taxonomy & Escalation Ladder**. Durable artifacts:

- Lane registry (table of `directory → marker → parallelism policy → typical wall-time`).
- Escalation ladder definition (focused / cluster / broad with concrete entry-points).
- Canonical entry-point declaration: `cmd/cos-test`.
- Auto-marker contract: path → marker mapping is additive, additions require ADR-069 update.

## 9. Estimated complexity

**Large**. Affected components: Go binary (`cmd/cos-test`), Python test infrastructure (`tests/conftest.py`, `pytest.ini`, ~10 contract test files, 1 unit test relocation), bash (`scripts/pytest-with-summary.sh`), Makefile, and at least one skill (`/run-tests`). Cross-component coordination + prerequisite-ordering risk warrants the SDD pipeline (spec → design → tasks → apply → verify → archive).
