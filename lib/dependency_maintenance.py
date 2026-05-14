# SCOPE: os-only
"""Dependency maintenance orchestrator for install/update/git hook flows.

This module intentionally keeps the default path read-only: it reconciles
coverage, triages findings, evaluates the fail-new ratchet, and reports the
installer dry-run command operators should execute. It does not install tools
unless a caller explicitly delegates to the installer outside this module.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.dependency_coverage_audit import build_report as build_coverage_report  # noqa: E402
from lib.dependency_profile_ratchet import DEFAULT_BASELINE, evaluate, load_baseline  # noqa: E402
from lib.dependency_tool_intake import ACTIONABLE_BUCKETS, build_triage_report, load_coverage  # noqa: E402

SCHEMA_VERSION = "cos-deps-maintain.v1"
MODES = {"install", "update", "post-merge", "pre-push", "doctor", "ci"}
DEFAULT_PROFILE = "default"


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def installer_plan(root: Path, profile: str) -> dict[str, Any]:
    script = root / "scripts" / "cos-deps-install.sh"
    command = ["bash", _relative(script, root), "--profile", profile, "--dry-run"]
    if not script.exists():
        return {
            "available": False,
            "profile": profile,
            "command": command,
            "note": "scripts/cos-deps-install.sh not found; install planning unavailable.",
        }
    return {
        "available": True,
        "profile": profile,
        "command": command,
        "note": "Run this command to preview host-tool installation. Add --apply only by explicit operator choice.",
    }


def build_maintenance_report(
    root: Path,
    mode: str,
    profile: str = DEFAULT_PROFILE,
    *,
    coverage_report: Path | None = None,
    baseline: Path | None = None,
    strict: bool = False,
    include_install_plan: bool = True,
    skipped: bool = False,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"unsupported maintenance mode: {mode}")

    root = root.resolve()
    baseline_path = baseline or DEFAULT_BASELINE
    resolved_baseline = baseline_path if baseline_path.is_absolute() else root / baseline_path

    if skipped:
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": mode,
            "status": "skipped",
            "strict": strict,
            "profile": profile,
            "summary": {"actionable": 0, "new_findings": 0},
            "reason": "COS_DEPS_MAINTENANCE=0",
        }

    coverage = load_coverage(coverage_report) if coverage_report else build_coverage_report(root)
    triage = build_triage_report(coverage)
    ratchet = evaluate(triage, load_baseline(resolved_baseline))
    actionable = [p for p in triage.get("proposals", []) if p.get("bucket") in ACTIONABLE_BUCKETS]
    status = "pass"
    if ratchet.get("new_findings", 0):
        status = "block" if strict else "warn"

    summary = {
        "coverage_missing_from_manifest": len(coverage.get("missing_from_manifest", []) or []),
        "coverage_optional_lane_needed": len(coverage.get("optional_lane_needed", []) or []),
        "triage_proposals": int(triage.get("summary", {}).get("proposals", 0)),
        "actionable": len(actionable),
        "new_findings": int(ratchet.get("new_findings", 0)),
        "accepted_findings": int(ratchet.get("accepted_findings", 0)),
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "status": status,
        "strict": strict,
        "profile": profile,
        "summary": summary,
        "baseline": _relative(resolved_baseline, root),
        "triage": triage,
        "ratchet": ratchet,
        "policy": {
            "default_behavior": "read_only_report",
            "auto_install": False,
            "installer_apply_requires_explicit_operator_action": True,
            "git_hooks_are_advisory_by_default": True,
        },
    }
    if include_install_plan:
        report["install_plan"] = installer_plan(root, profile)
    return report


def format_human(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        f"dependency maintenance: {report.get('schema_version')}",
        f"  mode: {report.get('mode')}",
        f"  status: {report.get('status')}",
        f"  profile: {report.get('profile')}",
        f"  strict: {str(report.get('strict')).lower()}",
    ]
    if report.get("status") == "skipped":
        lines.append(f"  reason: {report.get('reason')}")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"  actionable: {summary.get('actionable', 0)}",
            f"  new_findings: {summary.get('new_findings', 0)}",
            f"  accepted_findings: {summary.get('accepted_findings', 0)}",
            f"  missing_from_manifest: {summary.get('coverage_missing_from_manifest', 0)}",
            f"  optional_lane_needed: {summary.get('coverage_optional_lane_needed', 0)}",
        ]
    )
    install = report.get("install_plan") or {}
    if install:
        command = " ".join(str(part) for part in install.get("command", []))
        lines.append("\ninstaller plan:")
        lines.append(f"  {command}")
        lines.append(f"  {install.get('note')}")

    ratchet = report.get("ratchet") or {}
    new = ratchet.get("new") or []
    if new:
        lines.append("\nnew actionable sample:")
        for row in new[:10]:
            lines.append(f"  - {row.get('action')}: {row.get('name')} ({row.get('kind')})")

    if report.get("status") == "warn":
        lines.append("\nwarning: dependency coverage drift exists; this is advisory unless strict mode is enabled.")
    elif report.get("status") == "block":
        lines.append("\nblocked: strict mode rejects unaccepted dependency coverage findings.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only dependency maintenance across install/update/git-hook flows.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--mode", choices=sorted(MODES), default="doctor", help="Calling surface.")
    parser.add_argument("--profile", default=os.environ.get("COS_DEPS_MAINTAIN_PROFILE", DEFAULT_PROFILE))
    parser.add_argument("--coverage-report", type=Path, help="Existing cos-deps-coverage-audit JSON report.")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", default=os.environ.get("COS_DEPS_RATCHET_STRICT") == "1")
    parser.add_argument("--no-install-plan", action="store_true")
    args = parser.parse_args(argv)

    skipped = os.environ.get("COS_DEPS_MAINTENANCE") == "0"
    try:
        report = build_maintenance_report(
            Path(args.root),
            args.mode,
            args.profile,
            coverage_report=args.coverage_report,
            baseline=args.baseline,
            strict=args.strict,
            include_install_plan=not args.no_install_plan,
            skipped=skipped,
        )
    except Exception as exc:  # hooks/setup must degrade gracefully
        if args.json:
            print(json.dumps({"schema_version": SCHEMA_VERSION, "status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"dependency maintenance: error: {exc}", file=sys.stderr)
        return 2 if args.strict else 0

    print(json.dumps(report, indent=2, sort_keys=True) if args.json else format_human(report), end="")
    return 2 if report.get("status") == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
