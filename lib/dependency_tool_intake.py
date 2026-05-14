# SCOPE: os-only
"""Dependency tool intake/triage over ADR-305 coverage reports."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.dependency_coverage_audit import build_report, dumps_json as dumps_coverage_json, format_human as format_coverage_human  # noqa: E402

SCHEMA_VERSION = "cos-deps-triage.v1"
ACTIONABLE_BUCKETS = {"missing_from_manifest", "optional_lane_needed", "blocked_or_removed_by_policy"}


def load_coverage(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_source(row: dict[str, Any]) -> dict[str, Any]:
    sources = row.get("sources") or []
    return sources[0] if sources else {}


def _lane_from_sources(row: dict[str, Any]) -> str | None:
    for source in row.get("sources") or []:
        path = str(source.get("path", ""))
        prefix = "requirements/dependency-lanes/"
        if path.startswith(prefix) and path.endswith(".txt"):
            return Path(path).stem
    return None


def _fingerprint(bucket: str, row: dict[str, Any]) -> str:
    source = _first_source(row)
    return "|".join([
        bucket,
        str(row.get("kind", "")),
        str(row.get("name", "")),
        str(source.get("path", "")),
    ])


def _proposal(bucket: str, row: dict[str, Any]) -> dict[str, Any]:
    kind = str(row.get("kind", ""))
    name = str(row.get("name", ""))
    details = dict(row.get("details") or {})
    lane = _lane_from_sources(row)

    if bucket == "blocked_or_removed_by_policy":
        action = "block_or_remove"
        rationale = "Observed dependency is marked REMOVE/REJECT or cleanup-required by external-tool policy."
    elif bucket == "optional_lane_needed" or lane:
        action = "map_python_lane_to_manifest_profile"
        rationale = "Observed Python dependency belongs to an optional lane; keep it opt-in and map the lane/profile explicitly."
        details["lane"] = lane
    elif bucket == "missing_from_manifest" and kind == "host-tool":
        action = "triage_manifest_profile"
        rationale = "Observed host tool is used/probed by COS but absent from manifests/dependencies.yaml."
    elif bucket == "missing_from_manifest" and kind == "python":
        action = "triage_python_group_or_lane"
        rationale = "Observed Python dependency is absent from manifest Python groups; choose core group or optional lane."
    elif bucket == "platform_builtin":
        action = "keep_platform_builtin"
        rationale = "Platform utility should not become install-profile debt unless promoted by policy."
    elif bucket == "internal_helper_false_positive":
        action = "suppress_false_positive"
        rationale = "Observed command-like token is an internal shell helper, not an external dependency."
    elif bucket == "manifested_but_unused":
        action = "review_unused_manifest_entry"
        rationale = "Manifest entry is not observed by command probes; review before removing because docs/humans may consume it."
    else:
        action = "review"
        rationale = "Unclassified dependency coverage finding requires human review."

    return {
        "fingerprint": _fingerprint(bucket, row),
        "name": name,
        "kind": kind,
        "bucket": bucket,
        "action": action,
        "rationale": rationale,
        "sources": row.get("sources", []),
        **({"details": details} if details else {}),
    }


def build_triage_report(coverage: dict[str, Any]) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []
    for bucket in [
        "blocked_or_removed_by_policy",
        "missing_from_manifest",
        "optional_lane_needed",
        "platform_builtin",
        "internal_helper_false_positive",
        "manifested_but_unused",
    ]:
        for row in coverage.get(bucket, []) or []:
            proposals.append(_proposal(bucket, row))

    action_counts = Counter(proposal["action"] for proposal in proposals)
    bucket_counts = Counter(proposal["bucket"] for proposal in proposals)
    actionable = [proposal for proposal in proposals if proposal["bucket"] in ACTIONABLE_BUCKETS]

    return {
        "schema_version": SCHEMA_VERSION,
        "coverage_schema_version": coverage.get("schema_version"),
        "summary": {
            "proposals": len(proposals),
            "actionable": len(actionable),
            "actions": dict(sorted(action_counts.items())),
            "buckets": dict(sorted(bucket_counts.items())),
        },
        "proposals": sorted(proposals, key=lambda item: (item["action"], item["name"], item["fingerprint"])),
    }


def format_human(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        f"dependency tool intake: {report.get('schema_version')}",
        f"  proposals: {summary.get('proposals', 0)}",
        f"  actionable: {summary.get('actionable', 0)}",
    ]
    actions = summary.get("actions") or {}
    if actions:
        lines.append("  actions:")
        for action, count in actions.items():
            lines.append(f"    {action}: {count}")
    actionable = [p for p in report.get("proposals", []) if p.get("bucket") in ACTIONABLE_BUCKETS][:20]
    if actionable:
        lines.append("\nactionable sample:")
        for proposal in actionable:
            lines.append(f"  - {proposal['action']}: {proposal['name']} ({proposal['kind']})")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage ADR-305 dependency coverage findings into safe maintenance actions.")
    parser.add_argument("--root", default=".", help="Repository root to audit when --coverage-report is omitted.")
    parser.add_argument("--coverage-report", type=Path, help="Existing cos-deps-coverage-audit JSON report.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--coverage-json", action="store_true", help="Emit raw coverage JSON instead of triage JSON.")
    args = parser.parse_args(argv)

    coverage = load_coverage(args.coverage_report) if args.coverage_report else build_report(Path(args.root))
    if args.coverage_json:
        print(dumps_coverage_json(coverage), end="")
        return 0
    report = build_triage_report(coverage)
    print(json.dumps(report, indent=2, sort_keys=True) + "\n" if args.json else format_human(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
