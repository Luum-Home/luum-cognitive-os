# Design: Test Runner Ergonomics

> SDD design phase. Source: proposal observation #14951 (`sdd/test-runner-ergonomics/proposal`),
> explore observation #14950 (`sdd/test-runner-ergonomics/explore`).
> Phase: reconstruction. Complexity: Large.

## 1. Component Architecture

```
                            user / orchestrator / CI
                                       |
                                       v
  +------------------+   +------------------------------------+
  |   Makefile       |   |        cmd/cos-test (Go)           |
  | (deprecation     |-->|  cobra root.go                     |
  |  shim, 1 cycle)  |   |  +- run.go        (existing)       |
  +------------------+   |  +- focused.go    (NEW)            |
                         |  +- cluster.go    (NEW)            |
  +------------------+   |  +- broad.go      (NEW)            |
  | skills/run-tests |-->|  +- coverage.go   (existing)       |
  | (SKILL.md, redir)|   |  +- watch.go      (existing)       |
  +------------------+   |  +- dashboard.go  (existing)       |
                         +-----------------+------------------+
                                           |
                                           | invokes (preserves contract)
                                           v
                         +-----------------+------------------+
                         |  scripts/pytest-with-summary.sh    |
                         |  - YAML-aware via                  |
                         |    --workers/--lane args from      |
                         |    cos-test (no bash YAML parsing) |
                         |  - reads test-lanes.yaml ONLY when |
                         |    invoked directly (legacy)       |
                         +-----------------+------------------+
                                           |
                                +----------+-----------+
                                v                      v
                  scripts/detect_runner_capacity.py   pytest
                  (ADR-068, unchanged)                (with conftest hooks)
                                                       |
                                                       v
                                       +---------------+----------------+
                                       | tests/conftest.py              |
                                       |  pytest_collection_modifyitems |
                                       |  (auto-marker injection)       |
                                       +---------------+----------------+
                                                       |
                                                       v
                                              pytest.ini markers
                                              + .cognitive-os/test-lanes.yaml
                                                (canonical lane registry)

  Reports & history:
  .cognitive-os/reports/test-runs/<run-id>/inventory.md  (ETA source for banner)

  Contract test (existing, gets updated):
  tests/contracts/test_local_connected_systems_validation_docs.py
    - regex accepts BOTH `pytest-with-summary.sh` and `cos-test cluster`
      during deprecation cycle
```

**Boundaries**:
- `cmd/cos-test` is the canonical CLI. New subcommands (`focused`, `cluster`, `broad`) live alongside `run`.
- `pytest-with-summary.sh` keeps its current interface; `cos-test` invokes it with explicit `--workers N` and `--lane <name>` so bash never needs to parse YAML.
- `test-lanes.yaml` is consumed by Go (cos-test) and by Python (conftest tooling); bash only consumes flags.
- `tests/conftest.py` is the only place auto-markers are injected (single source of truth).

## 2. `cmd/cos-test` Subcommand Design

All three new subcommands share infrastructure from the existing `Runner` package
(`cmd/cos-test/internal/runner`). Reuse, do not duplicate. Each subcommand:
1. Resolves inputs (git diff, lane name, "all").
2. Loads `.cognitive-os/test-lanes.yaml`.
3. Computes worker count via `detect_runner_capacity.py` + lane policy.
4. Renders a 5-line banner to stdout.
5. Aggregates ETA from `.cognitive-os/reports/test-runs/*/inventory.md` (last N=10 runs, p50 wall time per lane).
6. Delegates to `Runner.Execute(opts)` which shells to `scripts/pytest-with-summary.sh` with explicit args.

### 2.1 `cos-test focused`

**Cobra signature**:
```
cos-test focused [flags]
  --since <ref>            (default: merge-base origin/main..HEAD)
  --include-uncommitted    (default: true)
  --testmon                (default: auto-detect)
  --workers <n>            (default: auto via ADR-068)
  --dry-run                (print plan, do not execute)
```

**Internal flow**:
1. Resolve diff: `git diff --name-only $(git merge-base origin/main HEAD)..HEAD` + `git diff --name-only` (uncommitted).
2. Map changed files → candidate test set (see §3).
3. If candidate set empty → fallback `pytest --lf --ff -x`.
4. Detect lane(s) covered by candidates; if any are `parallel: false`, fall back to serial with banner annotation.
5. Always pass `-n auto` when lanes allow parallel.
6. Invoke `pytest-with-summary.sh` with `--workers N --tests <file1> <file2> ...`.

**Banner sample (5–7 lines)**:
```
[cos-test focused] lane=unit+integration  tests=14  workers=auto:8 (ADR-068, 16 cores avail)
[cos-test focused] basis: 7 changed files since origin/main + 2 uncommitted
[cos-test focused] eta: ~22s (p50 of last 10 runs, +/- 6s)
[cos-test focused] kill-switch: COS_PYTEST_WORKERS=0 forces serial
[cos-test focused] starting...
```

### 2.2 `cos-test cluster --lane <name>`

**Cobra signature**:
```
cos-test cluster --lane <name> [flags]
  --lane <unit|integration|audit|contract|behavior|e2e|hook|chaos|architecture>  (required)
  --workers <n>     (default: from test-lanes.yaml policy)
  --markers <expr>  (extra -m filter, ANDed with lane)
  --dry-run
```

**Internal flow**:
1. Validate `--lane` against test-lanes.yaml registry.
2. Resolve `paths` from registry → pytest target list.
3. Resolve worker count: `parallel: true` → `auto`; `parallel: false` → `0`; `parallel: marker` → `auto` with `-m "not <marker_serial>"` for parallel batch then re-run serial slice.
4. ETA: aggregate p50 of last 10 same-lane runs from inventory history.
5. Invoke `pytest-with-summary.sh --lane <name> --workers N`.

**Banner sample**:
```
[cos-test cluster] lane=audit  tests=87  workers=auto:8 (parallel-safe per registry)
[cos-test cluster] paths: tests/audit/
[cos-test cluster] eta: ~18s (p50 of last 10 audit runs, +/- 4s)
[cos-test cluster] kill-switch: COS_FORCE_SERIAL_LANES=audit
[cos-test cluster] starting...
```

### 2.3 `cos-test broad`

**Cobra signature**:
```
cos-test broad [flags]
  --skip-docker     (omit lanes requiring Docker)
  --skip-slow       (omit lanes with p50 > threshold)
  --workers <n>
  --dry-run
```

**Internal flow**:
1. Iterate lanes in execution order: `unit, audit, contract, integration, behavior, hook, chaos, e2e, architecture`.
2. For each lane, run as if `cluster --lane <name>` with the lane's policy.
3. Stop on first lane FAIL unless `--continue` is set.
4. ETA = sum of per-lane p50.

**Banner sample**:
```
[cos-test broad] lanes=9 (unit,audit,contract,integration,behavior,hook,chaos,e2e,architecture)
[cos-test broad] workers vary per lane (see test-lanes.yaml)
[cos-test broad] eta: ~7m12s (sum of last-10 p50 per lane)
[cos-test broad] kill-switch: --skip-docker / --skip-slow flags
[cos-test broad] starting lane 1/9: unit...
```

### 2.4 ETA Source: inventory aggregation

**Location**: `.cognitive-os/reports/test-runs/<run-id>/inventory.md` (existing path per explore).

**Aggregation logic** (Go):
```
For each run-dir sorted desc by mtime, take last 10:
  Parse inventory.md for "lane: <name>  wall_time: <Xs>" lines
  Group by lane → list of durations
For each lane: p50 = median(durations); ci = p25..p75 spread
Cache result for the duration of one cos-test invocation
```

If <3 historical runs exist for a lane, banner prints `eta: ~unknown (history insufficient)`.

## 3. `focused` Mode Algorithm

**Input**:
- Default: `git diff --name-only $(git merge-base origin/main HEAD)..HEAD` ∪ `git diff --name-only` (uncommitted, staged + unstaged).
- Override: `--since <ref>` to use a different baseline.

**Mapping changed files → affected tests**:

1. **Same-name heuristic** (always applied):
   - `scripts/foo.py` → search `tests/unit/test_foo.py`, `tests/integration/test_foo*.py`, `tests/contracts/test_foo*.py`.
   - `lib/bar/baz.py` → `tests/unit/test_baz.py`, `tests/unit/bar/test_baz.py`.
   - `cmd/cos-test/internal/cli/run.go` → no Python test mapping; emit advisory "Go change — run `go test ./cmd/cos-test/...`".
   - `tests/<anything>` → that file is itself the affected test (run directly).
   - `pytest.ini`, `tests/conftest.py`, `.cognitive-os/test-lanes.yaml` → broaden to all lanes (treat as global config touch).

2. **Testmon transitive impact** (if `.cognitive-os/cache/testmon/.testmondata` exists):
   - Invoke `pytest --testmon-noselect --collect-only -q` to compute the testmon-derived selection for the diff.
   - Union with same-name results.
   - Skip if cache absent or stale (>7 days mtime) — log advisory "testmon cache absent or stale, using same-name only".

3. **Fallback** (if both produce empty set):
   - `pytest --lf --ff -x` (last-failed-first, exit-on-first-fail).

**Parallelism decision**:
- Compute the union lane set of selected tests via path → lane map.
- If all lanes have `parallel: true` → `-n auto`.
- If any lane has `parallel: false` → serial, banner annotates which lane forced serial.
- If `parallel: marker` lane present and selection includes serial-only marker → split into two pytest invocations (parallel batch first, serial batch second); banner notes "split run".

## 4. Auto-Marker Injection

**Location**: `tests/conftest.py`, function `pytest_collection_modifyitems(config, items)`.

**Algorithm** (pseudocode):
```
LANE_PATH_MAP = {
    "tests/unit/":         "unit",
    "tests/integration/":  "integration",
    "tests/audit/":        "audit",
    "tests/contracts/":    "contract",
    "tests/behavior/":     "behavior",
    "tests/e2e/":          "e2e",
    "tests/hooks/":        "hook",
    "tests/chaos/":        "chaos",
    "tests/architecture/": "architecture",
}

for item in items:
    rel = relative_to_repo_root(item.fspath)
    lane = first_match(LANE_PATH_MAP, rel)  # longest-prefix match
    if not lane:
        continue
    marker_obj = getattr(pytest.mark, lane)
    if item.get_closest_marker(lane) is None:
        item.add_marker(marker_obj)
```

**Properties**:
- **Additive only**: never strips an existing marker.
- **Idempotent**: `get_closest_marker(lane) is None` guard prevents double-adding on re-collection.
- **Strict-markers compatible**: every injected marker is also registered in `pytest.ini` (see §4.1).
- **Honors xdist_group, timeout, etc.**: those markers are independent of lane markers.

### 4.1 Marker Registry in `pytest.ini`

`pytest.ini` `markers =` block MUST list (canonical set):
```
unit
integration
audit
contract
behavior
e2e
hook
chaos
architecture
```
Plus existing utility markers: `slow`, `docker`, `isolated`, `engram_live`, `xdist_group`,
`requires_engram`, `forked`, `canary`, `timeout`.

Duplicate registrations in `tests/conftest.py:pytest_configure` and
`tests/integration/conftest.py:pytest_configure` are removed in this change.

## 5. Lane Reclassification — YAML Registry

**Path**: `.cognitive-os/test-lanes.yaml`

**Schema**:
```yaml
version: 1
lanes:
  unit:
    paths: [tests/unit/]
    parallel: true             # always -n auto
    marker_serial: ""          # unused when parallel=true
    stateful_reason: ""
    typical_wall_time_s: 30
  audit:
    paths: [tests/audit/]
    parallel: true
    marker_serial: ""
    stateful_reason: ""
    typical_wall_time_s: 25
  contract:
    paths: [tests/contracts/]
    parallel: true
    marker_serial: ""
    stateful_reason: ""
    typical_wall_time_s: 60
  integration:
    paths: [tests/integration/]
    parallel: marker           # parallel batch + serial batch on docker marker
    marker_serial: docker
    stateful_reason: "session-scoped Docker fixtures"
    typical_wall_time_s: 240
  behavior:
    paths: [tests/behavior/]
    parallel: false
    marker_serial: ""
    stateful_reason: "hook chain state, pre/post effect ordering"
    typical_wall_time_s: 90
  e2e:
    paths: [tests/e2e/]
    parallel: false
    marker_serial: ""
    stateful_reason: "end-to-end side effects"
    typical_wall_time_s: 180
  hook:
    paths: [tests/hooks/]
    parallel: false
    marker_serial: ""
    stateful_reason: "hook subprocess timing"
    typical_wall_time_s: 60
  chaos:
    paths: [tests/chaos/]
    parallel: false
    marker_serial: ""
    stateful_reason: "fault injection"
    typical_wall_time_s: 45
  architecture:
    paths: [tests/architecture/]
    parallel: true
    marker_serial: ""
    stateful_reason: ""
    typical_wall_time_s: 20
```

**Consumers**:
- `cmd/cos-test` (Go): primary consumer, parses with `gopkg.in/yaml.v3`.
- `scripts/pytest-with-summary.sh`: NOT a direct consumer. Receives `--workers N --lane <name>` from cos-test. Bash YAML parsing is avoided.
- For legacy direct invocations of `pytest-with-summary.sh` (no cos-test wrapper), the script falls back to its existing hardcoded behavior with a deprecation notice. After the deprecation cycle, the YAML becomes the only source of truth.

**`scripts/pytest-with-summary.sh:95` change**:
- Before: hardcoded `case` matching path patterns to force `_workers="0"`.
- After: respect `--workers N` flag from caller (cos-test). If invoked WITHOUT the flag (legacy path), use the existing case statement — but emit `[deprecation] direct invocation will lose lane awareness in next minor; use 'cos-test cluster' instead` to stderr.

## 6. Prerequisite Fixes Design

### 6.1 `tests/contracts/test_global_verify.py` shared-state fix

**Problem** (lines 29-33): writes baseline JSON to `PROJECT_DIR / ".cognitive-os" / "runtime" / "verify-baseline" / "{agent_id}.json"` — real repo path, shared across parallel workers.

**Fix design**:
- Replace module-level `PROJECT_DIR` constant usage in baseline path computation.
- Inject `tmp_path` fixture into each test that writes baseline; pass it as `COGNITIVE_OS_VERIFY_BASELINE_DIR` env var to the `global-verify.sh` subprocess.
- Update `global-verify.sh` to honor `COGNITIVE_OS_VERIFY_BASELINE_DIR` if set (reading default to `$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/runtime/verify-baseline`).

**Verification**:
- Run serial first: `pytest tests/contracts/test_global_verify.py` exits 0.
- Then parallel: `pytest -n 4 tests/contracts/test_global_verify.py` exits 0 across 3 consecutive runs.
- Check no files written under repo `.cognitive-os/runtime/verify-baseline/` after suite.

### 6.2 `tests/contracts/test_local_connected_systems_validation_docs.py:112` regex extension

**Problem**: asserts the recommended command in `docs/manual-tests/local-connected-systems-validation.md` is exactly `pytest-with-summary.sh`. When canonical command flips to `cos-test cluster`, this contract test fails.

**Fix design** (deprecation window):
- Change assertion from a strict equality to a regex `OR` match:
  ```
  pattern = r'(scripts/pytest-with-summary\.sh|cos-test\s+(cluster|broad|focused))'
  assert re.search(pattern, doc_content), "no canonical command found"
  ```
- Add inline comment: `# Accepts both during deprecation; remove pytest-with-summary.sh branch in vNEXT.`

**Final flip** (last batch of rollout): tighten regex to only `cos-test ...` after deprecation window closes.

## 7. Test Relocation

**Source**: `tests/unit/test_decision_triage.py` lines 307-413, class `TestRealFilesIntegration` (6 methods).

**Target**: NEW file `tests/integration/test_decision_triage_real_files.py`.

**Relocation contents**:
- `class TestRealFilesIntegration` (6 test methods, unchanged bodies).
- Imports:
  - `import scripts.decision_triage as dt`
  - Any helpers referenced (`from pathlib import Path`, etc.).
  - Top-level fixtures used by the class only.
- Add module-level marker: `pytestmark = pytest.mark.integration`.
- Add docstring: `"""Real-files integration tests for decision_triage. Moved from tests/unit per ADR-069."""`

**Source file cleanup** (`tests/unit/test_decision_triage.py`):
- Remove `class TestRealFilesIntegration` and only-used-by-class helpers.
- If a helper is used elsewhere in unit tests, hoist to `tests/_helpers/decision_triage_helpers.py` (new file) and re-import from both locations.
- Verify no other test in the file imports a name now removed.

**CI/doc reference grep** (must run before commit):
- `grep -rn "TestRealFilesIntegration" .` → 0 results outside the new file.
- `grep -rn "test_decision_triage.py::TestRealFilesIntegration" .` → 0 results.

## 8. Makefile Deprecation Shim

Each existing target gains a deprecation header then proxies to `cos-test`:

**Pattern** (applied to `test-fast`, `test-no-docker`, `test-no-docker-shard-a`, `test-no-docker-shard-b`):
```
test-fast:
	@echo "[deprecated] 'make test-fast' will be removed in next minor; use 'cos-test cluster --lane unit' instead" 1>&2
	@cos-test cluster --lane unit
```

**Mapping table**:
| Legacy target | Replacement |
|---|---|
| `make test-fast` | `cos-test cluster --lane unit` |
| `make test-no-docker` | `cos-test broad --skip-docker` |
| `make test-no-docker-shard-a` | `cos-test cluster --lane unit` |
| `make test-no-docker-shard-b` | `cos-test broad --skip-docker --skip-fast-lanes` (or sequence of clusters) |

**Lifecycle**: hold for one release cycle (per proposal §7). Remove in vNEXT+1.

## 9. `skills/run-tests/SKILL.md` Redirect

Replace skill body with:
- `cos-test focused` as default invocation when triggered by "run tests" with diff context.
- `cos-test cluster --lane <X>` when user specifies a lane.
- `cos-test broad` for "run all tests" or "full suite".
- Banner output is mandatory; the skill must not silence stdout.
- Legacy `pytest-with-summary.sh` invocations are removed from the skill body.

## 10. Banner / Transparency Design

**Format constraints**:
- Lines prefixed with `[cos-test <subcommand>]` for grep-ability.
- Always 5 lines, never more, never fewer (predictable for snapshot tests).
- Printed BEFORE any pytest output reaches stdout.
- Color: none in CI (`NO_COLOR` honored), gray on TTY.

**Mandatory fields** (per proposal AC9):
1. Lane(s) selected.
2. Test count (collected, not pre-collected estimate).
3. Worker count + reason (e.g., "auto:8 per ADR-068 on 16-core host").
4. ETA from history with confidence interval.
5. Kill-switch hint (env var or flag).

**Literal sample** (canonical 5-line box for `cos-test cluster --lane audit`):
```
[cos-test cluster] lane=audit  tests=87  workers=auto:8 (parallel-safe per registry)
[cos-test cluster] paths: tests/audit/
[cos-test cluster] eta: ~18s (p50 of last 10 audit runs, +/- 4s)
[cos-test cluster] kill-switch: COS_FORCE_SERIAL_LANES=audit
[cos-test cluster] starting...
```

## 11. ADR-069 Outline (to be written in apply phase)

**Title**: ADR-069 — Test Lane Taxonomy & Escalation Ladder.

**Sections**:
1. **Context**: three competing UX surfaces, over-classification of audit/contracts as serial, slow unit lane due to misclassified test class.
2. **Decision**:
   - `cmd/cos-test` is the canonical CLI entry point.
   - Lane registry lives in `.cognitive-os/test-lanes.yaml` (versioned schema).
   - Path-based markers are auto-injected via `pytest_collection_modifyitems`.
   - Escalation ladder: focused (diff-aware, <30s) → cluster (single lane, <2min) → broad (all lanes, <10min).
3. **Lane taxonomy table**: directory → marker → parallelism → typical wall time (mirrors §5 YAML).
4. **Parallel-safe contract**: a lane is parallel-safe iff every test isolates side effects to `tmp_path` or per-worker resources. Shared global state (real repo paths, real env vars) breaks parallel-safety.
5. **Why marker-based, not file-based split**: file moves break git blame, CI references, and import paths; markers are additive and reversible.
6. **Consequences**:
   - Pro: contributors get a single canonical command; CI shrinks for fast-lane runs.
   - Con: bash `pytest-with-summary.sh` callers must migrate within one cycle.
7. **Rollout**: cross-references rollout batches in proposal §7.
8. **Status**: Proposed.

ADR is WRITTEN in apply phase; this design only commits to the outline.

## 12. Risks Carried Forward + Design Mitigations

| # | Risk (proposal) | Design mitigation |
|---|---|---|
| R1 | `test_global_verify.py` real-repo write → races | §6.1 fixes via `tmp_path` injection + env var override. Verification harness runs `-n 4` × 3 to confirm no race before flipping serial guard. |
| R2 | Auto-markers break user `-m` filters | §4 algorithm is additive only; never removes a marker. ADR-069 §4 documents the path→marker map so `-m` filters stay predictable. New audit test asserts every test has ≥1 path-derived marker. |
| R3 | `TestProjectGitignore` parallel git init conflicts on macOS | Add `pytestmark = pytest.mark.xdist_group("git-installer")` to the class. Existing xdist_group infrastructure (already in use) handles this. Documented in test-lanes.yaml integration entry as a known constraint. |
| R4 | `--strict-markers` failures if `audit` only in conftest | §4.1: register all 9 lane markers in `pytest.ini`. Remove duplicate conftest registrations atomically with the registry change. |
| R5 | Two test runners (`cmd/cos`, `cmd/cos-test`) → user confusion | Settled in proposal §2(d): `cos-test` canonical. Design §1 reinforces: NO `test` subcommand added to `cmd/cos`. ADR-069 §2 commits to this. |
| R6 | Doc-contract tests fail when canonical command flips | §6.2: regex accepts BOTH commands during deprecation window; final tightening is the LAST rollout batch (per proposal §7 batch 9). |
| R7 | Moving `TestRealFilesIntegration` breaks CI references | §7 mandates pre-commit grep of CI configs/docs for the class name and source path. Atomic move + reference update in same commit. |

## 13. Testing Strategy for the Change Itself

| Test category | Path | What it verifies |
|---|---|---|
| Contract: YAML schema | `tests/contracts/test_test_lanes_yaml_schema.py` (NEW) | `.cognitive-os/test-lanes.yaml` matches schema; all 9 lanes present; no unknown keys; `parallel` ∈ {true, false, marker}. |
| Contract: marker registry | `tests/contracts/test_pytest_ini_marker_registry.py` (NEW) | All 9 lane markers registered in `pytest.ini` markers block. No duplicate registrations across conftest files. |
| Audit: every test has a lane marker | `tests/audit/test_lane_marker_coverage.py` (NEW) | `pytest --collect-only` shows every collected test has ≥1 lane marker (after auto-injection). |
| Integration: focused mode synthetic diff | `tests/integration/test_cos_test_focused.py` (NEW) | Create temp repo + synthetic diff (changed file + new file). Run `cos-test focused --dry-run`. Assert candidate test set matches expected mapping. |
| Integration: cluster mode | `tests/integration/test_cos_test_cluster.py` (NEW) | Run `cos-test cluster --lane unit --dry-run`. Assert banner has 5 lines, `--workers` resolves correctly, lane paths resolved from YAML. |
| Smoke (CI): `cos-test broad` end-to-end | `.github/workflows/test-smoke.yml` runs `cos-test broad --skip-docker --dry-run` | The new entry point at least plans the full pipeline without error. |
| Performance regression | `.cognitive-os/reports/test-runs/*/inventory.md` aggregator + alert | After each run, append `lane: <name>  wall_time: <Xs>` to inventory. CI compares run wall-time vs trailing 10-run p50; alerts if +20%. |
| Banner snapshot | `tests/contracts/test_cos_test_banner_format.py` (NEW) | For each subcommand, capture stdout prefix; assert exactly 5 lines; assert all 5 mandatory fields present (lane, tests, workers, eta, kill-switch). |
| Auto-marker idempotence | `tests/audit/test_auto_marker_idempotent.py` (NEW) | Collect twice in same process; assert no test gains duplicate lane markers. |

**Performance regression alert thresholds**:
- Lane wall-time > 1.2× p50 of trailing 10 → soft warning in CI.
- Lane wall-time > 1.5× p50 → hard fail (job exits non-zero).
- < 5 historical runs → no comparison; collect baseline.

---

**End of design document.**
