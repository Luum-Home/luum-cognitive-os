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
    readiness = readiness_summary(root)
    status_items = [runtime["summary"]["status"], adoption["status"], preamble["status"], wip["status"], readiness["status"]]
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
