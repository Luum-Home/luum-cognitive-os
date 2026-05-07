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


_DEBT_PATTERNS = re.compile(
    r"(feature not yet implemented|not implemented|not yet implemented|todo|fixme|stub|placeholder|"
    r"temporar(?:y|ily)|workaround|disabled until|currently broken|known failure)",
    re.IGNORECASE,
)
_OPTIONAL_AMBIGUOUS_PATTERNS = re.compile(
    r"(got empty parameter set|no contextual_triggers defined|declares no skills|does not mention contextual trigger)",
    re.IGNORECASE,
)




def sanitize_for_report(value: str, root: Path | None = None) -> str:
    """Remove operator-specific absolute checkout paths from tracked reports."""
    out = value
    candidates = [Path.cwd()]
    if root is not None:
        candidates.append(root)
    for candidate in candidates:
        try:
            out = out.replace(str(candidate.resolve()), "<repo-root>")
        except OSError:
            out = out.replace(str(candidate), "<repo-root>")
    return out


def recommended_action(category: str, reason: str, rule_id: str = "") -> str:
    """Map a classified skip to the action the maintainer should take."""
    text = f"{reason} {rule_id}"
    if category == "unknown":
        return "triage: classify in registry or convert to failing/xfail test"
    if _DEBT_PATTERNS.search(text):
        return "xfail-with-ADR-or-fix: reproducible implementation debt must not stay skipped"
    if category == "runtime-sample-precondition":
        return "deterministic-fixture: add fixture data or keep only in runtime-observability lane"
    if category == "external-dependency":
        return "lane-opt-in: keep skip in laptop; prove in dependency/provider lane"
    if category == "opt-in-lane":
        return "lane-opt-in: keep skip in laptop; prove in explicit opt-in lane"
    if category == "optional-runtime-state":
        if _OPTIONAL_AMBIGUOUS_PATTERNS.search(text):
            return "review: convert to deterministic fixture or policy xfail if this is product debt"
        return "lane-opt-in-or-fixture: keep only if optional artifact/profile is documented"
    if category == "policy-exemption":
        return "policy-review: keep only with paired owner policy; otherwise xfail/remove"
    return "review"


def is_suspicious(category: str, reason: str, rule_id: str = "") -> bool:
    action = recommended_action(category, reason, rule_id)
    return category == "unknown" or action.startswith(("xfail", "review", "triage"))


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


def _load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source"] = str(path)
    return payload


def _latest_summaries(root: Path) -> list[dict[str, Any]]:
    by_lane: dict[str, tuple[str, Path]] = {}
    for path in root.rglob("skip-summary.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        lane = str(payload.get("lane") or "unknown")
        timestamp = path.parent.name.split("-")[0]
        current = by_lane.get(lane)
        if current is None or timestamp > current[0]:
            by_lane[lane] = (timestamp, path)
    return [_load_summary(path) for _, path in sorted(by_lane.values(), key=lambda item: item[1].as_posix())]


def build_audit_payload(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    all_items: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    by_lane: dict[str, dict[str, Any]] = {}
    suspicious: list[dict[str, str]] = []

    for summary in summaries:
        lane = str(summary.get("lane") or "unknown")
        lane_counts: Counter[str] = Counter()
        lane_total = 0
        for item in summary.get("classified") or []:
            category = str(item.get("category") or "unknown")
            reason = sanitize_for_report(str(item.get("reason") or ""))
            rule_id = str(item.get("id") or "")
            enriched = {
                "lane": lane,
                "nodeid": sanitize_for_report(str(item.get("nodeid") or "")),
                "reason": reason,
                "category": category,
                "rule_id": rule_id,
                "recommended_action": recommended_action(category, reason, rule_id),
                "source": sanitize_for_report(str(summary.get("source") or "")),
            }
            enriched["suspicious"] = str(is_suspicious(category, reason, rule_id)).lower()
            all_items.append(enriched)
            counts[category] += 1
            lane_counts[category] += 1
            lane_total += 1
            if enriched["suspicious"] == "true":
                suspicious.append(enriched)
        for item in summary.get("unknown") or []:
            reason = sanitize_for_report(str(item.get("reason") or ""))
            enriched = {
                "lane": lane,
                "nodeid": sanitize_for_report(str(item.get("nodeid") or "")),
                "reason": reason,
                "category": "unknown",
                "rule_id": "",
                "recommended_action": recommended_action("unknown", reason),
                "source": sanitize_for_report(str(summary.get("source") or "")),
                "suspicious": "true",
            }
            all_items.append(enriched)
            counts["unknown"] += 1
            lane_counts["unknown"] += 1
            lane_total += 1
            suspicious.append(enriched)
        by_lane[lane] = {
            "total_skips": lane_total,
            "counts_by_category": dict(sorted(lane_counts.items())),
            "source": summary.get("source"),
        }

    action_counts = Counter(item["recommended_action"] for item in all_items)
    return {
        "schema_version": "test-skip-audit.v1",
        "total_skips": len(all_items),
        "suspicious_count": len(suspicious),
        "counts_by_category": dict(sorted(counts.items())),
        "counts_by_action": dict(sorted(action_counts.items())),
        "lanes": dict(sorted(by_lane.items())),
        "skips": all_items,
        "suspicious": suspicious,
    }


def render_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Test Skip Audit",
        "",
        f"- Total skips: {payload['total_skips']}",
        f"- Suspicious skips: {payload['suspicious_count']}",
        "",
        "## Counts by Category",
        "",
    ]
    for category, count in payload["counts_by_category"].items():
        lines.append(f"- {category}: {count}")
    lines += ["", "## Counts by Recommended Action", ""]
    for action, count in payload["counts_by_action"].items():
        lines.append(f"- {action}: {count}")
    lines += ["", "## Lanes", ""]
    for lane, meta in payload["lanes"].items():
        lines.append(f"- {lane}: {meta['total_skips']} skips — {meta['counts_by_category']}")
    if payload["suspicious"]:
        lines += ["", "## Suspicious Skips", ""]
        for item in payload["suspicious"][:100]:
            lines.append(
                f"- `{item['lane']}::{item['nodeid']}` — {item['category']} — "
                f"{item['recommended_action']} — {item['reason']}"
            )
    lines += ["", "## All Skips", ""]
    for item in payload["skips"]:
        lines.append(
            f"- `{item['lane']}::{item['nodeid']}` — {item['category']} — "
            f"{item['recommended_action']} — {item['reason']}"
        )
    return "\n".join(lines) + "\n"


def run_single_summary(args: argparse.Namespace) -> int:
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


def run_audit(args: argparse.Namespace) -> int:
    summaries = _latest_summaries(Path(args.audit_root))
    payload = build_audit_payload(summaries)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        Path(args.md_out).write_text(render_audit_markdown(payload), encoding="utf-8")
    print(json.dumps({
        "schema_version": payload["schema_version"],
        "total_skips": payload["total_skips"],
        "suspicious_count": payload["suspicious_count"],
        "counts_by_category": payload["counts_by_category"],
        "counts_by_action": payload["counts_by_action"],
    }, sort_keys=True))
    if args.fail_suspicious and payload["suspicious_count"]:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="manifests/test-skip-registry.yaml")
    parser.add_argument("--junit")
    parser.add_argument("--lane")
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--fail-unknown", action="store_true")
    parser.add_argument("--audit-root", help="Aggregate latest skip-summary.json files under this test-runs root")
    parser.add_argument("--fail-suspicious", action="store_true")
    args = parser.parse_args(argv)

    if args.audit_root:
        return run_audit(args)
    if not args.junit or not args.lane:
        parser.error("--junit and --lane are required unless --audit-root is used")
    return run_single_summary(args)


if __name__ == "__main__":
    raise SystemExit(main())
