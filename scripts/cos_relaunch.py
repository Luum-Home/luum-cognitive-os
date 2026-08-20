#!/usr/bin/env python3
# SCOPE: os-only
"""cos_relaunch — the only code in this repo that can start a session by itself.

It is deliberately small, and it re-checks everything the Stop hook already
checked. Not because the hook is untrusted, but because this file is the one
whose bug spends the operator's quota: a guard that lives only in the caller
is a guard that a future second caller will not have.

Order of operations, and none of it is negotiable:

  1. re-read the arm file — absent → exit, having launched nothing;
  2. re-run the fuses;
  3. reserve a slot in the counter under an exclusive lock (check and
     increment in one transaction, or two concurrent Stop hooks both pass a
     cap of one);
  4. only then build the child environment and spawn.

The child is spawned detached and its PID is written to the decision log. This
process never signals it, never waits on it, and never kills it. If a run has
to be stopped, the operator has the PID and makes that call.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cos_lib.session_lineage import (  # noqa: E402
    MODE_SPAWN,
    FuseLimits,
    RelaunchDecision,
    child_env,
    current_depth,
    default_store,
    evaluate_relaunch,
    resolve_root,
)


def relaunch(
    project_dir: Path,
    *,
    session_id: str,
    goal_id: str,
    prompt: str,
    consecutive_no_progress: int = 0,
    limits: FuseLimits | None = None,
    dry_run: bool = False,
) -> RelaunchDecision:
    store = default_store(project_dir)

    decision = evaluate_relaunch(
        store,
        session_id=session_id,
        goal_id=goal_id,
        consecutive_no_progress=consecutive_no_progress,
        limits=limits,
    )
    if not decision.allowed:
        store.record_decision(decision)
        return decision

    root_id = resolve_root(session_id)
    lim = limits or FuseLimits()
    reserved, why, counts = store.reserve_slot(root_id, session_id, lim)
    if not reserved:
        decision.allowed = False
        decision.fuse = "counter-race"
        decision.reason = why
        store.record_decision(decision)
        return decision

    decision.total_used = counts["total"]
    decision.width_used = counts["width"]

    env = dict(os.environ)
    env.update(child_env(
        parent_session_id=session_id,
        root_id=root_id,
        parent_depth=current_depth(),
        goal_id=goal_id,
    ))

    # The arm file, not the caller, has the last word on spawning. A caller
    # that forgot --dry-run must not be able to start a process the operator
    # only armed for dry-run.
    if dry_run or store.arm_mode() != MODE_SPAWN:
        decision.reason += (
            f" | mode={store.arm_mode()}: slot reserved, nothing spawned"
        )
        store.record_decision(decision)
        return decision

    claude = os.environ.get("CLAUDE_CODE_PATH", "claude")
    cmd = [claude, "-p", prompt]
    log_dir = store.base_dir / "child-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"gen{decision.child_depth}-{stamp}.log"

    try:
        with open(log_path, "wb") as log:
            proc = subprocess.Popen(
                cmd, cwd=str(project_dir), env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        decision.reason += f" | spawned pid={proc.pid} log={log_path}"
    except Exception as exc:  # noqa: BLE001
        decision.allowed = False
        decision.fuse = "spawn-error"
        decision.reason = f"spawn failed: {exc} (slot already consumed, on purpose)"

    store.record_decision(decision)
    return decision


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cos_relaunch")
    p.add_argument("--project-dir", default=None)
    p.add_argument("--session-id", required=True)
    p.add_argument("--goal-id", default="")
    p.add_argument("--prompt", default="")
    p.add_argument("--no-progress", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    project_dir = Path(
        args.project_dir
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or _ROOT
    )
    prompt = args.prompt or (
        f"Continue goal {args.goal_id}. Read the goal state under "
        f".cognitive-os/goals/ and submit an evidence packet with "
        f"scripts/cos-goal evaluate."
    )
    decision = relaunch(
        project_dir,
        session_id=args.session_id,
        goal_id=args.goal_id,
        prompt=prompt,
        consecutive_no_progress=args.no_progress,
        dry_run=args.dry_run,
    )
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0 if decision.allowed else 1


if __name__ == "__main__":
    sys.exit(main())
