#!/usr/bin/env python3
# SCOPE: os-only
"""Report ADR-186 context-budget calibration from .cognitive-os metrics."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.context_budget_monitor import build_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.project_dir, window_days=args.window_days)
    data = report.to_dict()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"Context budget calibration: {report.status.upper()} ({report.total_entries} entries / {report.window_days}d)")
        print(f"PASS={report.pass_rate:.1%} WARN={report.warn_rate:.1%} BLOCK={report.block_rate:.1%} OVERRIDE={report.override_rate:.1%}")
        if report.meter_p99_ms is not None:
            print(f"meter p99={report.meter_p99_ms:.1f}ms")
        if report.findings:
            print("Findings:")
            for finding in report.findings:
                print(f"- {finding}")
        print(f"Recommendation: {report.recommendation}")
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
