#!/usr/bin/env python3
# SCOPE: both
"""Generate a prioritized report for unresolved primitive surface coverage partials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

STATUS_RANK = {"partial": 0, "missing": 1, "unverified": 2, "aligned": 9}
POLICY_RANK = {
    "must-fix-parity": 0,
    "codex-adapter-needed": 1,
    "projectable-needs-driver": 2,
    "behavior-proof-needed": 3,
    "unclassified": 4,
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _priority(row: dict[str, Any]) -> tuple[int, int, str]:
    return (
        STATUS_RANK.get(str(row.get("gap_status") or ""), 5),
        POLICY_RANK.get(str(row.get("gap_policy") or ""), 8),
        str(row.get("primitive") or ""),
    )


def _action(row: dict[str, Any]) -> str:
    policy = row.get("gap_policy")
    gap = str(row.get("gap") or "")
    if policy == "must-fix-parity":
        return "Implement missing native parity or demote the scope before promotion."
    if policy == "codex-adapter-needed":
        if "missing projected/wired support" in gap:
            return "Add a Codex adapter/projection, or reclassify as accepted no-equivalent-event with evidence."
        return "Add behavior evidence or refine policy so this is not misclassified as an adapter gap."
    if policy == "projectable-needs-driver":
        return "Add a consumer projection driver or demote from projectable scope."
    if policy == "behavior-proof-needed":
        return "Map explicit tests/manual tests in manifests/primitive-behavior-evidence.yaml."
    return "Triage policy, severity, and owner."


def build_partials_report(coverage: dict[str, Any], limit: int | None = None) -> dict[str, Any]:
    rows = [row for row in coverage.get("items", []) if row.get("gap_status") == "partial"]
    rows.sort(key=_priority)
    if limit is not None:
        rows = rows[:limit]
    return {
        "schema_version": "primitive-harness-partials.v1",
        "source_schema_version": coverage.get("schema_version"),
        "summary": {
            "partial_count": len(rows),
            "total_gaps": coverage.get("summary", {}).get("gaps", 0),
            "unclassified_gaps": coverage.get("summary", {}).get("unclassified_gaps", 0),
            "by_policy": _counts(rows, "gap_policy"),
            "by_severity": _counts(rows, "gap_severity"),
        },
        "items": [
            {
                "primitive": row.get("primitive"),
                "family": row.get("family"),
                "scope": row.get("scope"),
                "gap": row.get("gap"),
                "gap_policy": row.get("gap_policy"),
                "gap_severity": row.get("gap_severity"),
                "coverage": row.get("coverage"),
                "next_action": _action(row),
            }
            for row in rows
        ],
    }


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "")
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Primitive Harness Partials — Prioritized",
        "",
        "This report lists classified-but-unresolved primitive surface coverage debt. It intentionally excludes aligned gaps.",
        "",
        f"Partial count: {report['summary']['partial_count']}",
        f"Total gaps in source report: {report['summary']['total_gaps']}",
        f"Unclassified gaps: {report['summary']['unclassified_gaps']}",
        f"By policy: {report['summary']['by_policy']}",
        "",
        "## Priority order",
        "",
        "1. `must-fix-parity`",
        "2. `codex-adapter-needed`",
        "3. `projectable-needs-driver`",
        "4. `behavior-proof-needed`",
        "5. remaining partials",
        "",
        "| # | Primitive | Family | Scope | Policy | Severity | Coverage | Gap | Next action |",
        "|---:|---|---|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(report["items"], start=1):
        lines.append(
            "| {index} | `{primitive}` | {family} | {scope} | {policy} | {severity} | {coverage} | {gap} | {action} |".format(
                index=index,
                primitive=row.get("primitive") or "",
                family=row.get("family") or "",
                scope=row.get("scope") or "",
                policy=row.get("gap_policy") or "",
                severity=row.get("gap_severity") or "",
                coverage=row.get("coverage") or "",
                gap=str(row.get("gap") or "").replace("|", "\\|"),
                action=str(row.get("next_action") or "").replace("|", "\\|"),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build prioritized primitive harness partials report")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--coverage-json", default="docs/reports/primitive-harness-coverage-latest.json")
    parser.add_argument("--json-out", default="docs/reports/primitive-harness-partials-latest.json")
    parser.add_argument("--md-out", default="docs/reports/primitive-harness-partials-latest.md")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_dir).resolve()
    coverage = _load_json(root / args.coverage_json)
    report = build_partials_report(coverage, limit=args.limit)
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": str(json_path), "markdown": str(md_path), **report["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
