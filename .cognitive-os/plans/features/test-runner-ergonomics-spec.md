# SDD Spec: test-runner-ergonomics

> Phase: spec | Change: test-runner-ergonomics | Project: luum-cognitive-os
> Source: proposal #14951, explore #14950
> Date: 2026-04-29

---

## 1. Functional Requirements

### REQ-1

**Statement**: The system MUST provide a canonical test entry point `cos-test` with three named escalation modes: `focused`, `cluster`, and `broad`.

**Rationale**: Three competing UX surfaces (Makefile, `pytest-with-summary.sh`, `cmd/cos-test`) leave contributors uncertain which command to run; a single canonical entry point removes that ambiguity.

**Priority**: MUST

---

### REQ-2

**Statement**: `cos-test focused` MUST auto-detect changed files via `git diff --name-only <merge-base>...HEAD`, derive test candidates from the delta (using pytest-testmon graph if available, else `--lf --ff -x`), and run ONLY those candidates.

**Rationale**: Running the full suite for every single-file edit is the primary contributor complaint; the focused mode removes that penalty and keeps feedback under 30 s.

**Priority**: MUST

---

### REQ-3

**Statement**: `cos-test cluster --lane <name>` MUST run the full named lane with adaptive worker count determined by ADR-068 `scripts/detect_runner_capacity.py`. Valid lane names are the nine lanes defined in the Lane Registry (see section 4).

**Rationale**: A per-lane command is the natural unit for CI sharding and for developers validating a single concern without running unrelated lanes.

**Priority**: MUST

---

### REQ-4

**Statement**: `cos-test broad` MUST run all nine lanes in the correct dependency order (prerequisites first, parallel-safe lanes in parallel, serial lanes sequentially after), with a wall-time target of less than 10 minutes on reference hardware.

**Rationale**: The existing `make test-no-docker` equivalent has no ordering guarantee and forces audit/contracts serial despite their being parallel-safe; broad mode must be correct by construction.

**Priority**: MUST

---

### REQ-5

**Statement**: Every `cos-test` invocation MUST print a transparency banner to stdout BEFORE any pytest output. The banner MUST contain: lane(s) being run, worker count, reasoning for that worker count (referencing ADR-068 output), and ETA derived from historical inventory.

**Rationale**: Contributors and CI logs must be able to confirm at a glance what is running and why, without reading source code.

**Priority**: MUST

---

### REQ-6

**Statement**: `tests/contracts/test_global_verify.py` MUST be fixed to write its baseline JSON file to `tmp_path` (or a per-worker unique directory) instead of the real repo path `.cognitive-os/runtime/verify-baseline/{agent_id}.json`.

**Rationale**: This is the single concrete shared-state offender that blocks parallel execution of the contracts lane; fixing it is a hard prerequisite to flipping the serial guard in `pytest-with-summary.sh:95`.

**Priority**: MUST

---

### REQ-7

**Statement**: The `audit` marker and all nine path-derived lane markers MUST be registered in `pytest.ini` under the `[pytest]` `markers` key. Duplicate registrations in conftest files MUST be removed.

**Rationale**: `--strict-markers` is already in `addopts`; missing `audit` from `pytest.ini` means any standalone run of `tests/audit/` without the root conftest would fail marker validation.

**Priority**: MUST

---

### REQ-8

**Statement**: A `pytest_collection_modifyitems` hook in `tests/conftest.py` MUST inject path-derived markers additively: any test file under `tests/<dir>/` receives the corresponding lane marker if it does not already carry one. The mapping is: `unit` → `unit`, `audit` → `audit`, `contracts` → `contract`, `integration` → `integration`, `behavior` → `behavior`, `e2e` → `e2e`, `hooks` → `hook`, `chaos` → `chaos`.

**Rationale**: Inconsistent manual marker application across ~20 contract files creates gaps where `-m contract` misses files; additive auto-injection closes those gaps without removing existing intentional markers.

**Priority**: MUST

---

### REQ-9

**Statement**: `TestRealFilesIntegration` (currently `tests/unit/test_decision_triage.py:307–413`) MUST be relocated to a new file `tests/integration/test_decision_triage_real_files.py`. The unit file MUST retain only the unit tests.

**Rationale**: The class reads hundreds of real repo files and takes ~99 s (40% of unit lane wall time); it violates the unit lane's parallel-safe invariant and makes the unit lane appear slow.

**Priority**: MUST

---

### REQ-10

**Statement**: Legacy Makefile targets `test-fast`, `test-no-docker`, `test-no-docker-shard-a`, and `test-no-docker-shard-b` MUST continue to function for at least one release cycle after the change lands, but MUST print a deprecation warning to stderr redirecting users to the equivalent `cos-test` command.

**Rationale**: Contract test `test_local_connected_systems_validation_docs.py:112` pins the canonical command; a hard break would fail CI immediately. A deprecation cycle allows an orderly migration.

**Priority**: MUST

---

### REQ-11

**Statement**: The `/run-tests` skill MUST default to invoking `cos-test focused` for single-file or small diff contexts, and `cos-test cluster --lane <detected-lane>` when a specific lane is requested.

**Rationale**: The skill is a primary developer-facing automation surface; it must reflect the new canonical entry point so contributors discover `cos-test` organically.

**Priority**: SHOULD

---

### REQ-12

**Statement**: The `integration` lane MUST be split into two virtual sub-lanes via markers: `integration-isolated` (tests using `tmp_path` only, no Docker) and `integration-shared` (tests using session-scoped Docker fixtures). `cos-test cluster --lane integration-isolated` MUST run with adaptive workers; `cos-test cluster --lane integration-shared` MUST run serially.

**Rationale**: The explore phase confirmed three distinct sub-populations in `tests/integration/`; treating them identically forces the fast isolated tests to wait for Docker availability.

**Priority**: MUST

---

### REQ-13

**Statement**: `pytest -m unit` run directly (without `cos-test`) MUST produce the same test set as `cos-test cluster --lane unit` after the auto-marker injection hook is active.

**Rationale**: Developers who bypass `cos-test` and invoke pytest directly must not get a different test set; the auto-marker hook ensures parity without requiring `cos-test` as a mandatory wrapper.

**Priority**: MUST

---

## 2. Behavioral Scenarios

### Scenario S-1: Developer edits one file, runs `cos-test focused`

**Given** a developer has edited `lib/model_router.py` and no other files since the branch merge-base,
**When** they run `cos-test focused`,
**Then**:
- The transparency banner appears first on stdout, showing: lane=`focused`, workers=`<N>` (from ADR-068), reason=`git diff detected 1 changed file`, ETA=`<estimate>`.
- Only test files that import or test `lib/model_router` are collected and run (via pytest-testmon graph or `--lf --ff -x` fallback).
- Exit code is 0 if all selected tests pass.
- Total elapsed time is less than 30 seconds on reference hardware.

---

### Scenario S-2: Developer runs `cos-test cluster --lane unit`

**Given** a developer wants to validate the entire unit lane,
**When** they run `cos-test cluster --lane unit`,
**Then**:
- The transparency banner shows: lane=`unit`, workers=`<N>` (adaptive, ≥2 on multi-core), reason=`parallel-safe lane`, ETA=`<estimate from history>`.
- All files under `tests/unit/` are collected (auto-marker injection ensures every file has the `unit` marker).
- `TestRealFilesIntegration` is NOT present in `tests/unit/` and does NOT appear in the collected set.
- Total elapsed time is less than 2 minutes on reference hardware.
- Exit code reflects actual test outcomes.

---

### Scenario S-3: Developer runs `cos-test broad`

**Given** a developer wants a full pre-push validation sweep,
**When** they run `cos-test broad`,
**Then**:
- Lanes run in this order: `unit` and `audit` and `contract` in parallel first (all parallel-safe), then `integration-isolated` in parallel, then `integration-shared` serially, then `behavior`, `hooks`, `e2e`, `chaos` serially (in that order).
- The transparency banner lists all lanes, the parallelism strategy, and a total ETA.
- Total elapsed time is less than 10 minutes on reference hardware.
- Exit code is the OR of all lane exit codes (non-zero if any lane fails).

---

### Scenario S-4: CI runs `cos-test cluster --lane <each>` per shard

**Given** a CI pipeline runs one `cos-test cluster --lane <lane>` command per shard,
**When** each shard executes independently,
**Then**:
- Results are comparable to the current Makefile shard-a / shard-b split (no test is silently skipped or duplicated across shards).
- The `unit` shard completes in under 2 minutes; stateful lanes (integration-shared, behavior, hooks) complete in under 5 minutes each.
- No test output contains race condition markers (e.g., `ResourceWarning`, duplicate file write errors).

---

### Scenario S-5: User runs old `make test-no-docker`

**Given** the change has landed and a developer runs `make test-no-docker`,
**When** the Makefile target executes,
**Then**:
- A deprecation warning is printed to stderr: `DEPRECATED: make test-no-docker — use: cos-test broad`.
- The underlying tests still run and produce results equivalent to the pre-change behavior.
- Exit code reflects actual test results (not just the warning).

---

### Scenario S-6: User runs `pytest -m unit` directly

**Given** the auto-marker injection hook is active in `tests/conftest.py`,
**When** a developer runs `pytest -m unit tests/unit/` directly,
**Then**:
- Every file under `tests/unit/` is collected (auto-injected `unit` marker ensures no gaps).
- `TestRealFilesIntegration` is not present in `tests/unit/` so does not appear.
- `pytest --collect-only -m unit tests/unit/ --strict-markers` exits 0 (all markers registered in `pytest.ini`).
- The collected test count matches the count returned by `cos-test cluster --lane unit --collect-only`.

---

### Scenario S-7: `test_global_verify.py` runs in parallel with `-n 4`

**Given** the fix for `test_global_verify.py` has landed (baseline file written to `tmp_path`),
**When** `pytest -n 4 tests/contracts/test_global_verify.py` is run three consecutive times,
**Then**:
- All three runs exit 0.
- No `FileExistsError`, `JSONDecodeError`, or partial-write failures appear in output.
- The `verify-baseline/` directory under the real repo root (`.cognitive-os/runtime/`) is NOT modified during the run.

---

### Scenario S-8: `cos-test focused` with empty git diff

**Given** a developer has no uncommitted changes and is on the merge-base commit,
**When** they run `cos-test focused`,
**Then**:
- The transparency banner states: `focused mode: no changed files detected — falling back to --lf (last-failed) mode`.
- If there are no last-failed tests, a clear message is printed: `No changed files and no previously-failed tests. Nothing to run.`
- Exit code is 0.
- The command completes in under 5 seconds.

---

### Scenario S-9: `cos-test cluster` with a lane that has zero matching tests

**Given** a developer runs `cos-test cluster --lane chaos` on a branch where no chaos tests exist,
**When** the command executes,
**Then**:
- The banner is still printed with the lane name and worker count.
- Pytest exits with a `no tests ran` warning (not an error).
- `cos-test` exits 0 (zero failures is success; zero tests is a warning, not a failure).
- The output contains: `WARNING: lane 'chaos' collected 0 tests`.

---

## 3. Non-Functional Requirements

### NFR-1: Wall-time targets

| Command | Target | Reference hardware |
|---|---|---|
| `cos-test focused` (1–3 file diff) | < 30 s | 8-core laptop, no Docker |
| `cos-test cluster --lane unit` | < 2 min | Same |
| `cos-test cluster --lane audit` | < 2 min | Same |
| `cos-test cluster --lane contract` | < 2 min | Same |
| `cos-test cluster --lane integration-isolated` | < 3 min | Same |
| `cos-test cluster --lane integration-shared` | < 5 min | Docker available |
| `cos-test broad` | < 10 min | Docker available |

### NFR-2: Marker coverage

100% of test files under `tests/{unit,integration,audit,contracts,behavior,e2e,hooks,chaos}/` MUST have at least one path-derived lane marker after auto-injection. Verified by a new audit test: `tests/audit/test_marker_coverage.py`.

### NFR-3: Flake rate regression budget

Zero increase in flake rate allowed. Specifically: the contracts lane flake rate (currently tracked in CI history) MUST NOT increase after the parallel flip. A test that was passing serially and fails under parallel is a bug in the fix, not an acceptable regression.

### NFR-4: Deprecation warning coverage

Every legacy Makefile target that is redirected MUST emit exactly one deprecation warning per invocation on stderr. The warning MUST include the replacement command. Verified by `make <target> 2>&1 | grep -ic deprecat` ≥ 1.

### NFR-5: pytest.ini marker completeness

`pytest --collect-only --strict-markers` on the entire test suite MUST exit 0 after the change. This validates REQ-7 without requiring any specific lane to be run.

---

## 4. Lane Registry

This is the durable artifact that ADR-069 will codify.

| Lane | Path | Parallel-Safe | Why |
|---|---|---|---|
| unit | tests/unit/ | yes | No shared state; all fixtures use tmp_path or monkeypatch; pure in-process logic |
| audit | tests/audit/ | yes | No pytest fixtures at all; pure Path.rglob() file scans; no side effects |
| contract | tests/contracts/ | yes (after REQ-6 fix) | Mostly pure file reads; one shared-state offender (test_global_verify.py) fixed by REQ-6 |
| integration-isolated | tests/integration/ marked `not docker` | yes | Uses tmp_path only; no session-scoped fixtures; isolated subprocess calls |
| integration-shared | tests/integration/ marked `docker` | no | Requires session-scoped Docker containers (PostgreSQL, Valkey, ClickHouse); must be serial |
| behavior | tests/behavior/ | no | Hook chain state is process-global; parallel execution would corrupt hook invocation order |
| hooks | tests/hooks/ | no | Mutates settings.json; shared real-file state between tests |
| e2e | tests/e2e/ | no | Full system under test; single instance; ordering matters |
| chaos | tests/chaos/ | no | Fault injection against real infra; concurrent faults would interfere |

**Escalation order for `cos-test broad`**: `unit` + `audit` + `contract` (parallel) → `integration-isolated` (parallel) → `integration-shared` (serial) → `behavior` → `hooks` → `e2e` → `chaos`.

---

## 5. Edge Cases

### EC-1: Empty git diff in `focused` mode

When `git diff --name-only <merge-base>...HEAD` returns no output (developer is on merge-base with no local changes), `cos-test focused` MUST fall back to `--lf` (last-failed) mode. If `--lf` also returns no tests, the command MUST print an informative message and exit 0. It MUST NOT attempt to run the entire suite as a fallback — that is `cos-test broad`'s responsibility.

### EC-2: Lane with zero matching tests

When `cos-test cluster --lane <name>` collects zero tests (e.g., `chaos` lane on a branch with no chaos tests yet), the command MUST exit 0 and print a `WARNING: lane '<name>' collected 0 tests`. It MUST NOT exit non-zero solely because no tests were collected — that would cause CI shards to fail spuriously on branches that haven't yet added tests for a given lane.

### EC-3: xdist worker crash during parallel contracts run

If a pytest-xdist worker crashes mid-run (e.g., OOM, signal), the remaining workers MUST continue and report results for their allocated tests. The master process MUST report the crashed worker's tests as `ERROR` (not `PASS`). The exit code MUST be non-zero. This behavior is inherited from xdist; the spec requires that the fix for REQ-6 does not introduce any new state that would cause a worker crash to corrupt other workers' test outcomes.

### EC-4: pytest-testmon database stale in `focused` mode

If the pytest-testmon `.testmondata` file is stale (e.g., after a rebase that rewrites many commits), `cos-test focused` MUST detect the stale state (testmon's own stale-detection or a file-age heuristic) and fall back to `--lf --ff -x` without testmon. It MUST print: `WARNING: testmon database may be stale — falling back to --lf mode`. It MUST NOT silently run zero tests because testmon reports no coverage for the changed files.

### EC-5: macOS git config lock under parallel `test_installer.py`

When `tests/integration/test_installer.py::TestProjectGitignore` runs in parallel (as part of `integration-isolated` lane), multiple workers call `git init` in separate `tmp_path` directories simultaneously. On macOS, `git init` may attempt to read `~/.gitconfig` which can experience advisory locks under high concurrency. If this causes a worker to fail with `error: could not lock config file`, the test MUST be decorated with `@pytest.mark.xdist_group("git-installer")` to serialize all `git init` tests within a parallel run. This edge case MUST be addressed before the `integration-isolated` lane is flipped to parallel.

### EC-6: `cos-test focused` on a file with no associated tests

When a changed file has no test file that imports it and testmon has no coverage record for it, `cos-test focused` MUST NOT silently skip validation. It MUST fall back to the `--lf --ff -x` mode and notify: `WARNING: no test coverage found for <file> — running last-failed tests instead`. The developer is responsible for adding tests; the tool must not pretend coverage exists.

### EC-7: `pytest.ini` `--strict-markers` and auto-injected markers from plugin context

If `pytest_collection_modifyitems` injects a marker that is not yet registered in `pytest.ini` (e.g., during a partial migration), `--strict-markers` will raise `PytestUnknownMarkWarning` promoted to error. The spec requires that REQ-7 (register all markers in `pytest.ini`) lands in the SAME batch as REQ-8 (auto-injection hook). These two requirements MUST be deployed atomically to avoid a window where injection is active but markers are unregistered.

---

## 6. Out of Scope

The following items are explicitly excluded from this change. They were carried forward from the proposal.

- `scripts/detect_runner_capacity.py` (ADR-068, Phase 1, already shipped) — no redesign.
- `tests/integration/conftest.py` session-scoped Docker fixtures — correct as-is; do not touch.
- `cmd/cos-test/` TUI core — extend only; do not rewrite or deprecate.
- `tests/e2e/`, `tests/behavior/`, `tests/hooks/`, `tests/chaos/` — correctly serial; keep them serial.
- Engram mock in unit tests — out of scope.
- CI workflow files (`.github/workflows/`) — no changes to GitHub Actions.
- Worker scheduling algorithm — reuse existing ADR-068 output; do not redesign.
- Security, payment, or auth flows — not touched by this change.

---

## Appendix: Requirement-to-Proposal Traceability

| REQ | Proposal Section | Explore Evidence |
|---|---|---|
| REQ-1 | §2d (cos-test extension), §4 (approach) | Finding 1 (cos-test CLI exists), Q5 (escalation ladder) |
| REQ-2 | §2d (focused mode) | Q5 (what focused means), Risk 1 (testmon stale) |
| REQ-3 | §2d (cluster mode), §6 AC2, AC4 | Finding 1, Claim 5 (xdist already in use) |
| REQ-4 | §2d (broad mode), §6 AC5 | Finding 7 (Makefile shard design) |
| REQ-5 | §2f (transparency layer) | Q5 (escalation ladder UX) |
| REQ-6 | §2c (hard prereq #1) | Claim 1 PARTIAL, Finding 3, Risk 1 |
| REQ-7 | §2a (marker registry), §2c marker backfill | Claim 4 CONFIRMED, Finding 4, Risk 7 |
| REQ-8 | §2a (auto-marker injection) | Claim 4, Q4 (auto-marker scope) |
| REQ-9 | §2c (TestRealFilesIntegration relocation) | Claim 3, Finding 5, Q3 |
| REQ-10 | §2e (Makefile redirection) | Finding 6, Finding 7, Risk 6 |
| REQ-11 | §2e (/run-tests skill update) | Finding 6 (skill consumer) |
| REQ-12 | §2b (integration sub-lanes) | Claim 2 CONFIRMED, Q1 |
| REQ-13 | §2a (marker parity) | Claim 4, Q4 |
