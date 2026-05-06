#!/usr/bin/env python3
# SCOPE: both
"""Acquire, inspect, renew, and release ADR-182 branch ownership locks."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.branch_lock import acquire, holder, release, release_all_for_session, renew  # noqa: E402


def project_dir(args: argparse.Namespace) -> Path:
    return Path(args.project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()


def current_branch(project: Path) -> str:
    try:
        return subprocess.check_output(["git", "branch", "--show-current"], cwd=str(project), text=True, stderr=subprocess.DEVNULL).strip() or "detached"
    except Exception:
        return "detached"


def session_id(args: argparse.Namespace) -> str:
    return args.session_id or os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--branch", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("holder")
    acq = sub.add_parser("acquire")
    acq.add_argument("--ttl-seconds", type=int, default=14_400)
    ren = sub.add_parser("renew")
    ren.add_argument("--ttl-seconds", type=int, default=14_400)
    sub.add_parser("release")
    sub.add_parser("release-all")
    args = parser.parse_args()
    project = project_dir(args)
    branch = args.branch or current_branch(project)
    sid = session_id(args)

    if args.cmd == "holder":
        row = holder(project, branch)
        print(json.dumps({"holder": row}, sort_keys=True) if args.json else (json.dumps(row, sort_keys=True) if row else ""))
        return 0
    if args.cmd == "acquire":
        result = acquire(project, branch=branch, session_id=sid, pid=os.getpid(), worktree=project, ttl_seconds=args.ttl_seconds)
        print(json.dumps(result, sort_keys=True) if args.json else result["status"])
        return 0 if result["status"] == "acquired" else 2
    if args.cmd == "renew":
        ok = renew(project, branch=branch, session_id=sid, ttl_seconds=args.ttl_seconds)
        print(json.dumps({"ok": ok}, sort_keys=True) if args.json else ("renewed" if ok else "not-held"))
        return 0 if ok else 2
    if args.cmd == "release":
        ok = release(project, branch=branch, session_id=sid)
        print(json.dumps({"ok": ok}, sort_keys=True) if args.json else ("released" if ok else "not-held"))
        return 0 if ok else 2
    if args.cmd == "release-all":
        count = release_all_for_session(project, session_id=sid)
        print(json.dumps({"released": count}, sort_keys=True) if args.json else str(count))
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
