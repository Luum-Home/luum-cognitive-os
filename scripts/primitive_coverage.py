#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from primitive_coverage import scan_repository
from primitive_coverage.reports.json_report import render_json
from primitive_coverage.reports.markdown import render_markdown
from primitive_coverage.reports.sarif import render_sarif


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan primitive coverage for a repository")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--adapter", default="generic")
    parser.add_argument("--format", choices=("json", "markdown", "sarif"), default="json")
    parser.add_argument("--out", default="")
    parser.add_argument("--fail-under", type=float, default=None, help="Exit 1 when average score is below this value")
    parser.add_argument("--no-cos-audits", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = scan_repository(args.project_dir, adapter=args.adapter, include_cos_audits=not args.no_cos_audits)
    if args.format == "json":
        rendered = render_json(report)
    elif args.format == "markdown":
        rendered = render_markdown(report)
    else:
        rendered = render_sarif(report)
    if args.out:
        out = Path(args.project_dir) / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.fail_under is not None and report.summary()["average_score"] < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
