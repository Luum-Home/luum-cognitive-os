#!/usr/bin/env bash
# SCOPE: os-only
# Lightweight runtime comparison benchmark runner. Default is dry-run/no model calls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS="$ROOT/.cognitive-os/metrics/runtime-benchmark-results.jsonl"
TASKS="$ROOT/.cognitive-os/tests/runtime-comparison/tasks.yaml"
DRY_RUN=1
if [ "${1:-}" = "--execute" ]; then
  DRY_RUN=0
fi
mkdir -p "$(dirname "$RESULTS")"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$ROOT" "$RESULTS" "$TASKS" "$DRY_RUN" <<'PY'
import sys
from pathlib import Path

from lib.adversarial_rubric import load_scenarios
from lib.runtime_benchmark import RuntimeBenchmarkResult, append_result, run_local_smoke

root = Path(sys.argv[1])
results_path = sys.argv[2]
tasks_path = Path(sys.argv[3])
dry_run = sys.argv[4] == "1"

def load_tasks(path: Path) -> list[dict]:
    import yaml
    return list((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("tasks", []))

systems = [("vanilla-codex", "baseline"), ("cos", "lean"), ("cos", "standard")]
tasks = load_tasks(tasks_path)
for system, profile in systems:
    for task in tasks:
        task_id = str(task["id"])
        if dry_run:
            passed = False
            duration = 0.0
            security_events = 0
            result = "inconclusive"
            notes = "dry-run only; no model calls and no local checks executed"
        else:
            passed, duration, notes, security_events = run_local_smoke(task_id, root)
            result = "pass" if passed else "fail"
        append_result(
            results_path,
            RuntimeBenchmarkResult(
                benchmark_id="agentic-mastery-local",
                system=system,
                profile=profile,
                task_id=task_id,
                result=result,
                duration_seconds=duration,
                tests_passed=passed,
                cost_usd=0.0,
                tool_calls=1 if not dry_run else 0,
                files_touched=0,
                security_events=security_events,
                notes=notes,
            ),
        )
PY
python3 "$ROOT/scripts/runtime-benchmark-report.py" --results "$RESULTS"
