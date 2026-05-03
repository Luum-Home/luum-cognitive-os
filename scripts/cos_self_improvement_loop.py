#!/usr/bin/env python3
# SCOPE: both
"""Headless propose-only self-improvement loop for Cognitive OS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cos_boring_reliability
import cos_claim_signature_audit
from lib.self_improvement_loop import build_self_improvement_plan, write_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(PROJECT_ROOT))
    parser.add_argument("--profile", choices=["core", "team", "maintainer", "lab"], default="core")
    parser.add_argument("--mode", choices=["propose"], default="propose")
    parser.add_argument("--write", action="store_true", help="write the proposal plan to .cognitive-os/improvements/proposals")
    parser.add_argument("--json", action="store_true", help="accepted for CLI consistency; output is always JSON")
    args = parser.parse_args(argv)

    project_root = Path(args.project_dir).resolve()
    boring = cos_boring_reliability.build_dashboard(args.profile, project_root)
    claim_signature = cos_claim_signature_audit.build_report(
        project_root / "manifests" / "primitive-lifecycle.yaml",
        project_root / "manifests" / "external-adoption-evidence.yaml",
    )
    plan = build_self_improvement_plan(
        boring_reliability=boring,
        claim_signature=claim_signature,
        profile=args.profile,
    )

    if args.write:
        plan["written_to"] = str(write_plan(project_root, plan))

    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
