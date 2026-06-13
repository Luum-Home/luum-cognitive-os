#!/usr/bin/env python3
# SCOPE: os-only
"""Aggregate persisted pytest JUnit timings into a slow-test report."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / ".cognitive-os" / "reports" / "test-runs"
DEFAULT_OUT_DIR = PROJECT_ROOT / ".cognitive-os" / "reports" / "slow-tests"

sys.path.insert(0, str(PROJECT_ROOT))
from scripts.test_run_inventory import TestItem, parse_junit  # noqa: E402


@dataclass
class SlowTestAggregate:
    nodeid: str
    file: str
    test: str
    observations: int = 0
    total_seconds: float = 0.0
    max_seconds: float = 0.0
    avg_seconds: float = 0.0
    latest_seconds: float = 0.0
    latest_run: str = ""
    outcomes: dict[str, int] = field(default_factory=dict)
    recommended_lane: str = "release-blocking-fast"


def _run_id_for_junit(junit_path: Path, reports_root: Path) -> str:
    try:
        return str(junit_path.parent.relative_to(reports_root))
    except ValueError:
        return junit_path.parent.name


def _recommend_lane(item: SlowTestAggregate, slow_threshold: float) -> str:
    haystack = f"{item.file} {item.nodeid}".lower()
    if any(part in haystack for part in ["tests/integration", "tests/e2e", "tests/chaos"]):
        return "integration-explicit"
    if any(part in haystack for part in ["benchmark", "arena", "quality"]):
        return "optional-explicit"
    if item.max_seconds >= slow_threshold:
        return "slow-nightly-review"
    return "release-blocking-fast"


def discover_junit_files(reports_root: Path) -> list[Path]:
    if not reports_root.exists():
        return []
    return sorted(
        path
        for path in reports_root.rglob("junit.xml")
        if path.is_file() and "slow-tests" not in path.parts
    )


def aggregate_items(items_by_run: list[tuple[str, list[TestItem]]], slow_threshold: float) -> list[SlowTestAggregate]:
    aggregates: dict[str, SlowTestAggregate] = {}
    for run_id, items in items_by_run:
        for item in items:
            aggregate = aggregates.setdefault(
                item.nodeid,
                SlowTestAggregate(nodeid=item.nodeid, file=item.file, test=item.test),
            )
            aggregate.observations += 1
            aggregate.total_seconds += item.duration_seconds
            aggregate.max_seconds = max(aggregate.max_seconds, item.duration_seconds)
            aggregate.latest_seconds = item.duration_seconds
            aggregate.latest_run = run_id
            aggregate.outcomes[item.outcome] = aggregate.outcomes.get(item.outcome, 0) + 1
    for aggregate in aggregates.values():
        aggregate.avg_seconds = aggregate.total_seconds / aggregate.observations if aggregate.observations else 0.0
        aggregate.recommended_lane = _recommend_lane(aggregate, slow_threshold)
    return sorted(aggregates.values(), key=lambda item: (item.max_seconds, item.total_seconds), reverse=True)


def build_report(reports_root: Path, top: int, slow_threshold: float) -> dict[str, object]:
    junit_files = discover_junit_files(reports_root)
    items_by_run: list[tuple[str, list[TestItem]]] = []
    parse_errors: list[dict[str, str]] = []
    for junit_path in junit_files:
        try:
            items_by_run.append((_run_id_for_junit(junit_path, reports_root), parse_junit(junit_path)))
        except Exception as exc:  # defensive reporting tool; keep one bad XML from hiding all timing evidence
            parse_errors.append({"path": str(junit_path), "error": str(exc)})
    aggregates = aggregate_items(items_by_run, slow_threshold)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reports_root": str(reports_root),
        "junit_files": len(junit_files),
        "parse_errors": parse_errors,
        "observations": sum(item.observations for item in aggregates),
        "unique_tests": len(aggregates),
        "slow_threshold_seconds": slow_threshold,
        "top": [asdict(item) for item in aggregates[:top]],
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    top = report.get("top", [])
    lines = [
        "# Slow Test Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"JUnit files scanned: `{report['junit_files']}`",
        f"Test observations: `{report['observations']}`",
        f"Unique tests: `{report['unique_tests']}`",
        f"Slow threshold: `{report['slow_threshold_seconds']}s`",
        "",
        "| Rank | Max s | Avg s | Obs | Recommended lane | Test | Latest run |",
        "|---:|---:|---:|---:|---|---|---|",
    ]
    for index, item in enumerate(top if isinstance(top, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        nodeid = str(item.get("nodeid", "")).replace("|", "\\|")
        latest_run = str(item.get("latest_run", "")).replace("|", "\\|")
        lines.append(
            f"| {index} | {float(item.get('max_seconds', 0.0)):.3f} | "
            f"{float(item.get('avg_seconds', 0.0)):.3f} | {int(item.get('observations', 0))} | "
            f"{item.get('recommended_lane', '')} | `{nodeid}` | `{latest_run}` |"
        )
    parse_errors = report.get("parse_errors", [])
    if parse_errors:
        lines.extend(["", "## Parse errors", ""])
        for error in parse_errors if isinstance(parse_errors, list) else []:
            if isinstance(error, dict):
                lines.append(f"- `{error.get('path')}`: {error.get('error')}")
    path.write_text("\n".join(lines) + "\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", type=Path, default=DEFAULT_REPORTS_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--slow-threshold", type=float, default=10.0)
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    reports_root = args.reports_root.resolve()
    out_dir = args.out_dir.resolve()
    json_out = (args.json_out or out_dir / "latest.json").resolve()
    md_out = (args.md_out or out_dir / "latest.md").resolve()

    report = build_report(reports_root, top=args.top, slow_threshold=args.slow_threshold)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, md_out)

    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"[cos-test-slow-report] wrote {json_out}")
        print(f"[cos-test-slow-report] wrote {md_out}")
        print(f"[cos-test-slow-report] unique_tests={report['unique_tests']} observations={report['observations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
