#!/usr/bin/env python3
# SCOPE: os-only
"""Generate a disposable adversarial scenario fixture."""

from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.adversarial_rubric import load_scenarios


DEFAULT_SCENARIOS = PROJECT_ROOT / ".cognitive-os" / "tests" / "adversarial-generalization" / "scenarios.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / ".cognitive-os" / "generated" / "adversarial-scenarios"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id")
    parser.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    scenarios = {s["id"]: s for s in load_scenarios(args.scenarios)}
    scenario = scenarios[args.scenario_id]
    out = Path(args.output_dir) / args.scenario_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "SCENARIO.json").write_text(json.dumps(scenario, indent=2, sort_keys=True), encoding="utf-8")
    (out / "README.md").write_text(f"# {scenario['id']}\n\n{scenario['prompt']}\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
