# SCOPE: os-only
"""Fail-new ratchet for dependency coverage triage reports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.dependency_tool_intake import ACTIONABLE_BUCKETS, build_triage_report, load_coverage  # noqa: E402
from lib.dependency_coverage_audit import build_report  # noqa: E402

SCHEMA_VERSION = "cos-deps-profile-ratchet.v1"
DEFAULT_BASELINE = Path("manifests/dependency-coverage-baseline.yaml")


def load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item) for item in data.get("accepted_findings", []) or []}


def evaluate(triage: dict[str, Any], accepted: set[str]) -> dict[str, Any]:
    actionable = [p for p in triage.get("proposals", []) if p.get("bucket") in ACTIONABLE_BUCKETS]
    new = [p for p in actionable if p.get("fingerprint") not in accepted]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if not new else "block",
        "accepted_findings": len(accepted),
        "actionable_findings": len(actionable),
        "new_findings": len(new),
        "new": new,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when ADR-305 dependency coverage introduces unaccepted actionable findings.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--coverage-report", type=Path)
    parser.add_argument("--triage-report", type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.triage_report:
        triage = json.loads(args.triage_report.read_text(encoding="utf-8"))
    else:
        coverage = load_coverage(args.coverage_report) if args.coverage_report else build_report(Path(args.root))
        triage = build_triage_report(coverage)
    baseline = args.baseline if args.baseline.is_absolute() else Path(args.root) / args.baseline
    report = evaluate(triage, load_baseline(baseline))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"dependency profile ratchet: {report['status']} new_findings={report['new_findings']} accepted={report['accepted_findings']}")
        for row in report.get("new", [])[:20]:
            print(f"- {row['fingerprint']}")
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
