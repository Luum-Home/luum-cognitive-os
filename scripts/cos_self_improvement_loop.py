#!/usr/bin/env python3
# SCOPE: os-only
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

import cos_claim_signature_audit
import cos_demotion_loop_audit
import cos_false_positive_ledger
import cos_manifest_tier_claim_audit
import silent_failure_audit
from lib.self_improvement_loop import build_self_improvement_plan, write_plan


def build_self_improvement_inputs(project_root: Path) -> dict:
    """Build only the audit slices consumed by the proposal normalizer.

    `cos_boring_reliability.build_dashboard()` is intentionally broad for a
    human dashboard. The self-improvement CLI only needs the proposal-producing
    slices, so keep this hot path small enough for unit and release lanes.
    """

    return {
        "demotion_loop": cos_demotion_loop_audit.build_report(
            project_root / "manifests" / "primitive-lifecycle.yaml"
        ),
        "false_positive_ledger": cos_false_positive_ledger.build_report(
            project_root / ".cognitive-os" / "metrics"
        ),
        "manifest_tier_claims": cos_manifest_tier_claim_audit.build_report(
            project_root / "manifests" / "primitive-lifecycle.yaml"
        ),
        "silent_failure_audit": silent_failure_audit.build_report(
            project_root,
            project_root / "hooks",
            project_root / "manifests" / "silent-failure-allowlist.yaml",
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(PROJECT_ROOT))
    parser.add_argument("--profile", choices=["core", "team", "maintainer", "lab"], default="core")
    parser.add_argument("--mode", choices=["propose"], default="propose")
    parser.add_argument("--write", action="store_true", help="write the proposal plan to .cognitive-os/improvements/proposals")
    parser.add_argument("--json", action="store_true", help="accepted for CLI consistency; output is always JSON")
    args = parser.parse_args(argv)

    project_root = Path(args.project_dir).resolve()
    boring = build_self_improvement_inputs(project_root)
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
