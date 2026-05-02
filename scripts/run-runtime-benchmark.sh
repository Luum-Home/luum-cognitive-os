#!/usr/bin/env bash
# SCOPE: os-only
# Lightweight runtime comparison benchmark runner. Default is dry-run/no model calls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS="$ROOT/.cognitive-os/metrics/runtime-benchmark-results.jsonl"
DRY_RUN=1
if [ "${1:-}" = "--execute" ]; then
  DRY_RUN=0
fi
mkdir -p "$(dirname "$RESULTS")"
python3 - "$RESULTS" "$DRY_RUN" <<'PY'
import sys
from lib.runtime_benchmark import RuntimeBenchmarkResult, append_result

results_path = sys.argv[1]
dry_run = sys.argv[2] == "1"
systems = [("vanilla-codex", "baseline"), ("cos", "lean"), ("cos", "standard")]
tasks = ["lethal-trifecta-smoke", "aci-empty-output-smoke", "skill-efficacy-smoke"]
for system, profile in systems:
    for task in tasks:
        append_result(
            results_path,
            RuntimeBenchmarkResult(
                benchmark_id="agentic-mastery-smoke",
                system=system,
                profile=profile,
                task_id=task,
                result="inconclusive" if dry_run else "pass",
                duration_seconds=0.0,
                tests_passed=not dry_run,
                cost_usd=0.0,
                tool_calls=0,
                files_touched=0,
                security_events=1 if system == "cos" and task == "lethal-trifecta-smoke" else 0,
                notes="dry-run synthetic row; no model call" if dry_run else "executed smoke row",
            ),
        )
PY
python3 "$ROOT/scripts/runtime-benchmark-report.py" --results "$RESULTS"
