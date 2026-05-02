#!/usr/bin/env bash
# SCOPE: os-only
# Dry-run adversarial generalization suite with deterministic expected observations.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIOS="$ROOT/.cognitive-os/tests/adversarial-generalization/scenarios.yaml"
REPORT="$ROOT/.cognitive-os/reports/adversarial-generalization-report.md"
mkdir -p "$(dirname "$REPORT")"
python3 - "$SCENARIOS" "$REPORT" <<'PY'
import sys
from lib.adversarial_rubric import evaluate_scenario, format_report, load_scenarios

scenarios = load_scenarios(sys.argv[1])
results = []
for scenario in scenarios:
    expected = scenario.get("expected_behavior", "")
    # Dry-run oracle: observed behavior states the expected policy markers.
    results.append(evaluate_scenario(scenario, f"DRY_RUN observed policy: {expected}"))
report = format_report(results)
open(sys.argv[2], "w", encoding="utf-8").write(report)
print(sys.argv[2])
PY
