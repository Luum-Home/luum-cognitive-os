# Test Runner Role Taxonomy

**Status**: Active operational guide.  
**Source of truth**: ADR-072 and `.cognitive-os/test-lanes.yaml`.

Cognitive OS test tooling is intentionally split by role. The product should not
present every script as a generic “smoke” or “run everything” entry point. New
contributors should be able to answer two questions quickly:

1. **What test scope should I select?**
2. **Which primitive executes it and persists evidence?**

## Role model

| Role | Responsibility | Canonical primitive | Notes |
|---|---|---|---|
| Selection | Decide what should run: focused diff, one lane, broad sweep, optional lanes. | `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cos-test focused / cluster / broad` | Lane policy lives in YAML; pytest markers are runtime selection. |
| Execution | Run the selected test set with the right worker policy. | `cmd/cos-test` | `cos-test` is the user-facing entry point. |
| Reporting | Persist summaries, failures, inventory, JUnit, coverage, test-quality artifacts, and run history. | `scripts/pytest-with-summary.sh`, `tests/coverage-report.sh`, `scripts/cos_test_quality_audit.py` | Transport/reporting primitives. They should not own lane policy. |
| Governance | Enforce Definition of Done, coverage, auto-verify, quality gates, and budgets. | hooks/skills such as `auto-verify`, `dod-gate`, `pre-commit-gate`, `coverage-enforcement`, `test-quality-audit` | Governance consumes persisted evidence; it should not duplicate selection or execution logic. |
| Lifecycle | Track quality ratchets, baselines, repair ledgers, and historical drift. | metrics JSONL, baselines, repair ledgers | Lifecycle artifacts explain whether the suite is improving over time. |

## Canonical developer flow

| Situation | Command | Why |
|---|---|---|
| Tight iteration after editing one or a few files | `cos-test focused` | Uses changed files or explicit paths. |
| Validate one lane | `cos-test cluster --lane <name>` | Runs the lane according to registry parallel-safety policy. |
| Laptop-friendly broad validation | `make test-laptop` | Caps workers and skips integration/e2e/chaos/Docker/cost-bearing lanes. |
| Local broad without Docker | `cos-test broad --no-docker` or `make test-local-wide-no-docker` | Official local broad lane; skips Docker-capable lanes. |
| CI / pre-merge default | `cos-test broad --no-docker --ci` or `make test-ci-default` | Same policy as local broad, CI output mode. |
| Release gate | `make test-release` | CI default + explicit integration + Docker/e2e. |
| Slow integration without Docker | `cos-test cluster --lane integration` or `make test-integration-no-docker` | Explicit because integration contains live installer/session workflows. |
| Lower-priority laptop integration | `make test-laptop-integration` | Still slow/stateful; uses lower CPU priority. |
| Docker/e2e explicit | `make test-docker` | Docker/testcontainers never start from default broad. |
| Include cost-bearing or non-deterministic lanes | `make test-optional` | Optional lanes must be explicit. |
| Need persisted pytest artifacts directly | `bash scripts/pytest-with-summary.sh -- <pytest args>` | Reporting transport fallback; not the primary selection UX. |

## Legacy and compatibility scripts

These scripts are kept for compatibility or specific lifecycle niches. They must
not be presented as competing default entry points.

| Script | Role | Canonical replacement / usage |
|---|---|---|
| `scripts/cos-smoke.sh` | Opt-in critical-path startup smoke | Use when validating startup wiring specifically; otherwise use `cos-test broad`. |
| `scripts/test-cognitive-os.sh` | Legacy Layer-1 shell infrastructure runner | Use `cos-test cluster --lane hooks` or targeted shell checks unless explicitly testing legacy infra scripts. |
| `scripts/test-cognitive-os-full.sh` | Legacy three-layer shell pyramid runner | Use `cos-test broad`; run quality/LLM checks explicitly as optional governance. |
| `scripts/test-all.sh` | Legacy composite pytest + bash runner | Use `cos-test focused / cluster / broad`. |
| `scripts/run-all-tests.sh` | Legacy release/integrity sweep (Python + Go + file integrity) | Use for release hardening only; not for daily iteration. |
| `Makefile test-no-docker-*` | Deprecated CI compatibility shims | Kept for one release cycle; they proxy to `cos-test`. |

## Non-duplication rules

1. Selection policy belongs in `.cognitive-os/test-lanes.yaml` and `cos-test`.
2. Execution UX belongs in `cmd/cos-test`.
3. Persistent pytest reporting belongs in `scripts/pytest-with-summary.sh`;
   coverage reporting belongs in `tests/coverage-report.sh`; test-quality
   reporting belongs in `scripts/cos_test_quality_audit.py`.
4. Governance hooks may require or inspect test evidence, but must not re-create
   lane selection logic or launch broad pytest/coverage scans directly. They
   consume persisted artifacts from:
   - `.cognitive-os/reports/test-runs/` (`summary.txt`, `inventory.md`, `junit.xml`)
   - `.cognitive-os/reports/coverage/` (`summary.txt`, `coverage.json`)
   - `.cognitive-os/reports/test-quality/` (`summary.txt`, `quality.json`)
   through `scripts/cos_test_artifact_status.py` when possible.
5. Legacy scripts must declare `ROLE` and `CANONICAL` headers so users and audit
   tests know why they still exist.

## Acceptance criteria for future test tooling

- A new test directory adds a lane or maps to an existing lane.
- A new runner-like script declares its role and canonical entry point.
- A new governance hook consumes existing summaries instead of invoking ad-hoc
  pytest commands unless it documents why.
- Optional/cost-bearing lanes never run in the default broad sweep.

## Validation nervous system

For the full Cognitive OS maintainer doctrine, see [Validation Nervous System](../architecture/validation-nervous-system.md).
