# Workstation/container comparison report

Work ID: worker-g-p5-p6-20260520

Scope: workstation and container only. Kubernetes, local cluster, and fleet
benchmarks remain deferred until a real worker runtime exists.

## Fixture workloads

| Fixture | Type | Path | Success command |
|---|---|---|---|
| `bugfix-python-logic` | Bugfix | `tests/fixtures/benchmark_workloads/bugfix-python-logic` | `python -m pytest tests/test_cart.py -q` |
| `refactor-python-multifile` | Multi-file refactor | `tests/fixtures/benchmark_workloads/refactor-python-multifile` | `python -m pytest tests -q` |

Both fixtures are repository-owned, MIT-compatible, deterministic local Python
workloads with no network or external service dependencies.

## Report generation

Record operator-run rows in JSON and render them with:

```bash
scripts/workstation_container_benchmark_report.py runs.json --output docs/08-References/benchmarks/workstation-container-results-YYYYMMDD.md
```

Expected row fields:

```json
{
  "fixture_id": "bugfix-python-logic",
  "environment": "workstation",
  "mode": "cos",
  "success": true,
  "elapsed_ms": 1000,
  "cost_usd": 0.01,
  "catch_value": "caught failing test",
  "artifact_quality": "pass",
  "notes": "manual run notes"
}
```

## Comparison dimensions

- Vanilla Claude/Codex results when manually available.
- COS-enabled results on the same fixture.
- Workstation versus container elapsed time.
- Overhead in latency and cost.
- Catch value, such as failing-test detection or governance refusal.
- Artifact quality, such as tests passing and minimal diff quality.

## Current status

No live agent/container benchmark run was executed in this slice. The fixture set
and report renderer are ready for operator-recorded workstation/container rows.
