# Runtime Benchmark MVP

> Status: MVP implemented as a no-cost local schema/leaderboard runner.

The runtime benchmark compares vanilla harnesses and COS profiles using a stable result schema before any expensive external benchmark is adopted.

## Profiles

- `vanilla-codex`
- `vanilla-claude` later
- `cos/lean`
- `cos/standard`
- `cos/full` later

## Runtime surface

- Schema/helpers: `lib/runtime_benchmark.py`
- Tasks: `.cognitive-os/tests/runtime-comparison/tasks.yaml`
- Runner: `scripts/run-runtime-benchmark.sh`
- Report: `scripts/runtime-benchmark-report.py`
- Tests: `tests/contracts/test_runtime_benchmark_schema.py`

The default runner emits dry-run rows and performs no model calls. Real execution must be explicit.
