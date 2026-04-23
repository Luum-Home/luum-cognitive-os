#!/usr/bin/env python3
# SCOPE: both
"""Consolidated helper for session-init.sh.

Replaces 3 separate python3 cold starts with a single invocation:
1. Read self-improve flag reason
2. Load user model from engram
3. Check work queue pending items

Reads env vars: COGNITIVE_OS_PROJECT_DIR, CODEX_PROJECT_DIR, CLAUDE_PROJECT_DIR,
SESSION_DIR, SELF_IMPROVE_FLAG
Writes to: SESSION_DIR/user-profile.txt
Outputs to stderr: self-improve reason, work queue warnings
Always exits 0 — failures are silent.
"""

import json
import os
import sys


def _emit_self_improve(flag_path: str) -> None:
    """Read self-improve flag file and emit reason to stderr."""
    if not os.path.isfile(flag_path):
        return
    try:
        with open(flag_path) as f:
            data = json.load(f)
        reason = data.get("reason", "KPIs below threshold")
    except Exception:
        reason = "KPIs below threshold"
    print(
        f"SELF-IMPROVE RECOMMENDED: {reason} — consider running /self-improve",
        file=sys.stderr,
    )


def _load_user_model(project_dir: str, session_dir: str) -> None:
    """Load user model from engram and write profile summary."""
    try:
        sys.path.insert(0, project_dir)
        from lib.user_model import UserModel

        model = UserModel.load_from_engram()
        if getattr(model, "preferences", None):
            profile = model.get_profile_summary()
            with open(os.path.join(session_dir, "user-profile.txt"), "w") as f:
                f.write(profile)
    except Exception:
        pass


def _check_work_queue(project_dir: str) -> None:
    """Check work queue for pending items from prior sessions."""
    try:
        sys.path.insert(0, project_dir)
        from lib.work_queue import WorkQueue

        queue_path = os.path.join(project_dir, ".cognitive-os", "work-queue.json")
        q = WorkQueue(queue_path=queue_path)
        pending = q.get_pending()
        if not pending:
            return
        print(
            f"\n=== WORK QUEUE: {len(pending)} pending task(s) from prior sessions ===",
            file=sys.stderr,
        )
        for t in pending[:5]:
            desc = t.get("description", "")[:80]
            added = t.get("added_at", "")[:19]
            print(f"  [{added}] {desc}", file=sys.stderr)
        if len(pending) > 5:
            print(
                f"  ... and {len(pending) - 5} more. Check .cognitive-os/work-queue.json",
                file=sys.stderr,
            )
        print("=== Consider resuming or clearing stale tasks ===\n", file=sys.stderr)
    except Exception:
        pass


def main() -> int:
    project_dir = (
        os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )
    session_dir = os.environ.get("SESSION_DIR", "")
    self_improve_flag = os.environ.get(
        "SELF_IMPROVE_FLAG",
        os.path.join(project_dir, ".cognitive-os", "metrics", ".self-improve-recommended"),
    )

    _emit_self_improve(self_improve_flag)

    if session_dir:
        _load_user_model(project_dir, session_dir)

    _check_work_queue(project_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
