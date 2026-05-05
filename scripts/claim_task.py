#!/usr/bin/env python3
# SCOPE: both
"""Acquire, release, and inspect task claims for multi-session agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.task_claim_ledger import acquire_claim, list_claims, release_claim  # noqa: E402
from lib.project_paths import project_dir_from_args as project_dir


def emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True))


def acquire(args: argparse.Namespace) -> int:
    result = acquire_claim(
        project_dir(args),
        task_id=args.task_id,
        session_id=args.session_id,
        agent_id=args.agent_id,
        expected_files=args.expected_file or [],
        scope=args.scope or "",
        ttl_seconds=args.ttl_seconds,
    )
    emit(result.to_dict())
    return 2 if result.status == "blocked" else 0


def release(args: argparse.Namespace) -> int:
    result = release_claim(
        project_dir(args),
        task_id=args.task_id,
        session_id=args.session_id,
        agent_id=args.agent_id,
    )
    emit(result.to_dict())
    return 2 if result.status == "blocked" else 0


def status(args: argparse.Namespace) -> int:
    emit({"claims": list_claims(project_dir(args), include_expired=args.include_expired)})
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

