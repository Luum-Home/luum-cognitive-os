#!/usr/bin/env python3
# SCOPE: both
"""Generate ADR-258 consumer impact report for the portable `.ai` overlay."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.consumer_fleet_audit import build_report as build_consumer_report
from scripts.portable_ai_overlay import build_overlay

SCHEMA_VERSION = "portable-ai-consumer-impact.v1"
DEFAULT_JSON = Path("docs/reports/portable-ai-consumer-impact-latest.json")
DEFAULT_MD = Path("docs/reports/portable-ai-consumer-impact-latest.md")


def _count_prefix(files: dict[str, str], prefix: str) -> int:
    return sum(1 for path in files if path.startswith(prefix))


def build_report(root: Path) -> dict[str, Any]:
    overlay = build_overlay(root)
    consumer = build_consumer_report(root, None)
    adapter_files = sorted(path for path in overlay if path.startswith("adapters/"))
    profile_files = sorted(path for path in overlay if path.startswith("profiles/"))
    primitive_files = sorted(path for path in overlay if path.startswith("primitives/"))
    status = "pass" if consumer.get("status") in {"pass", "warn"} else "fail"
    if consumer.get("status") == "warn":
        status = "warn"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "overlay": {
            "file_count": len(overlay),
            "primitive_file_count": len(primitive_files),
            "profile_file_count": len(profile_files),
            "adapter_file_count": len(adapter_files),
            "schema_file_count": _count_prefix(overlay, "logs/schema/"),
            "state_file_count": _count_prefix(overlay, "state/"),
        },
        "consumer_fleet": {
            "status": consumer.get("status"),
            "summary": consumer.get("summary", {}),
            "finding_count": len(consumer.get("findings", [])),
        },
        "decision": {
            "canonical_migration_allowed": False,
            "reason": "ADR-258 keeps `.ai` as a generated maintainer overlay; native consumer projection is allowed only through governed fidelity-preserving compilers and consumer proof.",
            "mutates_consumers": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    overlay = report["overlay"]
    fleet = report["consumer_fleet"]
    return "\n".join([
        "# Portable `.ai` Consumer Impact — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Schema: `{report['schema_version']}`",
        f"Status: `{report['status']}`",
        "",
        "## Overlay",
        "",
        f"- files: {overlay['file_count']}",
        f"- primitive files: {overlay['primitive_file_count']}",
        f"- profile files: {overlay['profile_file_count']}",
        f"- adapter files: {overlay['adapter_file_count']}",
        "",
        "## Consumer fleet",
        "",
        f"- status: `{fleet['status']}`",
        f"- findings: {fleet['finding_count']}",
        f"- summary: `{json.dumps(fleet['summary'], sort_keys=True)}`",
        "",
        "## Decision",
        "",
        "The `.ai` overlay is generated and does not mutate consumer projects by itself. Canonical migration remains blocked.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    root = args.project_dir.resolve()
    report = build_report(root)
    if not args.no_write:
        (root / DEFAULT_JSON).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (root / DEFAULT_MD).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"portable-ai-consumer-impact: {report['status']} files={report['overlay']['file_count']} fleet={report['consumer_fleet']['status']}")
    return 0 if report["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
