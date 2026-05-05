#!/usr/bin/env python3
# SCOPE: os-only
"""Report current hook/operator friction from COS metrics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.friction_telemetry import load_jsonl, summarize


def render_text(report: dict) -> str:
    lines = ["COS Friction Report", "===================", ""]
    lines.append(f"events: {report['total_events']}")
    lines.append("outcomes: " + ", ".join(f"{key}={value}" for key, value in report["outcome_counts"].items()))
    for title, key in (
        ("Top blockers", "top_blocking_hooks"),
        ("Top warnings", "top_warning_hooks"),
        ("Top latency p95", "top_latency_hooks"),
        ("Bypass usage", "top_bypass_hooks"),
        ("False-positive candidates", "false_positive_candidates"),
    ):
        lines.extend(["", title + ":"])
        rows = report.get(key) or []
        if not rows:
            lines.append("  - none")
            continue
        for row in rows:
            if key == "top_latency_hooks":
                lines.append(f"  - {row['hook']}: p95={row['p95_latency_ms']}ms samples={row['samples']}")
            elif key == "false_positive_candidates":
                lines.append(f"  - {row['hook']}: {row['outcome']} x{row['count']} reason={row['reason']}")
            else:
                lines.append(f"  - {row['hook']}: {row['count']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", default=".cognitive-os/metrics/hook-timing.jsonl")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--false-positive-threshold", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = summarize(load_jsonl(Path(args.metrics)), limit=args.limit, false_positive_threshold=args.false_positive_threshold)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
