#!/usr/bin/env python3
# SCOPE: os-only
"""Validate pytest skipped tests against the expected-skip registry."""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SkipCase:
    classname: str
    name: str
    file: str
    line: str
    message: str
    text: str

    @property
    def reason(self) -> str:
        return " ".join(part for part in [self.message, self.text] if part).strip()

    @property
    def nodeid(self) -> str:
        prefix = self.file or self.classname
        return f"{prefix}::{self.name}"


def parse_junit(path: Path) -> list[SkipCase]:
    if not path.exists():
        return []
    root = ET.parse(path).getroot()
    cases: list[SkipCase] = []
    for testcase in root.iter("testcase"):
        skipped = testcase.find("skipped")
        if skipped is None:
            continue
        cases.append(
            SkipCase(
                classname=testcase.attrib.get("classname", ""),
                name=testcase.attrib.get("name", ""),
                file=testcase.attrib.get("file", ""),
                line=testcase.attrib.get("line", ""),
                message=skipped.attrib.get("message", ""),
                text=(skipped.text or "").strip(),
            )
        )
    return cases


def load_registry(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("schema_version") != "test-skip-registry.v1":
        raise ValueError(f"{path}: unsupported schema_version {data.get('schema_version')!r}")
    return data


def lane_matches(entry: dict[str, Any], lane: str) -> bool:
    lanes = entry.get("lanes") or []
    return "*" in lanes or lane in lanes


def classify(skip: SkipCase, lane: str, entries: list[dict[str, Any]]) -> dict[str, str] | None:
    reason = skip.reason
    for entry in entries:
        if not lane_matches(entry, lane):
            continue
        pattern = entry.get("reason_pattern")
        if not pattern:
            continue
        if re.search(str(pattern), reason, re.IGNORECASE):
            return {
                "id": str(entry.get("id", "")),
                "category": str(entry.get("category", "unknown")),
            }
    return None


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Test Skip Registry Summary",
        "",
        f"- Lane: {payload['lane']}",
        f"- Total skips: {payload['total_skips']}",
        f"- Unknown skips: {payload['unknown_count']}",
        f"- Status: {payload['status']}",
        "",
        "## Counts by Category",
        "",
    ]
    for category, count in sorted(payload["counts_by_category"].items()):
        lines.append(f"- {category}: {count}")
    if payload["unknown"]:
        lines += ["", "## Unknown Skips", ""]
        for item in payload["unknown"][:50]:
            lines.append(f"- `{item['nodeid']}` — {item['reason']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="manifests/test-skip-registry.yaml")
    parser.add_argument("--junit", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--fail-unknown", action="store_true")
    args = parser.parse_args(argv)

    registry = load_registry(Path(args.registry))
    entries = list(registry.get("expected_skips") or [])
    skips = parse_junit(Path(args.junit))

    counts: Counter[str] = Counter()
    matched_by_rule: Counter[str] = Counter()
    unknown: list[dict[str, str]] = []
    classified: list[dict[str, str]] = []

    for skip in skips:
        match = classify(skip, args.lane, entries)
        if match is None:
            counts["unknown"] += 1
            unknown.append({"nodeid": skip.nodeid, "reason": skip.reason})
            continue
        counts[match["category"]] += 1
        matched_by_rule[match["id"]] += 1
        classified.append({"nodeid": skip.nodeid, "reason": skip.reason, **match})

    payload = {
        "schema_version": "test-skip-summary.v1",
        "lane": args.lane,
        "total_skips": len(skips),
        "unknown_count": len(unknown),
        "status": "fail" if unknown and args.fail_unknown else "pass",
        "counts_by_category": dict(sorted(counts.items())),
        "matched_by_rule": dict(sorted(matched_by_rule.items())),
        "unknown": unknown,
        "classified": classified,
    }

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        Path(args.md_out).write_text(render_markdown(payload), encoding="utf-8")

    print(json.dumps({k: payload[k] for k in ("lane", "total_skips", "unknown_count", "status", "counts_by_category")}, sort_keys=True))
    if unknown and args.fail_unknown:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
