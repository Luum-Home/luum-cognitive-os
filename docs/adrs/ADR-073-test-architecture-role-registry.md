---
adr: 73
title: Test Architecture Role Registry
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-073: Test Architecture Role Registry

## Status

**Accepted** — 2026-04-30.

## Context

ADR-072 made `cos-test focused / cluster / broad` the canonical execution ladder,
but the wider test architecture still had overlapping primitives:

- `scripts/cos-smoke.sh`, `scripts/test-cognitive-os.sh`,
  `scripts/test-cognitive-os-full.sh`, `scripts/test-all.sh`, and
  `scripts/run-all-tests.sh` all looked like generic test runners.
- Selection, execution, reporting, governance, and lifecycle concerns were mixed
  across bash scripts, Go commands, hooks, skills, reports, and metrics.
- Governance primitives such as `auto-verify`, `dod-gate`, coverage checks, and
  test-quality audits had no explicit contract saying they must consume the
  canonical lane/reporting artifacts instead of inventing their own test policy.
- Resource governance for test execution is still a gap: optional/cost-bearing
  lanes exist, but CPU/Docker/model-cost budgets are not yet governed as a
  first-class test-run resource policy.

## Decision

Adopt a role registry for test-related primitives. Every primitive gets exactly
one primary role:

| Role | Owner | Boundary |
|---|---|---|
| Selection | `.cognitive-os/test-lanes.yaml`, `tests/conftest.py`, `cmd/cos-test` selectors | Decides what tests should run. |
| Execution | `cmd/cos-test` and explicit legacy/on-demand runners | Starts test processes. |
| Reporting | `scripts/pytest-with-summary.sh`, inventory scripts, report stores, metrics | Persists and summarizes evidence. |
| Governance | hooks/skills/scripts that enforce DoD, coverage, ratchets, and test quality | Consumes evidence and blocks weak changes. |
| Lifecycle | baselines, historical reports, plans, and ratchet state | Tracks quality state over time. |

The inventory lives at
`.cognitive-os/migrations/test-architecture-inventory.md` and is the migration
ledger for this cleanup.

## Canonical map

| Concern | Canonical primitive | Notes |
|---|---|---|
| Default test UX | `cos-test focused / cluster / broad` | Contributors learn one ladder. |
| Lane policy | `.cognitive-os/test-lanes.yaml` | Single source of truth for paths, optional lanes, and parallel safety. |
| Marker application | `tests/conftest.py` + `pytest.ini` | Runtime marker selection must mirror the registry. |
| Persistent artifacts | `scripts/pytest-with-summary.sh` | Transport/reporting layer; no lane policy ownership. |
| Startup smoke | `scripts/cos-smoke.sh` | Explicit opt-in only. |
| Legacy shell runners | `scripts/test-cognitive-os*.sh`, `scripts/test-all.sh` | Deprecated compatibility shims. |
| Release hardening | `scripts/run-all-tests.sh` | Release/integrity sweep only, not daily iteration. |
| Quality governance | `auto-verify`, `global-verify`, `dod-gate`, coverage and quality audit primitives | Consume canonical evidence; do not duplicate selection policy. |
| Test lifecycle | metrics JSONL, baselines, repair ledgers | Historical evidence and ratchets. |


## Gap audit from read-only agents

The inventory phase identified these follow-up gaps. They are intentionally
tracked here instead of hidden in chat notes:

| Priority | Gap | Current evidence | Follow-up |
|---|---|---|---|
| P0 | Worker/resource policy is advertised but not fully canonical. | Resolved after acceptance: `focused`, `cluster`, and `broad` now pass explicit `--workers` / `--lane` scalars to `pytest-with-summary.sh`; `COS_FORCE_SERIAL_LANES` is implemented for focused and lane-based runs. | Keep `pytest-with-summary.sh` as reporting transport and test worker scalar forms. |
| P0 | Governance can duplicate focused selection and reporting. | Partially resolved after acceptance: `global-verify.sh` still owns before/after comparison and resolver input, but test execution/reporting now delegates to `pytest-with-summary.sh` and parses persisted JUnit when available. | Continue reducing selector duplication by exposing a cos-test focused plan API in a later slice. |
| P1 | `cmd/cos-test` still has two runner architectures. | Resolved after acceptance: `run` and `dashboard` are deprecated compatibility shims over canonical broad/cluster, and `watch` reruns the focused plan instead of using old `runner.RunConfig` execution. | Keep audit coverage that deprecated surfaces do not call the legacy pytest runner. |
| P1 | Legacy shell runners are still executable alternatives. | `test-all.sh`, `test-cognitive-os*.sh`, and `cos-smoke.sh` run independent selection/execution. | Keep only explicit niches; redirect or hard-deprecate redundant scripts after the current release cycle. |
| P1 | Empty shell pyramid can falsely pass. | `test-cognitive-os.sh` loops legacy `tests/infra/test-*.sh`; if none exist it can report zero failures. | Remove from active runner surface or make zero discovered tests a deprecated/non-success status. |
| P2 | Reporting ownership is split. | Go JSON report parser, shell summary parsing, global-verify parsing, and wrapper artifacts all coexist. | Promote wrapper inventory/JUnit/summary artifacts as the single report schema. |
| P2 | Governance gates can drift into scanners/runners. | Resolved for the core gates: `auto-verify`, `dod-gate`, and `pre-commit-gate` now consume persisted test/coverage artifacts via `scripts/cos_test_artifact_status.py`; `cos_test_quality_audit.py` writes report artifacts for quality consumers. | Future gates must read `.cognitive-os/reports/**` first and justify any direct scanner/executor fallback. |

## Deprecation policy

1. Add `ROLE` and `CANONICAL` headers to legacy scripts.
2. During the current release cycle, keep legacy scripts executable but clearly
   non-canonical.
3. In the next release cycle, redirect/proxy deprecated scripts to canonical
   commands where safe.
4. After one release cycle with no external consumers, remove redundant scripts
   or keep them only if they serve a documented release-only purpose.

## Resource governance follow-up

Resource governance is intentionally not solved in this ADR. It is tracked as a
separate sprint in `.cognitive-os/plans/architecture/test-resource-governance-sprint.md`
with these deliverables:

- time/CPU/Docker budgets for `cos-test broad` and optional lanes, starting with `.cognitive-os/test-resource-policy.yaml`;
- explicit cost gates for LLM-evaluated quality tests;
- a Docker/testcontainers concurrency policy;
- report fields that distinguish functional failure from resource exhaustion;
- CI defaults that avoid surprise cost-bearing lanes.

## Consequences

### Positive

- New contributors get a single test ladder and a clear explanation of legacy
  scripts.
- Governance primitives are prevented from becoming hidden test runners.
- Reporting artifacts remain consistent across focused, cluster, and broad runs.

### Negative

- Existing scripts remain temporarily, so the cleanup requires one more release
  cycle.
- The role registry adds an audit burden: new test primitives must declare their
  role and canonical owner.

## Validation

- `tests/audit/test_test_runner_role_taxonomy.py` enforces role headers and the
  operator-facing taxonomy.
- `tests/audit/test_test_architecture_inventory.py` enforces that this inventory
  has 30+ uniquely classified primitives across all five roles.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep all test scripts as peer entry points | This preserves the exact ambiguity the role registry is intended to remove; new contributors still cannot know which “smoke” or “all tests” command is authoritative. |
| Move all test policy into `pytest-with-summary.sh` | The wrapper is a reporting transport. Putting lane policy in bash would duplicate the Go/Python lane registry and violate ADR-066’s polyglot boundary. |
| Delete legacy scripts immediately | Some users or CI jobs may still call them. A one-release deprecation window preserves compatibility while making the canonical path explicit. |
| Solve test resource governance in this ADR | Resource budgets require separate runtime behavior changes and empirical measurements; combining that with role cleanup would make the migration harder to validate. |

## Verification

```bash
python3 -m pytest \
  tests/audit/test_test_architecture_inventory.py \
  tests/audit/test_test_runner_role_taxonomy.py \
  tests/audit/test_doc_paths_tracked.py \
  tests/audit/test_adr_contracts.py \
  tests/audit/test_rules_enforcement.py::test_no_rule_references_missing_file \
  tests/audit/test_skill_descriptions_nonempty.py \
  -q --tb=short

bash -n \
  scripts/pytest-with-summary.sh \
  scripts/cos-smoke.sh \
  scripts/test-cognitive-os.sh \
  scripts/test-cognitive-os-full.sh \
  scripts/test-all.sh \
  scripts/run-all-tests.sh

python3 scripts/check_test_quality.py \
  tests/audit/test_test_architecture_inventory.py \
  tests/audit/test_test_runner_role_taxonomy.py
```
