#!/usr/bin/env python3
# SCOPE: both
# @manual-trigger: invoke to aggregate per-scenario red-team JSON results; part of red-team harness suite
# redteam_aggregate.py — Aggregates per-scenario JSON results into a baseline.
#
# Reads per-scenario JSON files produced by run-redteam-scenario.sh and:
#   1. Compiles a summary (pass/fail/partial/xfail/error counts)
#   2. Builds a verb_coverage matrix
#   3. Writes output JSON per design §3.5 schema
#   4. Writes Markdown table + verb coverage matrix
#   5. Optionally diffs against a prior baseline
#
# Part of: red-team-harness Wave W5 (§3.5)
#
# Usage:
#   python3 scripts/redteam_aggregate.py \
#     --input-dir <path> \
#     [--output-json <path>] \
#     [--output-md <path>] \
#     [--baseline-compare <path>]
#
# Output JSON schema_version: 1.0.0 (see design §3.5)
# Naming: snake_case per RULES §13 (Python)

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HARNESS_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"

STATUS_KEYS = ("pass", "fail", "partial", "xfail", "error")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Aggregate red-team scenario JSON results into a baseline."
    )
    p.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing per-scenario JSON files from run-redteam-scenario.sh",
    )
    p.add_argument(
        "--output-json",
        default="docs/06-Daily/reports/redteam-baseline.json",
        help="Output JSON path (default: docs/06-Daily/reports/redteam-baseline.json)",
    )
    p.add_argument(
        "--output-md",
        default="docs/06-Daily/reports/redteam-baseline.md",
        help="Output Markdown path (default: docs/06-Daily/reports/redteam-baseline.md)",
    )
    p.add_argument(
        "--baseline-compare",
        default=None,
        help="Path to prior baseline JSON; adds diff section to Markdown output",
    )
    return p.parse_args()


def load_scenario_results(input_dir: str) -> list[dict[str, Any]]:
    """Load all *.json files from input_dir, skip non-scenario files."""
    results: list[dict[str, Any]] = []
    input_path = Path(input_dir)
    if not input_path.is_dir():
        print(f"[redteam-aggregate] ERROR: input-dir not found: {input_dir}", file=sys.stderr)
        sys.exit(3)

    json_files = sorted(input_path.glob("*.json"))
    if not json_files:
        print(f"[redteam-aggregate] WARNING: No JSON files found in {input_dir}", file=sys.stderr)

    for json_file in json_files:
        try:
            with open(json_file) as f:
                data = json.load(f)
            # Require at minimum: scenario id and status
            if "scenario" not in data or "status" not in data:
                print(
                    f"[redteam-aggregate] SKIP: {json_file.name} — missing 'scenario' or 'status' field",
                    file=sys.stderr,
                )
                continue
            results.append(data)
        except json.JSONDecodeError as e:
            print(f"[redteam-aggregate] SKIP: {json_file.name} — JSON decode error: {e}", file=sys.stderr)

    return results


def build_summary(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {k: 0 for k in STATUS_KEYS}
    summary["total"] = len(results)
    for r in results:
        status = r.get("status", "error").lower()
        if status in summary:
            summary[status] += 1
        else:
            summary["error"] += 1
    return summary


def build_verb_coverage(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count scenarios per ADR-105 verb."""
    coverage: dict[str, int] = {}
    for r in results:
        verb = r.get("verb")
        if verb:
            coverage[verb] = coverage.get(verb, 0) + 1
    return coverage


def build_scenarios_list(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the scenarios[] array per design §3.5 schema."""
    out = []
    for r in results:
        out.append({
            "id": r.get("scenario", "unknown"),
            "version": r.get("version", "unknown"),
            "status": r.get("status", "error"),
            "verb": r.get("verb"),
            "severity": r.get("severity", "UNKNOWN"),
            "duration_seconds": r.get("duration_seconds", 0.0),
            "signals_matched": r.get("signals_matched"),
            "signals_total": r.get("signals_total"),
            "scope": r.get("scope", "unknown"),
            "category": r.get("category", "unknown"),
        })
    return out


def build_output_json(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "harness_version": HARNESS_VERSION,
        "scenarios": build_scenarios_list(results),
        "summary": build_summary(results),
        "verb_coverage": build_verb_coverage(results),
    }


def status_emoji(status: str) -> str:
    return {
        "pass": "PASS",
        "fail": "FAIL",
        "partial": "PARTIAL",
        "xfail": "XFAIL",
        "error": "ERROR",
    }.get(status.lower(), status.upper())


def build_markdown(
    output: dict[str, Any],
    baseline_compare: str | None,
    prior: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    generated_at = output["generated_at"]
    summary = output["summary"]
    verb_coverage = output["verb_coverage"]
    scenarios = output["scenarios"]

    lines.append("# Red-Team Harness Baseline Report")
    lines.append("")
    lines.append(f"**Generated**: {generated_at}  ")
    lines.append(f"**Harness version**: {output['harness_version']}  ")
    lines.append(f"**Schema**: v{output['schema_version']}")
    lines.append("")

    # Summary box
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Total | Pass | Fail | Partial | XFail | Error |")
    lines.append(f"|-------|------|------|---------|-------|-------|")
    lines.append(
        f"| {summary['total']} "
        f"| {summary['pass']} "
        f"| {summary['fail']} "
        f"| {summary['partial']} "
        f"| {summary['xfail']} "
        f"| {summary['error']} |"
    )
    lines.append("")

    # Scenario table
    lines.append("## Scenario Results")
    lines.append("")
    lines.append("| Scenario | Version | Status | Verb | Severity | Scope | Signals | Duration |")
    lines.append("|----------|---------|--------|------|----------|-------|---------|----------|")
    for s in scenarios:
        sig = (
            f"{s['signals_matched']}/{s['signals_total']}"
            if s.get("signals_matched") is not None
            else "n/a"
        )
        lines.append(
            f"| {s['id']} "
            f"| {s['version']} "
            f"| {status_emoji(s['status'])} "
            f"| {s.get('verb') or 'n/a'} "
            f"| {s['severity']} "
            f"| {s['scope']} "
            f"| {sig} "
            f"| {s['duration_seconds']:.2f}s |"
        )
    lines.append("")

    # Verb coverage matrix
    lines.append("## Verb Coverage Matrix")
    lines.append("")
    # ADR-105 canonical verbs
    adr105_verbs = ["archived", "wired", "tested", "verified", "claimed", "completed"]
    lines.append("| ADR-105 Verb | Scenarios | Coverage |")
    lines.append("|-------------|-----------|----------|")
    for verb in adr105_verbs:
        count = verb_coverage.get(verb, 0)
        coverage_str = "YES" if count > 0 else "MISSING"
        lines.append(f"| {verb} | {count} | {coverage_str} |")
    # Add any extra verbs not in canonical list
    for verb, count in sorted(verb_coverage.items()):
        if verb not in adr105_verbs:
            lines.append(f"| {verb} (extra) | {count} | YES |")
    lines.append("")

    # Diff section if baseline-compare provided
    if prior is not None and baseline_compare is not None:
        lines.append("## Baseline Diff")
        lines.append("")
        lines.append(f"Comparing against: `{baseline_compare}`")
        lines.append("")
        prior_scenarios = {s["id"]: s for s in prior.get("scenarios", [])}
        current_scenarios = {s["id"]: s for s in scenarios}

        new_ids = set(current_scenarios) - set(prior_scenarios)
        removed_ids = set(prior_scenarios) - set(current_scenarios)
        changed = []
        for sid in set(current_scenarios) & set(prior_scenarios):
            cur = current_scenarios[sid]
            prv = prior_scenarios[sid]
            if cur["status"] != prv["status"]:
                changed.append((sid, prv["status"], cur["status"]))

        if new_ids:
            lines.append(f"**New scenarios** ({len(new_ids)}): {', '.join(sorted(new_ids))}")
            lines.append("")
        if removed_ids:
            lines.append(f"**Removed scenarios** ({len(removed_ids)}): {', '.join(sorted(removed_ids))}")
            lines.append("")
        if changed:
            lines.append("**Status changes:**")
            lines.append("")
            lines.append("| Scenario | Before | After |")
            lines.append("|----------|--------|-------|")
            for sid, before, after in sorted(changed):
                lines.append(f"| {sid} | {status_emoji(before)} | {status_emoji(after)} |")
            lines.append("")
        if not new_ids and not removed_ids and not changed:
            lines.append("_No changes from prior baseline._")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    # Load scenario results
    results = load_scenario_results(args.input_dir)

    # Build output
    output = build_output_json(results)

    # Load prior baseline if provided
    prior: dict[str, Any] | None = None
    if args.baseline_compare:
        try:
            with open(args.baseline_compare) as f:
                prior = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[redteam-aggregate] WARNING: Could not load baseline-compare: {e}", file=sys.stderr)

    # Write JSON
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[redteam-aggregate] JSON baseline written: {args.output_json}")

    # Write Markdown
    md_content = build_markdown(output, args.baseline_compare, prior)
    Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_md, "w") as f:
        f.write(md_content)
    print(f"[redteam-aggregate] Markdown baseline written: {args.output_md}")

    # Print summary to stdout
    s = output["summary"]
    print(
        f"[redteam-aggregate] Results: {s['total']} total | "
        f"{s['pass']} pass | {s['fail']} fail | "
        f"{s['partial']} partial | {s['xfail']} xfail | {s['error']} error"
    )

    # Exit non-zero if any failures
    if s["fail"] > 0 or s["error"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
