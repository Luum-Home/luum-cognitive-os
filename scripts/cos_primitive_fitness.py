#!/usr/bin/env python3
# SCOPE: os-only
"""Compare candidate primitive fitness against a baseline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.primitive_fitness import build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primitive", required=True, help="Primitive id being evaluated")
    parser.add_argument("--baseline-metrics", required=True, help="Baseline metrics directory")
    parser.add_argument("--candidate-metrics", required=True, help="Candidate metrics directory")
    parser.add_argument("--baseline-repo", help="Baseline repo root for dogfood scoring")
    parser.add_argument("--candidate-repo", help="Candidate repo root for dogfood scoring")
    parser.add_argument("--baseline-dogfood-json", help="Precomputed baseline dogfood score JSON")
    parser.add_argument("--candidate-dogfood-json", help="Precomputed candidate dogfood score JSON")
    parser.add_argument("--baseline-consumer-proposals", help="Baseline consumer improvement proposal bundle JSON")
    parser.add_argument("--candidate-consumer-proposals", help="Candidate consumer improvement proposal bundle JSON")
    parser.add_argument("--baseline-dependency-report", help="Baseline cos-deps-install JSON report")
    parser.add_argument("--candidate-dependency-report", help="Candidate cos-deps-install JSON report")
    parser.add_argument("--required-delta", type=float, default=1.0)
    parser.add_argument("--min-sample-count", type=int, default=1)
    parser.add_argument("--evidence-command", action="append", default=[])
    parser.add_argument("--output", help="Optional path to write the primitive fitness report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(
        primitive_id=args.primitive,
        baseline_metrics=args.baseline_metrics,
        candidate_metrics=args.candidate_metrics,
        baseline_repo=args.baseline_repo,
        candidate_repo=args.candidate_repo,
        baseline_dogfood_json=args.baseline_dogfood_json,
        candidate_dogfood_json=args.candidate_dogfood_json,
        baseline_consumer_proposals_json=args.baseline_consumer_proposals,
        candidate_consumer_proposals_json=args.candidate_consumer_proposals,
        baseline_dependency_report_json=args.baseline_dependency_report,
        candidate_dependency_report_json=args.candidate_dependency_report,
        required_delta=args.required_delta,
        min_sample_count=args.min_sample_count,
        evidence_commands=args.evidence_command,
    )
    payload = report.to_dict()
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        delta = "n/a" if report.delta is None else f"{report.delta:+.2f}"
        print(f"primitive fitness: {report.verdict} delta={delta} required={report.required_delta}")
        for item in report.safety_regressions:
            print(f"- safety regression: {item}")
        if report.missing_signals:
            print("- missing signals: " + ", ".join(report.missing_signals))
    return 0 if report.verdict == "promote" else 1


if __name__ == "__main__":
    raise SystemExit(main())
