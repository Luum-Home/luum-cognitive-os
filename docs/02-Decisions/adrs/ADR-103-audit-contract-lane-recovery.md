---
adr: 103
title: Audit and contract lane recovery before parallel flip
status: accepted
implementation_status: not-applicable
date: '2026-05-12'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'policy-only: lane sequencing decision; no standalone implementation surface beyond later audit/contract lane work'
---

# ADR-103: Audit and contract lane recovery before parallel flip

## Status

Accepted.

## Context

Audit and contract lanes were held serial after install-touching races were
isolated with `xdist_group("self_install")`. A later smoke showed the remaining
red state was deterministic documentation-contract debt, not an install race:
stale plan paths, stale ADR section formats, stale hook whitelist entries,
missing skill namespace metadata, and stale Codex projection counts.

Keeping the lanes serial after fixing the deterministic failures would hide the
value of ADR-072. Flipping them before fixing deterministic debt would create a
misleading signal where parallelism looked broken because unrelated contracts
were already red.

## Decision

Repair deterministic audit/contract debt first, then make both lanes parallel.
Parallel runner invocations must use xdist load grouping so existing
`xdist_group("self_install")` markers actually serialize install-touching tests
on one worker.

The lane registry remains the source of truth:

- `audit` is `parallel: true` after ADR/plan/catalog/hook-scorecard debt is fixed.
- `contract` is `parallel: true` after stale doc-contract paths and whitelist
  drift are fixed.
- `COS_FORCE_SERIAL_LANES=audit,contract` remains the emergency rollback switch.

## Alternatives rejected

- Leave audit and contract serial — rejected because the deterministic debt is
  now separable from the original install race and serial lanes slow normal
  maintainer feedback.
- Flip lanes without repairing documentation contracts — rejected because it
  would greenwash neither issue and would keep failures misleading.
- Remove or weaken failing contracts — rejected because stale contracts should
  be repointed to canonical artifacts, not deleted.

## Consequences

- Documentation-contract tests now track canonical plan storage under
  `.cognitive-os/plans/architecture/`.
- The pytest wrapper becomes more portable across worktrees without `.venv`.
- Parallel cos-test runs preserve self-install isolation through load groups.
- Report Markdown that must be committed lives under `docs/06-Daily/reports/`; runtime
  `.cognitive-os/reports/` stays transient.

## Verification

Run the focused repair surface:

```bash
python3 -m pytest tests/unit/test_pytest_with_summary.py tests/unit/test_capacity_logging.py tests/contracts/test_headless_runtime_direction_docs.py tests/contracts/test_runtime_comparison_benchmark_plan.py tests/contracts/test_local_connected_systems_validation_docs.py -q
```

Run the lane flip smoke:

```bash
cd cmd/cos-test && go run . cluster --lane audit --dry-run && go run . cluster --lane contract --dry-run
```
