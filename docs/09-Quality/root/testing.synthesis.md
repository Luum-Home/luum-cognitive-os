---
type: quality-synthesis
source: docs/09-Quality/root/testing.md
provenance: "Canonical reference for the luum-agent-os pytest suite (~5639 tests, 195 files across unit/behavior/integration/system) and the cos-test TUI/CLI tooling used to run, report, and repair it."
---

## What it is

The primary test-suite reference doc: describes the ~5639-test, 195-file pytest suite under `tests/` (unit, behavior, integration, system categories), the Go-based `cos-test` dashboard that wraps pytest, and the full set of canonical run commands, artifact conventions, and repair workflows for maintaining the suite.

## Key mechanics

- **Categories**: Unit (~2823 tests/94 files, no I/O/Docker), Behavior (~1636 tests/73 files, hook/skill/protocol validation without Docker), Integration (~259 tests/17 files, Docker via testcontainers, `docker` marker), System (25 tests/5 files, config/container/runtime consistency).
- **cos-test** (`cmd/cos-test/`, Cobra+Bubbletea+Lipgloss) wraps `./run -m pytest --json-report` and renders a TUI dashboard; `conftest.py` + `pytest.ini` provide shared fixtures/markers.
- **Canonical entry points** (preferred over raw pytest) each preserve summaries/JUnit/inventories under `.cognitive-os/reports/test-runs/`: `make test-local-fast`/`cos-test focused` (quick iteration), `make test-laptop` (broad non-Docker, `COS_TEST_WORKERS_MAX=2`, skips integration/e2e/optional/chaos), `make test-laptop-integration` (SO-maintainer-only, serial, `nice -n 10`), `make test-ci-default`/`cos-test broad --no-docker --ci` (CI/pre-merge gate), `make test-release` (heaviest: CI default + integration + Docker/e2e), `make test-docker`, `make test-optional`.
- **Integration lane semantics**: resolves to `pytest-with-summary.sh --workers 0 --lane integration --timeout-seconds 900 --docker-policy forbidden --cost-policy free_only -- tests/integration/ -m not docker`; intentionally serial/slow because it covers live install/session workflows, Engram/Phoenix-adjacent checks, hook subprocesses, git ops, TCP waits — unsafe to blend with xdist. A 7-step escalation ladder is prescribed from `./cos-test focused` up to `make test-release`.
- **Governance gate ownership split**: `cos-test` owns selection/lane execution, `scripts/pytest-with-summary.sh` owns reporting transport, governance hooks (`global-verify`, `auto-verify`, `dod-gate`) must consume persisted artifacts via `scripts/cos_test_artifact_status.py` rather than launching their own pytest runs. Canonical machine-readable surfaces: `summary.txt`, `inventory.md`/`inventory.json`, `junit.xml`.
- **Repair tooling**: `scripts/cos-pytest-serial-repair` (serial maxfail=1 loop, resumable via `.cognitive-os/runtime/pytest-serial-repair-state.json`, exit 124 = budget/chunk timeout); `scripts/pytest-with-summary.sh` (persists full output/summary/failures/JUnit/metadata, runs broad/stateful lanes serially by default, `-n`/`COS_PYTEST_WORKERS` forces parallelism).
- **Opt-in Docker lanes**: `COS_RUN_OPTIONAL_APP_SERVICES`, `COS_RUN_E2E_REFERENCE_FLOWS`, `COS_RUN_DATABASE_CONTAINERS`, `COS_RUN_PLATFORM_SERVICES`, `COS_RUN_OPIK_REFERENCE`, `COS_RUN_COGNEE_REFERENCE`, `COS_RUN_SMART_INFRA_CONTAINERS`, `COS_RUN_ENGRAM_CLOUD_CONTAINERS`, `COS_RUN_HEADLESS_SERVICE_DOCKER`, `COS_RUN_GITHUB_REMOTE_INSTALL_SMOKE` — enforced by `tests/contracts/test_optional_docker_lanes.py` (any new testcontainers-using test must declare a `COS_RUN_*` flag).
- **Host Tool Doctor** (`scripts/cos-doctor-tools.sh`, run at SessionStart via `hooks/host-tool-doctor.sh`, 24h cache, advisory-only) verifies harness detection, dependencies, MCP registrations, Engram CLI/MCP startup, and via `scripts/cos-doctor-memory-lifecycle.sh` runs a synthetic session proving the full memory lifecycle (task recovery, prompt capture, session-learning, git-context, changelog, crystallization, pre-compaction reminder).
- **Test inventory**: every `pytest-with-summary.sh` run generates `inventory.md`/`inventory.json` (repair queue, skip/xfail/failure lists, slowest tests, heuristic tags like `optional-lane`, `drift`, `aspirational`, `timeout`, `false-positive-risk`), regenerable without rerunning pytest via `scripts/test_run_inventory.py`.
- **Latency-test discipline**: subprocess hook latency tests must distinguish product latency from host scheduler noise, retry only one outlier, fail repeated slow samples, avoid blanket `xfail`, and use allowlists for acknowledged-slow hooks (example: `agent-working-dir-inject.sh` p95 <100ms/p99 <150ms); telemetry-driven p95 contracts need a minimum of 20 samples.
- **Coverage table**: Unit 94/2823 (~50%), Behavior 73/1636 (~29%), Integration 17/259 (~5%), System 5/25 (<1%), Total 195/~5639.
- **Key fixtures**: `real_engram` (real SQLite-backed engram client, no MagicMock), `isolated_cos_home`, `override_settings`, `run_hook`.

## Relations & where used

- `cmd/cos-test/`, `scripts/pytest-with-summary.sh`, `scripts/cos-pytest-serial-repair`, `scripts/cos_test_artifact_status.py`, `scripts/test_run_inventory.py`, `scripts/cos-doctor-tools.sh`, `scripts/cos-doctor-memory-lifecycle.sh`, `manifests/dependencies.yaml`, `docker-compose.cognitive-os.yml`, `tests/contracts/test_optional_docker_lanes.py`, `docs/09-Quality/manual-tests/host-tooling-engram-mcp-verification.md`, `docs/09-Quality/manual-tests/engram-cloud-docker-sync.md`.
- Contrasts with `testing-cognitive-os-suite.md`, which documents a separate, smaller `.cognitive-os/tests/` self-check suite (not this pytest suite).

## Status / caveats

Test counts (~5639 tests, 195 files) and per-category numbers are point-in-time figures that will drift as the suite grows; treat as approximate/dated rather than a live count. No internal inconsistencies found in the file itself.
