#!/usr/bin/env python3
# SCOPE: os-only
"""Run non-destructive recovery drills for WIP/snapshot safety."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "stash-reapply": ["python3", "-m", "pytest", "tests/integration/test_stash_reapply.py", "-q"],
    "snapshot-restore": ["python3", "-m", "pytest", "tests/integration/test_post_agent_snapshot_restore.py", "-q"],
    "wip-score": ["python3", "scripts/cos_wip_safety_score.py"],
}


def run(cmd: list[str], root: Path) -> dict[str, object]:
    proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False, timeout=120)
    return {"command": cmd, "returncode": proc.returncode, "stdout_tail": proc.stdout[-1000:], "stderr_tail": proc.stderr[-1000:]}


def build_report(scenario: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    scenarios = list(SCENARIOS) if scenario == "all" else [scenario]
    results: list[dict[str, Any]] = []
    for name in scenarios:
        if name not in SCENARIOS:
            results.append({"scenario": name, "returncode": 2, "stderr_tail": "unknown scenario"})
            continue
        item = run(SCENARIOS[name], root)
        item["scenario"] = name
        results.append(item)
    passed = sum(1 for item in results if item["returncode"] == 0)
    return {"status": "pass" if passed == len(results) else "fail", "passed": passed, "total": len(results), "results": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["all", *sorted(SCENARIOS)], default="wip-score")
    args = parser.parse_args(argv)
    report = build_report(args.scenario)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
