# Test Suite Documentation

## Overview

The luum-agent-os test suite contains **~5639 tests** across **195 test files**, organized into four categories: unit, behavior, integration, and system. Tests are executed via pytest and surfaced through a Go-based TUI dashboard (`cos-test`).

## Architecture

```
cos-test (Go: Cobra + Bubbletea + Lipgloss)
  └── ./run -m pytest --json-report
        └── tests/
              ├── unit/          (94 files, ~2823 tests)
              ├── behavior/      (73 files, ~1636 tests)
              ├── integration/   (17 files, ~259 tests)
              ├── system/        (5 files, 25 tests)
              └── conftest.py + pytest.ini
```

- **cos-test** is a Go binary (`cmd/cos-test/`) built with Cobra (CLI), Bubbletea (TUI), and Lipgloss (styling). It wraps pytest with `--json-report` and renders results in a terminal dashboard.
- **conftest.py** provides shared fixtures, markers, and test configuration.
- **pytest.ini** defines marker registrations and default options.

## Test Categories

### Unit Tests (~2823 tests, 94 files)

Fast, isolated tests with no external dependencies. Validate individual functions and state machines.

| File | Tests | Description |
|------|-------|-------------|
| `test_circuit_breaker.py` | Circuit breaker state machine | CLOSED/OPEN/HALF-OPEN transitions, thresholds, reset behavior |
| `test_safe_jsonl.py` | JSONL append safety | Safe append operations, concurrent writes, flock-based locking |
| `test_execute_repair.py` | Repair execution | Repair dispatch, language detection heuristics |
| `test_semantic_search.py` | Fuzzy matching | Registry lookup, semantic similarity scoring |
| `test_eval_repo_parsing.py` | GitHub URL parsing | Repository URL normalization and component extraction (skill: repo-scout) |
| `test_eval_repo_scoring.py` | Repository scoring | License validation, activity scoring, auto-reject criteria (skill: repo-scout) |
| `test_remediation.py` | Remediation registry | CRUD operations on the remediation registry |

### Behavior Tests (~1636 tests, 73 files)

Validate business logic, hook contracts, skill structures, and protocol compliance without requiring Docker or external services.

| File | Tests | Description |
|------|-------|-------------|
| `test_hooks_batch1.py` | 15 hooks | dod-gate, secret-detector, pre-compaction-flush, auto-verify, agent-checkpoint, agent-prelaunch, architecture-compliance, completeness-check, doc-sync-detector, epic-task-detector, error-pattern-detector, infra-intent-detector, result-truncator, skill-tracker, trust-score-validator |
| `test_hooks_batch2.py` | 14 hooks | auto-skill-generator, cognitive-os-health, conversation-capture, engram-auto-import, engram-auto-sync, memu-sync, metrics-calibrator-trigger, paperclip-sync, pre-cleanup-snapshot, session-cleanup, session-knowledge-extractor, session-resume, sync-to-repo, tool-discovery-trigger |
| `test_hook_triggers.py` | 4 conditional hooks | Hook trigger condition evaluation |
| `test_skills_batch1.py` | 23 skills | Structural validation (frontmatter, required sections, naming) |
| `test_skills_batch2.py` | 21 skills | Structural validation (frontmatter, required sections, naming) |
| `test_gen_eval_loop.py` | Loop decisions | Generator-evaluator loop verdict handling and retry logic |
| `test_sprint_contracts.py` | Task verification | Sprint task verification line validation |
| `test_harness_audit.py` | Classification | Hook, rule, and skill classification audit |
| `test_sdd_transitions.py` | SDD phases | Phase transition validation across the SDD dependency graph |
| `test_self_install.py` | 29 tests | Framework auto-sync: bulk upgrade, content verification, performance, edge cases, real repo scenarios |
| `test_phase_system.py` | Phase detection | Phase detection logic and constitutional gate enforcement |
| `test_self_improvement.py` | Self-improvement | KPI triggers, metrics collection, protocol compliance |
| `test_file_locking.py` | File locking | Cross-session file locking correctness |
| `test_private_mode.py` | Privacy gate | Privacy gate logic and mode switching |
| `test_resource_governor.py` | Resource budgets | Resource budget enforcement and limit handling |
| `test_session_isolation.py` | Session independence | Session state isolation guarantees |
| `test_contract_drift.py` | Contract drift | HTTP call extraction (Go/TS/Python), URL normalization, drift comparison, ignore patterns, report generation |
| `test_proposal_conflicts.py` | Proposal conflicts | Proposal overlap detection between concurrent changes |
| `test_apply_next_batch.py` | Batch application | Remaining task calculation and next batch suggestion |
| `test_staleness_tracking.py` | Staleness | Discovery refresh tracking and expiry detection |
| `test_sprint_planning.py` | Sprint planning | Capacity calculation and task assignment |
| `test_sdd_governance.py` | SDD governance | Compliance scoring and rollback decision logic |

### Integration Tests (~259 tests, 17 files)

Require Docker. Use testcontainers to spin up **17 Docker services** on demand. Marked with the `docker` pytest marker.

| File | Tests | Services |
|------|-------|----------|
| `test_databases.py` | Database connectivity | Postgres (x2), MySQL, Valkey, ClickHouse |
| `test_app_services.py` | Application services | Langfuse web + worker, LiteLLM, Jupyter, Opik backend |
| `test_platform_services.py` | Platform services | Paperclip, MemU, Cognee, SeaweedFS, Automaker, NeMo, Opik frontend |
| `test_eval_frameworks.py` | Eval frameworks | DeepEval + RAGAS import and API validation |
| `test_e2e_flows.py` | End-to-end flows | 5 multi-service flows using `testcontainers` for isolated observability/memory/reference stacks |
| `test_service_health.py` | Service health | Compose contract + opt-in localhost probes for reference stacks; does not start optional services |
| `test_repair_chain.py` | Repair chain | Error learning and dispatch across services |
| `test_metrics_rotation.py` | Metrics rotation | Truncation and archiving pipelines |
| `test_opik_integration.py` | Opik SDK | Opik SDK validation against running service |
| `test_cognee_integration.py` | Cognee SDK | Cognee SDK validation against running service |

`test_service_health.py` is intentionally lighter than the `testcontainers`
lanes. It verifies that reference stacks such as Opik and Cognee remain modeled
correctly in `docker-compose.cognitive-os.yml` and in `cognitive-os.yaml`, but
it does not imply they are part of the default local product path. If a test
needs to prove those stacks actually boot and serve traffic in isolation, prefer
the `testcontainers` integration lanes instead of turning default-lane smoke
tests into implicit Docker bring-up.

### System Tests (25 tests, 5 files)

Validate configuration files, container state, and runtime consistency.

| File | Tests | Description |
|------|-------|-------------|
| `test_config.py` | Configuration | `cognitive-os.yaml` schema and value validation |
| `test_docker.py` | Containers | Running container status checks |
| `test_docker_stack.py` | Docker stack | Compose file validity and image availability |
| `test_metrics.py` | Metrics | JSONL file validity and schema conformance |
| `test_rules.py` | Rules | Rule file consistency and required fields |

## Running Tests

### Official `cos-test` Defaults

Use these entry points before reaching for raw pytest. They preserve summaries,
JUnit, inventories, and resource-policy metadata under
`.cognitive-os/reports/test-runs/`.

| Use case | Command |
|---|---|
| Local quick iteration | `make test-local-fast` or `cos-test focused` |
| Laptop-friendly broad validation | `make test-laptop` |
| Local broad without Docker | `make test-local-wide-no-docker` or `cos-test broad --no-docker` |
| CI / pre-release default | `make test-ci-default` or `cos-test broad --no-docker --ci` |
| Slow integration without Docker | `make test-integration-no-docker` or `cos-test cluster --lane integration` |
| Docker/testcontainers explicit | `make test-docker-explicit` |
| Optional/cost-bearing explicit | `make test-optional-cost` |

The default broad lane is intentionally non-optional. Docker-capable and
cost-bearing lanes are opt-in so local laptops and CI jobs do not start heavy
services or hosted evaluations by surprise. The integration lane is also
explicit because it exercises live session/install workflows and can exceed the
bounded CI default even when Docker tests are excluded.

`make test-laptop` is the preferred broad local command when you want useful
coverage without making the workstation feel unusable. It runs the core
non-Docker lanes with `COS_TEST_WORKERS_MAX=2` and intentionally skips
integration, e2e, optional/cost-bearing lanes, and chaos. Use it for normal
local confidence after multi-file changes.

`make test-ci-default` is a CI/pre-release gate, not a tight development loop.
It runs the canonical broad non-Docker plan with CI settings and may take long
enough to slow a laptop. Use it before push/release or in CI; do not run it
constantly during day-to-day edits.

### Persistent Local Run Artifacts

Use `scripts/pytest-with-summary.sh` for any repair-oriented partial or full
test run. It preserves the full output, a short summary, failure snippets,
JUnit XML, metadata, and the exit code under
`.cognitive-os/reports/test-runs/`, which is ignored by git.

```bash
bash scripts/pytest-with-summary.sh -- tests/unit/test_example.py -q -ra
bash scripts/pytest-with-summary.sh -- tests/ -q --tb=short
```

The wrapper intentionally runs broad/stateful lanes serially unless you pass an
explicit worker override. This keeps full-suite and non-Docker repair evidence
comparable instead of mixing real failures with xdist worker death or shared
state races. Unit-only lanes may still use adaptive parallelism by default.

To force parallelism for a known-safe lane, pass `-n` directly or set
`COS_PYTEST_WORKERS=auto|N`.

While the repair effort is still separating core behavior from optional
reference stacks, prefer a broad non-Docker lane before running the full suite:

```bash
bash scripts/pytest-with-summary.sh -- tests/ -m 'not docker' -q --tb=short -ra --disable-warnings --timeout=120 --timeout-method=thread --session-timeout=900 --maxfail=40
```

This lane is still intentionally broad and can be slow, but it should not start
testcontainers stacks. Use its `inventory.md` as the next repair queue instead
of rerunning `tests/` just to recover the failure list.

The latest run is linked at `.cognitive-os/reports/test-runs/latest`.
Prefer this wrapper while reducing broad-suite failures so interrupted or
partial runs remain analyzable across sessions.

`pytest-with-summary.sh` is intentionally not a SessionStart hook. Cognitive OS
previously ran pytest automatically at session start and produced orphaned
processes; broad test execution must stay explicit, with persistent artifacts,
until a bounded test lane is selected by the operator or CI.

### Host Tool Doctor

Use `scripts/cos-doctor-tools.sh` when you need proof that the current host can
see the active harness driver, declared dependencies, MCP registrations, and
optional tools such as Engram.

For the full Codex/Engram setup and expected output, see
[Codex Host Tooling Verification](manual-tests/codex-host-tooling-verification.md).

Installed projects also run `hooks/host-tool-doctor.sh` on SessionStart. That
hook schedules the doctor with the default dependency profile, caches the result
for 24 hours, and writes the latest report to
`.cognitive-os/reports/host-tools/latest.txt`. It is advisory by design: startup
must continue even when host tooling is incomplete.

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-tools.sh --profile default
```

The doctor verifies:

- active harness detection
- active settings driver presence and JSON shape
- native Codex lifecycle keys when Codex is active
- required/recommended tools from `manifests/dependencies.yaml`
- recommended MCP server dependencies from `manifests/dependencies.yaml`
- Engram CLI search
- Engram MCP stdio startup
- Codex config registration for Engram when Codex is active
- portable memory lifecycle viability through
  `scripts/cos-doctor-memory-lifecycle.sh`

The memory lifecycle doctor runs a synthetic isolated session. It verifies that
a Codex or Claude session can start the Engram launcher, detect and recover a
pending task, capture a relevant user prompt, write session-learning metrics,
write git context, write a resumable changelog, record session-end
crystallization, and emit the pre-compaction Engram save reminder. It runs
against a temporary project and does not run pytest.

To run only that lifecycle check:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-memory-lifecycle.sh --harness codex
```

Use `--profile full` to check the broader optional stack declared for full
installations:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-tools.sh --profile full
```

Run with `--strict` when optional tool warnings should fail the check:

```bash
COGNITIVE_OS_HARNESS=codex CODEX_PROJECT_DIR="$PWD" bash scripts/cos-doctor-tools.sh --strict
```

This command proves local availability and host configuration. If Codex config
was changed during setup, restart Codex so the host reloads MCP server
definitions before expecting new MCP tools to appear in-session.

`manifest-check.sh` is consumed by both the manual doctor command and the
SessionStart host-tool doctor. Required dependency failures are recorded as
doctor failures; recommended dependency gaps remain warnings unless the manual
doctor is run with `--strict`.

Each `pytest-with-summary.sh` run also gets a test inventory:

- `inventory.md` — human-readable repair queue, skipped/xfail/failure list,
  slowest tests, and heuristic tags such as `optional-lane`, `drift`,
  `aspirational`, `timeout`, and `false-positive-risk`.
- `inventory.json` — machine-readable version for later dashboards, agents, or
  repair automation.

You can regenerate the inventory without rerunning pytest:

```bash
python3 scripts/test_run_inventory.py --run-dir .cognitive-os/reports/test-runs/latest
```

If pytest times out before writing JUnit XML, the inventory falls back to the
captured stack trace and records a synthetic timeout item. That keeps timeout
failures visible instead of turning them into empty reports.

Latency tests must distinguish product latency from host scheduler noise. When
an integration test measures a subprocess hook path, it may confirm one isolated
outlier with an immediate retry, but it must still fail repeated slow samples
and report both raw and effective timings. Do not mark latency regressions as
blanket `xfail`; acknowledged slow hooks belong in explicit allowlists so newly
slow hooks still fail.
For subprocess-based hook tests in the broad non-Docker lane, wall-clock p95
targets should reflect loaded-host execution rather than idle microbenchmarks;
`agent-working-dir-inject.sh` uses p95 <100ms and p99 <150ms for that reason.

Telemetry-driven hook p95 contracts should require enough samples to be
statistically meaningful. The default per-hook minimum is 20 samples; below
that, a couple of local synthetic or cold-start rows can dominate p95 and create
false product regressions.

CLI tests that parse stdout as JSON should treat stdout as a product contract.
Optional observability initializers, SDK banners, and exporter diagnostics must
be suppressed or redirected away from stdout. If a command emits machine-readable
JSON, tracing setup must not contaminate that stream.

This wrapper is part of the Cognitive OS development workflow. It is paired
with the OS-only `test-contract-repair` skill and should be used whenever
maintainers repair or classify this repository's own test suite. Projects that
install Cognitive OS should keep using their own test command, or a
project-facing testing skill, unless they explicitly opt into Cognitive OS
maintainer tooling.

### Without Docker (unit + behavior + system)

```bash
./run -m pytest tests/unit/ tests/behavior/ tests/system/ -v
```

### With Docker (integration + e2e)

```bash
./run -m pytest tests/ -v -m docker
```

Some Docker lanes are optional reference stacks rather than default product
requirements. For example, `tests/integration/test_app_services.py` starts
heavy application services with testcontainers and only runs when explicitly
requested:

```bash
COS_RUN_OPTIONAL_APP_SERVICES=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_app_services.py -q -ra
```

The heavier multi-service E2E reference flows are also opt-in:

```bash
COS_RUN_E2E_REFERENCE_FLOWS=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_e2e_flows.py -q -ra
```

Other testcontainers lanes are also explicit opt-ins:

```bash
COS_RUN_DATABASE_CONTAINERS=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_databases.py -q -ra
COS_RUN_PLATFORM_SERVICES=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_platform_services.py -q -ra
COS_RUN_OPIK_REFERENCE=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_opik_integration.py -q -ra
COS_RUN_COGNEE_REFERENCE=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_cognee_integration.py -q -ra
COS_RUN_SMART_INFRA_CONTAINERS=1 bash scripts/pytest-with-summary.sh -- tests/integration/test_smart_infra_containers.py -q -ra
```

`tests/contracts/test_optional_docker_lanes.py` enforces this policy so any new
integration test that creates testcontainers must declare and document a
`COS_RUN_*` opt-in flag before it can enter the repository.

### Specific category

```bash
./run -m pytest tests/behavior/ -v
```

### TUI dashboard

```bash
cd cmd/cos-test && go build -o cos-test . && ./cos-test dashboard
```

### Watch mode

```bash
./cos-test watch
```

### Single file

```bash
./run -m pytest tests/unit/test_circuit_breaker.py -v
```

## Coverage

| Category | Files | Tests | Percentage |
|----------|-------|-------|------------|
| Unit | 94 | ~2823 | ~50% |
| Behavior | 73 | ~1636 | ~29% |
| Integration | 17 | ~259 | ~5% |
| System | 5 | 25 | <1% |
| **Total** | **195** | **~5639** | **100%** |

The unit test layer now carries the plurality of coverage. Behavior tests shifted focus from file-existence checks (reclassified as unit) to pure behavioral assertions — 65% of behavior tests verify runtime behavior, 3% are integration-style, and the remainder validate structural invariants. This keeps the feedback loop fast while ensuring real behavior is covered.

## Key Fixtures (conftest.py)

Four shared fixtures power the behavioral and unit layers:

| Fixture | What It Provides |
|---------|-----------------|
| `real_engram` | A real engram client backed by a temp SQLite DB — no MagicMock |
| `isolated_cos_home` | Temporary `COS_HOME` directory via `tmp_path` + monkeypatch |
| `override_settings` | Monkeypatches `cognitive-os.yaml` values without touching disk |
| `run_hook` | Executes a hook script with mock stdin JSON, captures stdout/stderr/exit code |

## Adding New Tests

### 1. Choose the right category

- **Unit** (`tests/unit/`): Pure functions, state machines, parsers. No I/O, no Docker.
- **Behavior** (`tests/behavior/`): Hook contracts, skill validation, protocol logic. May read files but no external services.
- **Integration** (`tests/integration/`): Requires Docker services. Use testcontainers or the `docker` marker.
- **System** (`tests/system/`): Config validation, container checks, file consistency.

### 2. File naming

All test files must follow the pattern `test_*.py` and live in the appropriate category directory.

### 3. Test structure

```python
"""Tests for <component>."""
import pytest

class TestComponentName:
    """<Component> behavior tests."""

    def test_specific_behavior(self):
        """Should <expected behavior>."""
        # Arrange
        ...
        # Act
        ...
        # Assert
        assert result == expected

    @pytest.mark.parametrize("input,expected", [...])
    def test_parameterized(self, input, expected):
        """Should handle <varied inputs>."""
        assert function(input) == expected
```

### 4. Markers

Use pytest markers to classify tests that need special handling:

```python
@pytest.mark.docker       # Requires Docker (integration tests)
@pytest.mark.slow         # Long-running test
```

### 5. Fixtures

Shared fixtures live in `conftest.py`. Category-specific fixtures can go in a local `conftest.py` within the category directory.

### 6. Integration test pattern (testcontainers)

```python
@pytest.mark.docker
class TestServiceIntegration:
    def test_service_responds(self, service_container):
        """Service should respond to health check."""
        response = requests.get(f"http://localhost:{service_container.port}/health")
        assert response.status_code == 200
```

## CI/CD Integration

The test suite integrates into CI/CD pipelines through pytest's JSON report output:

```bash
./run -m pytest tests/ --json-report --json-report-file=report.json
```

The `cos-test` TUI consumes this report format. CI pipelines can:

1. Run the non-Docker suite (unit + behavior + system) on every push.
2. Run the full suite including integration tests on PR merges or scheduled builds (requires Docker).
3. Parse `report.json` for pass/fail counts and failure details.

Recommended CI stages:

| Stage | Command | When |
|-------|---------|------|
| Fast check | `./run -m pytest tests/unit/ tests/behavior/ -v` | Every push |
| System check | `./run -m pytest tests/system/ -v` | Every push |
| Integration | `./run -m pytest tests/ -v -m docker` | PR merge, nightly |
