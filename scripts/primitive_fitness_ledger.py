#!/usr/bin/env python3
# SCOPE: both
"""Aggregate primitive fitness reports by agentic primitive family.

The ledger is a visibility surface for ACC/readiness consumers. It does not run
fitness evaluations and does not promote primitives; it summarizes already
produced primitive-fitness reports.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import write_json  # noqa: E402

REPORT_GLOBS = (
    "docs/reports/primitive-fitness/*.json",
    ".cognitive-os/reports/primitive-fitness/*.json",
    ".cognitive-os/metrics/primitive-fitness-reports/*.json",
)
FAMILIES = ("hooks", "skills", "scripts", "rules", "other")
VERDICT_TO_STATUS = {
    "promote": "aligned",
    "keep_draft": "partial",
    "needs_evidence": "unverified",
    "reject": "stale",
}


def primitive_family(primitive_id: str) -> str:
    normalized = primitive_id.strip().lower()
    for family in ("hooks", "skills", "scripts", "rules"):
        if normalized.startswith(f"{family}/") or normalized.startswith(f"{family}:"):
            return family
    if normalized.startswith("hook:"):
        return "hooks"
    if normalized.startswith("skill:"):
        return "skills"
    if normalized.startswith("script:"):
        return "scripts"
    if normalized.startswith("rule:"):
        return "rules"
    return "other"


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def row_from_report(path: Path, report: dict[str, Any], root: Path) -> dict[str, Any] | None:
    primitive_id = str(report.get("primitive_id") or "").strip()
    if not primitive_id:
        return None
    verdict = str(report.get("verdict") or "needs_evidence")
    baseline = report.get("baseline") if isinstance(report.get("baseline"), dict) else {}
    candidate = report.get("candidate") if isinstance(report.get("candidate"), dict) else {}
    safety_regressions = report.get("safety_regressions") if isinstance(report.get("safety_regressions"), list) else []
    missing_signals = report.get("missing_signals") if isinstance(report.get("missing_signals"), list) else []
    evidence_commands = report.get("evidence_commands") if isinstance(report.get("evidence_commands"), list) else []
    source = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    return {
        "primitive_id": primitive_id,
        "family": primitive_family(primitive_id),
        "verdict": verdict,
        "mapping_status": VERDICT_TO_STATUS.get(verdict, "unverified"),
        "status": str(report.get("status") or ""),
        "delta": report.get("delta"),
        "required_delta": report.get("required_delta"),
        "baseline_score": baseline.get("overall_score"),
        "candidate_score": candidate.get("overall_score"),
        "baseline_sample_count": baseline.get("sample_count"),
        "candidate_sample_count": candidate.get("sample_count"),
        "safety_regressions": [str(item) for item in safety_regressions],
        "missing_signals": [str(item) for item in missing_signals],
        "evidence_commands": [str(item) for item in evidence_commands],
        "source_report": source,
    }


def discover_reports(root: Path, explicit_inputs: list[str]) -> list[Path]:
    found: dict[str, Path] = {}
    for item in explicit_inputs:
        path = Path(item)
        if not path.is_absolute():
            path = root / path
        if path.exists():
            found[str(path.resolve())] = path.resolve()
    for pattern in REPORT_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                found[str(path.resolve())] = path.resolve()
    return [found[key] for key in sorted(found)]


def build_ledger(root: Path, explicit_inputs: list[str] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    unreadable = 0
    for path in discover_reports(root, explicit_inputs or []):
        payload = load_json(path)
        if payload is None:
            unreadable += 1
            continue
        row = row_from_report(path, payload, root)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda item: (item["family"], item["primitive_id"], item["source_report"]))

    by_family: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        verdicts = Counter(row["verdict"] for row in family_rows)
        statuses = Counter(row["mapping_status"] for row in family_rows)
        scores = [float(row["candidate_score"]) for row in family_rows if isinstance(row.get("candidate_score"), int | float)]
        by_family[family] = {
            "total": len(family_rows),
            "verdicts": dict(sorted(verdicts.items())),
            "mapping_statuses": dict(sorted(statuses.items())),
            "average_candidate_score": round(sum(scores) / len(scores), 2) if scores else None,
            "needs_evidence": verdicts.get("needs_evidence", 0),
            "reject": verdicts.get("reject", 0),
            "promote": verdicts.get("promote", 0),
        }
    verdict_counts = Counter(row["verdict"] for row in rows)
    status_counts = Counter(row["mapping_status"] for row in rows)
    return {
        "schema_version": "primitive-fitness-ledger.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_globs": list(REPORT_GLOBS),
        "summary": {
            "total_reports": len(rows),
            "unreadable_reports": unreadable,
            "families": by_family,
            "verdicts": dict(sorted(verdict_counts.items())),
            "mapping_statuses": dict(sorted(status_counts.items())),
        },
        "items": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Primitive Fitness Ledger — Latest",
        "",
        f"Generated: {payload['generated_at']}",
        f"Total reports: {summary['total_reports']}",
        f"Unreadable reports: {summary['unreadable_reports']}",
        "",
        "## Family Summary",
        "",
        "| Family | Total | Promote | Keep draft | Needs evidence | Reject | Average candidate score |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for family in FAMILIES:
        data = summary["families"][family]
        verdicts = data["verdicts"]
        score = "" if data["average_candidate_score"] is None else f"{data['average_candidate_score']:.2f}"
        lines.append(
            f"| {family} | {data['total']} | {verdicts.get('promote', 0)} | {verdicts.get('keep_draft', 0)} | {verdicts.get('needs_evidence', 0)} | {verdicts.get('reject', 0)} | {score} |"
        )
    lines += [
        "",
        "## Reports",
        "",
        "| Primitive | Family | Verdict | Delta | Candidate | Baseline | Source |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in payload["items"]:
        lines.append(
            f"| `{row['primitive_id']}` | {row['family']} | {row['verdict']} | {row.get('delta') if row.get('delta') is not None else ''} | {row.get('candidate_score') if row.get('candidate_score') is not None else ''} | {row.get('baseline_score') if row.get('baseline_score') is not None else ''} | `{row['source_report']}` |"
        )
    if not payload["items"]:
        lines.append("| none | - | needs_evidence |  |  |  | no primitive fitness reports found |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate primitive fitness reports by family")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--input", action="append", default=[], help="Additional primitive fitness report JSON path")
    parser.add_argument("--json-out", default="docs/reports/primitive-fitness-ledger-latest.json")
    parser.add_argument("--md-out", default="docs/reports/primitive-fitness-ledger-latest.md")
    parser.add_argument("--json", action="store_true", help="Print the ledger JSON payload")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    payload = build_ledger(root, args.input)
    json_out = root / args.json_out
    md_out = root / args.md_out
    write_json(json_out, payload)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(render_markdown(payload), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": args.json_out, "markdown": args.md_out, "summary": payload["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
