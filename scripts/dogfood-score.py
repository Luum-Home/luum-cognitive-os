#!/usr/bin/env python3
# SCOPE: os-only
"""CLI for the dogfood-maturity meter.

Modes:
  default   pretty-printed breakdown
  --json    machine-readable JSON (stdout)
  --trend   append to .cognitive-os/metrics/dogfood-score.jsonl + show delta

Exit code is 0 on success regardless of the score. Use --fail-below N to make
the command exit 1 if the overall score drops below N.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python3 scripts/dogfood-score.py` from repo root without install.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.dogfood_scorer import (  # noqa: E402
    DIMENSION_WEIGHTS,
    DogfoodScorer,
    append_trend_record,
    read_last_trend_record,
)


DEFAULT_TREND_PATH = REPO_ROOT / ".cognitive-os/metrics/dogfood-score.jsonl"


def _fmt_cell(v, width):
    if v is None:
        s = "null"
    elif isinstance(v, float):
        s = f"{v:.2f}"
    else:
        s = str(v)
    return s.ljust(width)


def render_pretty(score, last_record=None, trend_path=None):
    lines = []
    lines.append("=" * 72)
    lines.append("Dogfood Maturity Score")
    lines.append("=" * 72)
    overall_str = "null" if score.overall is None else f"{score.overall:.2f}/100"
    flag = " (partial)" if score.partial else ""
    lines.append(f"Overall: {overall_str}{flag}")
    if last_record is not None and last_record.get("overall") is not None and score.overall is not None:
        delta = score.overall - last_record["overall"]
        sign = "+" if delta >= 0 else ""
        lines.append(f"Delta vs last: {sign}{delta:.2f} (prev {last_record['overall']:.2f})")
    lines.append(f"Timestamp: {score.timestamp}")
    lines.append("")
    lines.append(f"{'Dimension':<24} {'Score':>8} {'Weight':>8}  Evidence")
    lines.append("-" * 72)
    for dim, weight in DIMENSION_WEIGHTS.items():
        v = score.dimensions.get(dim)
        ev = score.evidence.get(dim, "")
        lines.append(
            f"{dim:<24} {_fmt_cell(v, 8)} {_fmt_cell(weight, 8)}  {ev}"
        )
    if score.missing_signals:
        lines.append("")
        lines.append("Missing signals (excluded from weighted sum):")
        for m in score.missing_signals:
            lines.append(f"  - {m}")
    if trend_path is not None:
        lines.append("")
        lines.append(f"Trend file: {trend_path}")
    lines.append("=" * 72)
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--trend", action="store_true",
                   help="append to trend JSONL and show delta vs previous run")
    p.add_argument("--trend-path", default=str(DEFAULT_TREND_PATH),
                   help=f"trend JSONL path (default: {DEFAULT_TREND_PATH})")
    p.add_argument("--repo", default=str(REPO_ROOT),
                   help="repo root (default: auto-detected)")
    p.add_argument("--fail-below", type=float, default=None,
                   help="exit 1 if overall score is below this value")
    args = p.parse_args(argv)

    scorer = DogfoodScorer(Path(args.repo))
    score = scorer.compute_score()

    trend_path = Path(args.trend_path)
    last = None
    if args.trend:
        last = read_last_trend_record(trend_path)
        append_trend_record(score, trend_path)

    if args.json:
        out = score.to_dict()
        if last is not None and last.get("overall") is not None and score.overall is not None:
            out["delta_vs_last"] = round(score.overall - last["overall"], 2)
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print(render_pretty(score, last_record=last, trend_path=trend_path if args.trend else None))

    if args.fail_below is not None and score.overall is not None and score.overall < args.fail_below:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
