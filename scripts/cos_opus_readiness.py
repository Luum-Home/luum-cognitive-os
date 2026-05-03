#!/usr/bin/env python3
# SCOPE: both
"""Opus objection readiness report for Cognitive OS governance.

This command converts the Opus critique into a concrete gate report. It is not a
marketing score; warnings are intentionally visible so governance can be demoted,
wired, or reduced when it does not earn its cost.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cos_governance_roi
import primitive_lifecycle

REPO_ROOT = SCRIPT_DIR.parents[0]
REQUIRED_RUNTIME_PRIMITIVES = {
    "branch_writer_lease": ["scripts/cos_branch_lease.py", "scripts/cos-branch-lease"],
    "headless_safe_mode": ["scripts/cos_headless_safe_mode.py", "scripts/cos-headless-safe-mode"],
    "headless_publication": ["scripts/cos_headless_publication.py", "scripts/cos-headless-publication"],
}
WIRE_GAPS = [
    {
        "id": "branch-lease-prelaunch-wiring",
        "severity": "warn",
        "message": "branch writer lease exists but is not yet enforced by agent prelaunch/governed-agent flow",
        "phase": "Phase 2",
    },
    {
        "id": "headless-safe-mode-run-task-wiring",
        "severity": "warn",
        "message": "headless safe-mode exists but is not yet wired into cos run-task / worker admission",
        "phase": "Phase 2",
    },
    {
        "id": "headless-publication-flow-wiring",
        "severity": "warn",
        "message": "protected-publication checker exists but is not yet wired into real headless publication orchestration",
        "phase": "Phase 2",
    },
    {
        "id": "primitive-demotion-gate",
        "severity": "warn",
        "message": "ROI/friction data does not yet automatically propose lifecycle demotions",
        "phase": "Phase 1",
    },
]


@dataclass(frozen=True)
class Check:
    id: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def run_git_stash_list(root: Path) -> list[str]:
    result = subprocess.run(["git", "stash", "list"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return [f"<error:{result.stderr.strip()}>"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def check_repo_hygiene(root: Path) -> Check:
    stashes = run_git_stash_list(root)
    markers = sorted(str(path.relative_to(root)) for path in (root / ".cognitive-os" / "runtime").glob("pre-agent-snapshot-*.json"))
    status = "pass" if not stashes and not markers else "fail"
    return Check(
        id="repo-hygiene",
        status=status,
        message="no stashes or pre-agent snapshot markers" if status == "pass" else "stash/snapshot residue can hide or lose WIP",
        details={"stash_count": len(stashes), "marker_count": len(markers), "markers": markers},
    )


def check_adoption_tiers(root: Path) -> Check:
    result = subprocess.run(
        ["python3", "scripts/render_adoption_tiers.py", "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return Check(
        id="adoption-tiers-derived",
        status="pass" if result.returncode == 0 else "fail",
        message="adoption tiers are derived and in sync" if result.returncode == 0 else "adoption tiers doc is stale",
        details={"stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
    )


def check_lifecycle_manifest(root: Path) -> Check:
    report = primitive_lifecycle.build_report(root / "manifests" / "primitive-lifecycle.yaml")
    return Check(
        id="primitive-lifecycle-manifest",
        status="pass" if report["valid"] else "fail",
        message="primitive lifecycle manifest is valid" if report["valid"] else "primitive lifecycle manifest has findings",
        details=report,
    )


def check_roi(root: Path, window_hours: int) -> Check:
    report = cos_governance_roi.build_report(root, window_hours)
    roi = report["roi"]
    status = "pass" if roi["status"] == "positive" else "warn"
    return Check(
        id="governance-roi",
        status=status,
        message="governance ROI is non-negative in the selected window" if status == "pass" else "governance ROI is negative; demotion/reduction required",
        details={"roi": roi, "recommendations": report.get("recommendations", [])},
    )


def check_runtime_primitives(root: Path) -> Check:
    missing: dict[str, list[str]] = {}
    for primitive_id, rel_paths in REQUIRED_RUNTIME_PRIMITIVES.items():
        absent = [rel for rel in rel_paths if not (root / rel).exists()]
        if absent:
            missing[primitive_id] = absent
    return Check(
        id="runtime-safety-primitives-present",
        status="pass" if not missing else "fail",
        message="branch lease, safe-mode, and protected-publication primitives exist" if not missing else "required runtime-safety primitive files are missing",
        details={"missing": missing, "required": REQUIRED_RUNTIME_PRIMITIVES},
    )


def check_wiring_gaps() -> Check:
    return Check(
        id="known-wiring-gaps",
        status="warn" if WIRE_GAPS else "pass",
        message="known phase gaps remain visible" if WIRE_GAPS else "no known wiring gaps",
        details={"gaps": WIRE_GAPS},
    )


def build_report(root: Path, window_hours: int) -> dict[str, Any]:
    checks = [
        check_repo_hygiene(root),
        check_adoption_tiers(root),
        check_lifecycle_manifest(root),
        check_roi(root, window_hours),
        check_runtime_primitives(root),
        check_wiring_gaps(),
    ]
    fail_count = sum(1 for check in checks if check.status == "fail")
    warn_count = sum(1 for check in checks if check.status == "warn")
    pass_count = sum(1 for check in checks if check.status == "pass")
    score = round((pass_count / len(checks)) * 100) if checks else 0
    return {
        "project": str(root),
        "window_hours": window_hours,
        "score": score,
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "checks": [asdict(check) for check in checks],
        "next_phases": [
            "Phase 1: friction budget and demotion gate",
            "Phase 2: wire branch lease, safe-mode, and protected-publication into real flows",
            "Phase 3: active surface reduction by distribution/profile",
            "Phase 4: production border-case suite",
            "Phase 5: product packaging proof",
        ],
    }


def print_human(report: dict[str, Any]) -> None:
    print("COS Opus Readiness")
    print(f"status: {report['status']} score={report['score']} pass={report['pass_count']} warn={report['warn_count']} fail={report['fail_count']}")
    for check in report["checks"]:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[check["status"]]
        print(f"- {marker} {check['id']}: {check['message']}")
    if report["status"] != "pass":
        print("next phases:")
        for phase in report["next_phases"]:
            print(f"- {phase}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(REPO_ROOT))
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.project_dir).resolve(), args.window_hours)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report["fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
