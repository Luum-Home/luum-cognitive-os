# Runtime Benchmark MVP

> Status: local real-check MVP. Default is no model calls; explicit execution runs deterministic local smokes.

The runtime benchmark compares vanilla harnesses and COS profiles using a stable result schema before any expensive external benchmark is adopted. It does **not** call models by default.

## Execution modes

- `scripts/run-runtime-benchmark.sh`: writes `inconclusive` dry-run rows only; no model calls and no local checks.
- `scripts/run-runtime-benchmark.sh --execute`: runs no-cost local checks and writes `pass`/`fail` rows.

The `--execute` lane currently exercises:

1. `lethal-trifecta-smoke` — invokes `hooks/lethal-trifecta-gate.sh` with a private-data + untrusted-content + external-action payload and expects a block.
2. `aci-empty-output-smoke` — runs `true`, normalizes the empty successful output through `lib.aci_observation`, and expects explicit no-output success.
3. `skill-efficacy-smoke` — computes a paired skill-enabled/no-skill local summary and expects a paired success delta.

## Runtime surface

- Schema/helpers/local checks: `lib/runtime_benchmark.py`
- Tasks: `.cognitive-os/tests/runtime-comparison/tasks.yaml`
- Runner: `scripts/run-runtime-benchmark.sh`
- Report: `scripts/runtime_benchmark_report.py`
- Tests: `tests/contracts/test_runtime_benchmark_schema.py`

Generated metrics are appended to `.cognitive-os/metrics/runtime-benchmark-results.jsonl`; the leaderboard is written to `.cognitive-os/reports/runtime-benchmark-leaderboard.md`.
