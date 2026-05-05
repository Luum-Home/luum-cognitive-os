#!/usr/bin/env python3
# SCOPE: both
"""Local deterministic headless task admission proof for Phase 2 wiring.

This command does not invoke LLMs or mutate git state. It proves that real task
admission checks the ADR-091 safe-mode kill switch and, when publication
arguments are supplied, the protected-publication policy before recording a
minimal local outcome artifact.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.script_io import atomic_write_json

from cos_headless_publication import check_publication_policy  # noqa: E402
from cos_headless_safe_mode import read_state, resolve_project_dir  # noqa: E402

OUTCOME_DIR = Path(".cognitive-os") / "headless" / "tasks"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def current_branch(project_dir: Path) -> str:
    for args in (["branch", "--show-current"], ["rev-parse", "--abbrev-ref", "HEAD"]):
        try:
            result = subprocess.run(
                ["git", "-C", str(project_dir), *args],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        branch = result.stdout.strip()
        if result.returncode == 0 and branch and branch != "HEAD":
            return branch
    return "unknown"


def outcome_path(project_dir: Path, task_id: str) -> Path:
    safe_id = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in task_id).strip(".-")
    if not safe_id:
        safe_id = "task"
    return project_dir / OUTCOME_DIR / f"{safe_id}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", help="Project root; defaults like other Cognitive OS scripts.")
    parser.add_argument("--task-id", required=True, help="Stable local task identifier.")
    parser.add_argument("--description", default="", help="Optional human task description recorded in the outcome.")
    parser.add_argument("--actor-mode", choices=("interactive", "headless"), help="Actor mode for publication policy checks.")
    parser.add_argument("--publication-target", help="Optional requested publication target, e.g. main, patch, branch.")
    parser.add_argument("--landing-mode", default="none", choices=("none", "merge_queue", "human_approved"))
    parser.add_argument("--branch", help="Source branch for publication policy; defaults to current git branch.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def emit(payload: dict[str, Any], *, json_output: bool, error: bool = False) -> None:
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    stream = sys.stderr if error else sys.stdout
    print(f"cos-run-task: {payload.get('status')}: {payload.get('reason', payload.get('outcome_path', ''))}", file=stream)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)

    safe_state = read_state(project_dir)
    if not safe_state.admits_new_tasks:
        payload = {
            "ok": False,
            "status": "blocked",
            "reason": safe_state.reason or "headless safe mode blocks new task admission",
            "task_id": args.task_id,
            "safe_mode": safe_state.to_dict(),
        }
        emit(payload, json_output=args.json, error=True)
        return 2

    publication_decision = None
    if args.publication_target or args.actor_mode:
        if not args.publication_target or not args.actor_mode:
            payload = {
                "ok": False,
                "status": "error",
                "reason": "--publication-target and --actor-mode must be supplied together",
                "task_id": args.task_id,
            }
            emit(payload, json_output=args.json, error=True)
            return 2
        publication_decision = check_publication_policy(
            branch=args.branch or current_branch(project_dir),
            actor_mode=args.actor_mode,
            publication_target=args.publication_target,
            landing_mode=args.landing_mode,
        )
        if not publication_decision.allowed:
            payload = {
                "ok": False,
                "status": "blocked",
                "reason": publication_decision.reason,
                "task_id": args.task_id,
                "publication": asdict(publication_decision),
            }
            emit(payload, json_output=args.json, error=True)
            return 2

    path = outcome_path(project_dir, args.task_id)
    payload = {
        "ok": True,
        "status": "admitted",
        "task_id": args.task_id,
        "description": args.description,
        "admitted_at": utc_now(),
        "outcome_path": str(path),
        "safe_mode": safe_state.to_dict(),
        "publication": asdict(publication_decision) if publication_decision else None,
    }
    atomic_write_json(path, payload)
    emit(payload, json_output=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
