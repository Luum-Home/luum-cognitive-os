#!/usr/bin/env python3
# SCOPE: os-only
"""Read persisted cos-test/pytest-with-summary artifacts.

Governance hooks use this helper to consume existing test evidence instead of
starting new test runs or reimplementing pytest parsing.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SUMMARY_PATTERNS = {
    "passed": re.compile(r"(\d+)\s+passed"),
    "failed": re.compile(r"(\d+)\s+failed"),
    "errors": re.compile(r"(\d+)\s+errors?"),
    "skipped": re.compile(r"(\d+)\s+skipped"),
    "xfailed": re.compile(r"(\d+)\s+xfailed"),
    "xpassed": re.compile(r"(\d+)\s+xpassed"),
}

COVERAGE_PATTERN = re.compile(r"Composite:\s*(\d+)%\s*\((\d+)/(\d+)\)", re.IGNORECASE)


def _latest_run(reports_root: Path) -> Path | None:
    latest = reports_root / "latest"
    if latest.exists():
        try:
            resolved = latest.resolve()
            if resolved.is_dir():
                return resolved
        except OSError:
            pass
    if not reports_root.is_dir():
        return None
    runs = [p for p in reports_root.iterdir() if p.is_dir() and p.name != "latest"]
    if not runs:
        return None
    return max(runs, key=lambda p: p.stat().st_mtime)


def _parse_summary(path: Path) -> dict[str, int]:
    out = {key: 0 for key in SUMMARY_PATTERNS}
    if not path.is_file():
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    for key, pattern in SUMMARY_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            out[key] = max(int(m) for m in matches)
    return out


def _parse_junit(path: Path) -> dict[str, int]:
    out = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    if not path.is_file():
        return out
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return out
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    for suite in suites:
        for key in out:
            out[key] += int(suite.attrib.get(key, 0) or 0)
    return out


def artifact_status(project_root: Path, reports_root: Path | None = None) -> dict[str, object]:
    root = reports_root or project_root / ".cognitive-os" / "reports" / "test-runs"
    run_dir = _latest_run(root)
    if run_dir is None:
        return {
            "available": False,
            "status": "missing",
            "run_dir": "",
            "summary_txt": "",
            "inventory_md": "",
            "junit_xml": "",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "xfailed": 0,
            "xpassed": 0,
            "tests": 0,
        }

    summary_path = run_dir / "summary.txt"
    inventory_path = run_dir / "inventory.md"
    junit_path = run_dir / "junit.xml"
    summary = _parse_summary(summary_path)
    junit = _parse_junit(junit_path)
    failed = max(summary.get("failed", 0), junit.get("failures", 0))
    errors = max(summary.get("errors", 0), junit.get("errors", 0))
    tests = junit.get("tests", 0)
    passed = summary.get("passed", 0)
    if tests and not passed:
        passed = max(0, tests - failed - errors - junit.get("skipped", 0))
    status = "pass" if (tests or passed) and failed == 0 and errors == 0 else "fail"
    return {
        "available": True,
        "status": status,
        "run_dir": str(run_dir),
        "summary_txt": str(summary_path) if summary_path.is_file() else "",
        "inventory_md": str(inventory_path) if inventory_path.is_file() else "",
        "junit_xml": str(junit_path) if junit_path.is_file() else "",
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": max(summary.get("skipped", 0), junit.get("skipped", 0)),
        "xfailed": summary.get("xfailed", 0),
        "xpassed": summary.get("xpassed", 0),
        "tests": tests,
    }


def coverage_artifact_status(
    project_root: Path,
    reports_root: Path | None = None,
    threshold: int = 80,
) -> dict[str, object]:
    """Read the latest persisted coverage report artifact."""
    root = reports_root or project_root / ".cognitive-os" / "reports" / "coverage"
    run_dir = _latest_run(root)
    if run_dir is None:
        return {
            "available": False,
            "status": "missing",
            "run_dir": "",
            "summary_txt": "",
            "coverage_json": "",
            "coverage_pct": 0,
            "covered": 0,
            "total": 0,
            "threshold": threshold,
        }

    summary_path = run_dir / "summary.txt"
    coverage_json = run_dir / "coverage.json"
    coverage_pct = 0
    covered = 0
    total = 0

    if coverage_json.is_file():
        try:
            payload = json.loads(coverage_json.read_text(encoding="utf-8"))
            coverage_pct = int(payload.get("composite_pct", 0) or 0)
            covered = int(payload.get("composite_covered", 0) or 0)
            total = int(payload.get("composite_total", 0) or 0)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    if summary_path.is_file() and (not coverage_pct or not total):
        text = summary_path.read_text(encoding="utf-8", errors="replace")
        match = COVERAGE_PATTERN.search(text)
        if match:
            coverage_pct = int(match.group(1))
            covered = int(match.group(2))
            total = int(match.group(3))

    status = "pass" if total and coverage_pct >= threshold else "fail"
    return {
        "available": True,
        "status": status,
        "run_dir": str(run_dir),
        "summary_txt": str(summary_path) if summary_path.is_file() else "",
        "coverage_json": str(coverage_json) if coverage_json.is_file() else "",
        "coverage_pct": coverage_pct,
        "covered": covered,
        "total": total,
        "threshold": threshold,
    }


def quality_artifact_status(project_root: Path, reports_root: Path | None = None) -> dict[str, object]:
    """Read the latest persisted test-quality audit artifact."""
    root = reports_root or project_root / ".cognitive-os" / "reports" / "test-quality"
    run_dir = _latest_run(root)
    if run_dir is None:
        return {
            "available": False,
            "status": "missing",
            "run_dir": "",
            "summary_txt": "",
            "quality_json": "",
            "total": 0,
            "blocking_count": 0,
        }

    summary_path = run_dir / "summary.txt"
    quality_json = run_dir / "quality.json"
    total = 0
    blocking_count = 0
    if quality_json.is_file():
        try:
            payload = json.loads(quality_json.read_text(encoding="utf-8"))
            total = int(payload.get("total", 0) or 0)
            blocking_count = int(payload.get("blocking_count", 0) or 0)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass
    status = "pass" if total and blocking_count == 0 else "fail"
    return {
        "available": True,
        "status": status,
        "run_dir": str(run_dir),
        "summary_txt": str(summary_path) if summary_path.is_file() else "",
        "quality_json": str(quality_json) if quality_json.is_file() else "",
        "total": total,
        "blocking_count": blocking_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--reports-root", default="")
    parser.add_argument(
        "--artifact-kind",
        choices=("test", "coverage", "quality"),
        default="test",
        help="Persisted artifact family to read.",
    )
    parser.add_argument("--coverage-threshold", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    reports_root = Path(args.reports_root).resolve() if args.reports_root else None
    if args.artifact_kind == "coverage":
        status = coverage_artifact_status(project_root, reports_root, args.coverage_threshold)
    elif args.artifact_kind == "quality":
        status = quality_artifact_status(project_root, reports_root)
    else:
        status = artifact_status(project_root, reports_root)
    if args.json:
        print(json.dumps(status, sort_keys=True))
    else:
        if args.artifact_kind == "coverage":
            print(
                f"{status['status']} coverage={status['coverage_pct']} "
                f"threshold={status['threshold']} run_dir={status['run_dir']}"
            )
        elif args.artifact_kind == "quality":
            print(
                f"{status['status']} total={status['total']} "
                f"blocking={status['blocking_count']} run_dir={status['run_dir']}"
            )
        else:
            print(f"{status['status']} passed={status['passed']} failed={status['failed']} errors={status['errors']} run_dir={status['run_dir']}")
    return 0 if status["available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
