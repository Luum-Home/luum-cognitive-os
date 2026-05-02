#!/usr/bin/env bash
# SCOPE: os-only
# @manual-trigger: run to execute local adversarial generalization fixture suite; no model calls required
# Local adversarial generalization suite. Generates fixtures and evaluates local checks; no model calls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIOS="$ROOT/.cognitive-os/tests/adversarial-generalization/scenarios.yaml"
GENERATED="$ROOT/.cognitive-os/generated/adversarial-scenarios"
REPORT="$ROOT/.cognitive-os/reports/adversarial-generalization-report.md"
mkdir -p "$(dirname "$REPORT")" "$GENERATED"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$SCENARIOS" "$GENERATED" "$REPORT" <<'PY'
import sys
from lib.adversarial_rubric import evaluate_fixture, format_report, generate_fixture, load_scenarios

scenarios = load_scenarios(sys.argv[1])
output_dir = sys.argv[2]
results = []
for scenario in scenarios:
    fixture_path = generate_fixture(scenario, output_dir)
    results.append(evaluate_fixture(scenario, fixture_path))
report = format_report(results)
open(sys.argv[3], "w", encoding="utf-8").write(report)
failed = [r.scenario_id for r in results if not r.passed]
print(sys.argv[3])
print(f"generated={output_dir}")
if failed:
    print("failed=" + ",".join(failed))
    raise SystemExit(1)
PY
