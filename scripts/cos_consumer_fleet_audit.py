#!/usr/bin/env python3
# SCOPE: os-only
"""CLI for the Cognitive OS consumer-fleet audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.consumer_fleet_audit import build_report, dumps_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on warn/fail instead of fail only.")
    args = parser.parse_args()
    report = build_report(args.source_dir, args.registry)
    if args.json:
        print(dumps_json(report))
    else:
        summary = report["summary"]
        print(
            "consumer-fleet-audit: "
            f"{report['status']} projects={summary['matching_source']}/{summary['registered_total']} "
            f"fail={summary['project_failures']} warn={summary['project_warnings']} "
            f"findings={summary['fleet_findings']}"
        )
        for finding in report["findings"]:
            print(f"- [{finding['severity']}] {finding['id']} — {finding['message']}")
        for project in report["projects"]:
            if project["status"] != "pass":
                print(f"- [{project['status']}] {project['project_name']} — {project['path']}")
                for finding in project["findings"]:
                    print(f"  - [{finding['severity']}] {finding['id']} — {finding['message']}")
    if report["status"] == "fail":
        return 1
    if args.strict and report["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
