#!/usr/bin/env python3
# SCOPE: os-only
# @manual-trigger: invoke to generate adversarial scenario fixtures for testing; not an automated hook
"""Generate a disposable adversarial scenario fixture."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.adversarial_rubric import generate_fixture, load_scenarios


DEFAULT_SCENARIOS = PROJECT_ROOT / ".cognitive-os" / "tests" / "adversarial-generalization" / "scenarios.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / ".cognitive-os" / "generated" / "adversarial-scenarios"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id")
    parser.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    scenarios = {s["id"]: s for s in load_scenarios(args.scenarios)}
    if args.scenario_id not in scenarios:
        known = ", ".join(sorted(scenarios))
        raise SystemExit(f"unknown scenario_id {args.scenario_id!r}; known: {known}")
    print(str(generate_fixture(scenarios[args.scenario_id], args.output_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
