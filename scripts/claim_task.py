#!/usr/bin/env python3
# SCOPE: both
"""Acquire, release, and inspect task claims for multi-session agents.

Thin CLI wrapper around scripts/cos_task_claims.py (canonical API).
Canonical store: .cognitive-os/tasks/active-claims.json (ADR-116 §P1.1).

Previously delegated to lib/task_claim_ledger.py (deprecated shim).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cos_task_claims import (  # noqa: E402
    claim_task,
    project_dir as _project_dir,
    release_task,
)
from lib.project_paths import project_dir_from_args as _project_dir_from_args  # noqa: E402


def _project(args: argparse.Namespace) -> Path:
    # Support both lib.project_paths and cos_task_claims resolution for compat.
    try:
        return _project_dir_from_args(args)
    except Exception:
        return _project_dir(args)


def emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True))


def acquire(args: argparse.Namespace) -> int:
    project = _project(args)
    task = {
        "id": args.task_id,
        "expected_files": args.expected_file or [],
    }
    ok, result = claim_task(
        project,
        task,
        session=args.session_id,
        expected_files=args.expected_file or [],
        agent_id=args.agent_id,
        scope=args.scope or "",
        ttl_seconds=args.ttl_seconds,
    )
    # Emit TCL-compatible envelope so existing shell callers can parse it.
    if ok:
        envelope = {
            "status": "acquired",
            "task_id": result.get("task_id", args.task_id),
            "claim": result,
        }
        emit(envelope)
        return 0
    else:
        envelope = {
            "status": "blocked",
            "task_id": result.get("task_id", args.task_id),
            "held_by": {"session_id": result.get("held_by")},
        }
        emit(envelope)
        return 2


def release(args: argparse.Namespace) -> int:
    project = _project(args)
    result = release_task(project, args.task_id, session=args.session_id)
    envelope = {
        "status": "released" if result.get("updated") else "absent",
        "task_id": args.task_id,
    }
    emit(envelope)
    return 0


def status(args: argparse.Namespace) -> int:
    from scripts.cos_task_claims import prune_claims, normalize_claims, read_json
    project = _project(args)
    from scripts.cos_task_claims import claims_path as _claims_path
    data = prune_claims(project, normalize_claims(read_json(_claims_path(project), {"claims": []})))
    active = [c for c in data.get("claims", []) if c.get("status") == "active"]
    emit({"claims": active})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir")
    sub = parser.add_subparsers(dest="command", required=True)

    acq = sub.add_parser("acquire")
    acq.add_argument("task_id")
    acq.add_argument("--session-id", required=True)
    acq.add_argument("--agent-id", required=True)
    acq.add_argument("--expected-file", action="append")
    acq.add_argument("--scope")
    acq.add_argument("--ttl-seconds", type=int, default=1800)
    acq.set_defaults(func=acquire)

    rel = sub.add_parser("release")
    rel.add_argument("task_id")
    rel.add_argument("--session-id")
    rel.add_argument("--agent-id")
    rel.set_defaults(func=release)

    stat = sub.add_parser("status")
    stat.add_argument("--include-expired", action="store_true")
    stat.set_defaults(func=status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
