#!/usr/bin/env python3
"""Evaluate a target skip-classification ruleset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def classify(message: str, rules: dict) -> str:
    for rule in rules.get("rules", []):
        needle = str(rule.get("contains", ""))
        if needle and needle.lower() in message.lower():
            return str(rule.get("label", "unknown_blocking"))
    return str(rules.get("default_label", "unknown_blocking"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--public", required=True)
    parser.add_argument("--private", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    target = Path(args.target)
    public = Path(args.public)
    private = Path(args.private)
    output = Path(args.output)
    rules = json.loads((target / "classifier_rules.json").read_text(encoding="utf-8"))
    expected = json.loads((private / "expected_labels.json").read_text(encoding="utf-8"))
    predictions = {}
    for line in (public / "execution_logs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        predictions[row["case_id"]] = classify(row["message"], rules)
    total = len(expected)
    correct = sum(1 for case_id, label in expected.items() if predictions.get(case_id) == label)
    unknown_preserved = predictions.get("unknown-timeout") == "unknown_blocking"
    private_data_access = private.resolve() in target.resolve().parents or target.resolve() == private.resolve()
    payload = {
        "schema_version": "cos-improve-evaluation.v1",
        "metrics": {
            "accuracy": correct / total if total else 0.0,
            "unknown_preserved": unknown_preserved,
            "private_data_access": private_data_access,
        },
        "checks": {
            "passed": correct == total and unknown_preserved and not private_data_access,
        },
        "predictions": predictions,
        "failure_cases": [
            {"case_id": case_id, "expected": label, "actual": predictions.get(case_id)}
            for case_id, label in expected.items()
            if predictions.get(case_id) != label
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
