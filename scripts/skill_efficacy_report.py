#!/usr/bin/env python3
# SCOPE: os-only
"""Generate a Skill Efficacy markdown report from the skill archive."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.skill_efficacy import format_markdown, load_runs_from_archive, summarize_runs


DEFAULT_ARCHIVE = PROJECT_ROOT / ".cognitive-os" / "metrics" / "skill-archive.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / ".cognitive-os" / "reports" / "skill-efficacy-report.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--output", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    summaries = summarize_runs(load_runs_from_archive(args.archive))
    report = format_markdown(summaries)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
