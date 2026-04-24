#!/usr/bin/env python3
# SCOPE: both
"""CLI wrapper for lib.cost_predictor.

Turns the existing cost prediction engine into a real user-facing tool so
`/cost-predict` is backed by executable behavior, not just documentation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.cost_predictor import CostPredictor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predict task cost from Cognitive OS history and model routing."
    )
    parser.add_argument("task_description", help="Task to estimate.")
    parser.add_argument(
        "--type",
        dest="task_type",
        default="feature",
        choices=("feature", "bugfix", "refactor", "docs", "research"),
        help="Dominant task type for the estimate.",
    )
    parser.add_argument(
        "--history-path",
        default=".cognitive-os/metrics/task-history.jsonl",
        help="Path to task history JSONL.",
    )
    parser.add_argument(
        "--cost-events-path",
        default=".cognitive-os/metrics/cost-events.jsonl",
        help="Path to cost events JSONL.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of formatted text.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    predictor = CostPredictor(
        history_path=args.history_path,
        cost_events_path=args.cost_events_path,
    )
    prediction = predictor.predict(args.task_description, task_type=args.task_type)

    if args.json:
        payload = asdict(prediction)
        payload["task_description"] = args.task_description
        payload["task_type"] = args.task_type
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print("Cost Prediction")
    print(f"Task: {args.task_description}")
    print(f"Task type: {args.task_type}")
    print(predictor.format_prediction(prediction))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
