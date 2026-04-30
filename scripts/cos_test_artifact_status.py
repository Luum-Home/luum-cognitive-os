#!/usr/bin/env python3
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--reports-root", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    reports_root = Path(args.reports_root).resolve() if args.reports_root else None
    status = artifact_status(project_root, reports_root)
    if args.json:
        print(json.dumps(status, sort_keys=True))
    else:
        print(f"{status['status']} passed={status['passed']} failed={status['failed']} errors={status['errors']} run_dir={status['run_dir']}")
    return 0 if status["available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
