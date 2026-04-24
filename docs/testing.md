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
| `test_eval_repo_parsing.py` | GitHub URL parsing | Repository URL normalization and component extraction |
| `test_eval_repo_scoring.py` | Repository scoring | License validation, activity scoring, auto-reject criteria |
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

### Without Docker (unit + behavior + system)

```bash
./run -m pytest tests/unit/ tests/behavior/ tests/system/ -v
```

### With Docker (integration + e2e)

```bash
./run -m pytest tests/ -v -m docker
```

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
