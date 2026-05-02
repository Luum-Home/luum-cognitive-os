#!/usr/bin/env python3
# SCOPE: os-only
"""Generate a runtime benchmark leaderboard from JSONL results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.runtime_benchmark import format_leaderboard, load_results


DEFAULT_RESULTS = PROJECT_ROOT / ".cognitive-os" / "metrics" / "runtime-benchmark-results.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / ".cognitive-os" / "reports" / "runtime-benchmark-leaderboard.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--output", default=str(DEFAULT_REPORT))
    args = parser.parse_args()
    report = format_leaderboard(load_results(args.results))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
