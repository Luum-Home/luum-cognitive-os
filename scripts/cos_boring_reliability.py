#!/usr/bin/env python3
# SCOPE: both
"""Single boring-reliability dashboard for Cognitive OS."""
from __future__ import annotations

import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cos_adoption_profile
import cos_default_visible_reducer
import cos_false_positive_ledger
import cos_preamble_budget
import cos_wip_safety_score
import runtime_hook_reality
import silent_failure_audit
import session_start_budget



def dispatch_metrics_evidence(root: Path) -> dict[str, Any]:
    dispatch_path = root / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
    history_path = root / ".cognitive-os" / "metrics" / "task-history.jsonl"
    dispatch_bytes = dispatch_path.stat().st_size if dispatch_path.exists() else 0
    history_bytes = history_path.stat().st_size if history_path.exists() else 0
    status = "pass" if dispatch_bytes > 0 and history_bytes > 0 else "warn"
    return {
        "status": status,
        "llm_dispatch_bytes": dispatch_bytes,
        "task_history_bytes": history_bytes,
        "repair_command": "scripts/cos-dispatch-smoke --json",
    }

def readiness_summary(root: Path) -> dict[str, Any]:
    proc = subprocess.run(["python3", "scripts/cos_architecture_readiness.py", "--json"], cwd=root, text=True, capture_output=True, check=False)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "fail", "error": proc.stderr[-1000:]}
    return {"status": report.get("status"), "pass": report.get("pass_count"), "warn": report.get("warn_count"), "fail": report.get("fail_count"), "returncode": proc.returncode}


def build_dashboard(profile: str = "core", root: Path = REPO_ROOT) -> dict[str, Any]:
    runtime = runtime_hook_reality.build_report(project_root=root)
    adoption = cos_adoption_profile.build_profile(profile)
    preamble = cos_preamble_budget.build_budget(profile, root)
    reducer = cos_default_visible_reducer.build_recommendations()
    false_positive = cos_false_positive_ledger.build_report(root / ".cognitive-os" / "metrics")
    wip = cos_wip_safety_score.build_score(root)
    silent = silent_failure_audit.build_report(root, root / "hooks", root / "manifests" / "silent-failure-allowlist.yaml")
    session_budget = session_start_budget.build_report(profile, root)
    dispatch_evidence = dispatch_metrics_evidence(root)
    readiness = readiness_summary(root)
    status_items = [runtime["summary"]["status"], adoption["status"], preamble["status"], wip["status"], silent["status"], session_budget["status"], dispatch_evidence["status"], readiness["status"]]
    overall = "fail" if "fail" in status_items else ("warn" if "warn" in status_items else "pass")
    return {
        "status": overall,
        "profile": profile,
        "runtime_reality": runtime["summary"],
        "adoption_profile": {k: adoption[k] for k in ("status", "primitive_count", "hook_count", "default_visible_count", "blocking_count")},
        "preamble_budget": preamble,
        "default_visible_reducer": {"status": reducer["status"], "recommendation_count": reducer["recommendation_count"], "recommendations": reducer["recommendations"][:10]},
        "false_positive_ledger": false_positive,
        "wip_safety": wip,
        "session_start_budget": {
            "status": session_budget["status"],
            "profile": session_budget["profile"],
            "session_start_hook_count": session_budget["session_start_hook_count"],
            "counts_by_tier": session_budget["counts_by_tier"],
            "budget": session_budget["budget"],
            "findings": session_budget["findings"],
        },
        "silent_failure_audit": {
            "status": silent["status"],
            "file_count": silent["file_count"],
            "occurrence_count": silent["occurrence_count"],
            "fail_count": silent["fail_count"],
            "warn_count": silent["warn_count"],
            "counts_by_degradation_class": silent.get("counts_by_degradation_class", {}),
            "legacy_audited_count": silent.get("legacy_audited_count", 0),
        },
        "dispatch_metrics_evidence": dispatch_evidence,
        "readiness": readiness,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["core", "team", "maintainer", "lab"], default="core")
    args = parser.parse_args(argv)
    report = build_dashboard(args.profile)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
