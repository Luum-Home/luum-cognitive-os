#!/usr/bin/env python3
# SCOPE: os-only
"""Verify every tests/integration/test_*.py file belongs to exactly one integration-* sublane."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _expand_path(root: Path, raw: str) -> list[str]:
    path = root / raw
    if raw.endswith(".py"):
        return [raw]
    if path.is_dir():
        return sorted(str(item.relative_to(root)) for item in path.glob("test_*.py"))
    return [raw]


def build_report(root: Path) -> dict[str, Any]:
    lanes = yaml.safe_load((root / ".cognitive-os/test-lanes.yaml").read_text(encoding="utf-8"))["lanes"]
    all_files = sorted(str(path.relative_to(root)) for path in (root / "tests/integration").glob("test_*.py"))
    owners: dict[str, list[str]] = {path: [] for path in all_files}
    for lane, spec in lanes.items():
        if not lane.startswith("integration-") or lane == "integration-docker":
            continue
        for raw in spec.get("paths", []) or []:
            for expanded in _expand_path(root, str(raw)):
                if expanded in owners:
                    owners[expanded].append(lane)
    unassigned = [path for path, value in owners.items() if not value]
    duplicates = {path: value for path, value in owners.items() if len(value) > 1}
    status = "pass" if not unassigned and not duplicates else "fail"
    return {
        "schema_version": "integration-lane-coverage/v1",
        "status": status,
        "total": len(all_files),
        "unassigned_count": len(unassigned),
        "duplicate_count": len(duplicates),
        "unassigned": unassigned,
        "duplicates": duplicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(ROOT))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path(args.project_dir).resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"integration-lane-coverage: {report['status']} total={report['total']} unassigned={report['unassigned_count']} duplicates={report['duplicate_count']}")
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
