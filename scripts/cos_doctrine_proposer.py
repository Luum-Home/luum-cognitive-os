#!/usr/bin/env python3
# SCOPE: both
"""Generate proposed doctrine amendments from control-plane evidence."""

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
from lib.doctrine_proposer import build_doctrine_proposals, build_report, write_markdown
from lib.self_improvement_loop import build_self_improvement_plan


def _safe_boring_dashboard(project_root: Path, profile: str) -> dict:
    try:
        return cos_boring_reliability.build_dashboard(profile, project_root)
    except Exception as exc:  # noqa: BLE001
        return {"status": "warn", "dashboard_error": str(exc)}


def _self_improvement_plan(project_root: Path, profile: str) -> dict:
    boring = _safe_boring_dashboard(project_root, profile)
    claim_signature = cos_claim_signature_audit.build_report(
        project_root / "manifests" / "primitive-lifecycle.yaml",
        project_root / "manifests" / "external-adoption-evidence.yaml",
    )
    return build_self_improvement_plan(
        boring_reliability=boring,
        claim_signature=claim_signature,
        profile=profile,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--profile", choices=["core", "team", "maintainer", "lab"], default="core")
    parser.add_argument("--write", action="store_true", help="write markdown proposal under docs/proposals")
    parser.add_argument("--json", action="store_true", help="accepted for CLI consistency; output is always JSON")
    args = parser.parse_args(argv)

    project_root = args.project_dir.resolve()
    boring = _safe_boring_dashboard(project_root, args.profile)
    plan = _self_improvement_plan(project_root, args.profile)
    report = build_report(
        project_root=project_root,
        boring_reliability=boring,
        self_improvement_plan=plan,
    )
    if args.write:
        proposals = build_doctrine_proposals(
            project_root=project_root,
            boring_reliability=boring,
            self_improvement_plan=plan,
        )
        report["written_to"] = str(write_markdown(project_root, proposals))

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
