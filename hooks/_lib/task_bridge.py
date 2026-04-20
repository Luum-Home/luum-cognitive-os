#!/usr/bin/env python3
# SCOPE: both
"""Task Bridge — correlates COS task_id with Claude Code tool_use_id.

This is the bidirectional link that makes COS-orchestrated tasks visible
in Claude Code's native Task panel.

How it works:
1. PreToolUse hook captures Claude Code's tool_use_id from the input JSON
2. It's stored alongside the COS task_id in active-tasks.json
3. When COS manages the task (queue, circuit breaker, etc.), it can now
   reference back to the native tool_use_id
4. additionalContext in hookSpecificOutput tells the model about queued
   tasks with their native IDs so it can drain the queue via Task tool

Usage:
    # From a hook (PreToolUse Agent):
    python3 task_bridge.py register --tool-use-id TUI --description "..."
    python3 task_bridge.py sync  # syncs queued → tool_use_id correlations
    python3 task_bridge.py panel-context  # emits hookSpecificOutput
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional


def _tasks_file() -> Path:
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    return project_dir / ".cognitive-os" / "tasks" / "active-tasks.json"


def _queue_file() -> Path:
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    return project_dir / ".cognitive-os" / "rate-limit-queue.json"


def _load_tasks() -> dict:
    path = _tasks_file()
    if not path.is_file():
        return {"version": 1, "tasks": [], "lastUpdated": ""}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "tasks": [], "lastUpdated": ""}


def _save_tasks(data: dict) -> None:
    path = _tasks_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_queue() -> list:
    path = _queue_file()
    if not path.is_file():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("queue", []) if isinstance(data, dict) else []
    except Exception:
        return []


def register(tool_use_id: str, description: str, task_id: Optional[str] = None) -> dict:
    """Register a COS task with its Claude Code tool_use_id correlation.

    Called by agent-prelaunch.sh with the tool_use_id from the hook input.
    Returns the task entry for further processing.
    """
    data = _load_tasks()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if not task_id:
        task_id = f"task-{int(time.time())}-{os.urandom(2).hex()}"

    # Check if this tool_use_id is already registered (dedup)
    for existing in data.get("tasks", []):
        if existing.get("toolUseId") == tool_use_id:
            return existing

    entry = {
        "id": task_id,
        "toolUseId": tool_use_id,
        "description": description[:500],
        "status": "in_progress",
        "launchedAt": now,
        "started_at": now,
        "pid": None,
        "completedAt": None,
        "outputSummary": None,
        "expectedOutputs": [],
        "checkCommand": None,
    }

    data.setdefault("tasks", []).append(entry)
    data["lastUpdated"] = now
    _save_tasks(data)
    return entry


def complete(tool_use_id: str, summary: str = "") -> bool:
    """Mark a task complete by its tool_use_id."""
    data = _load_tasks()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for task in data.get("tasks", []):
        if task.get("toolUseId") == tool_use_id:
            task["status"] = "completed"
            task["completedAt"] = now
            if summary:
                task["outputSummary"] = summary[:500]
            data["lastUpdated"] = now
            _save_tasks(data)
            return True
    return False


def panel_context() -> str:
    """Format COS orchestration state as additionalContext for Claude.

    This is what lets the agent SEE (and potentially act on) the state
    that's NOT in Claude Code's native Task panel:
    - Tasks queued by rate limiter
    - Tasks blocked by circuit breaker
    - In-progress tasks with COS-tracked metadata
    """
    tasks = _load_tasks().get("tasks", [])
    queue = _load_queue()

    # Classify tasks
    in_progress = [t for t in tasks if t.get("status") == "in_progress"]
    failed = [t for t in tasks if t.get("status") == "failed"]

    sections = []

    if queue:
        ready = [q for q in queue if q.get("ready_at_epoch", 0) <= time.time()]
        sections.append(f"## COS Rate-Limit Queue ({len(queue)} total, {len(ready)} ready)")
        if ready:
            sections.append("Ready for drain — invoke `/drain-queue` or Task tool:")
            for q in ready[:5]:
                desc = (q.get("description") or q.get("blocked_reason") or "")[:80]
                sections.append(f"- `{q.get('id', '?')}`: {desc}")
        else:
            next_ready = min(q.get("ready_at_epoch", 0) for q in queue) - time.time()
            sections.append(f"Next ready in {int(next_ready)}s")
        sections.append("")

    if in_progress:
        # Filter to tasks with toolUseId (so the model can correlate)
        with_bridge = [t for t in in_progress if t.get("toolUseId")]
        without_bridge = [t for t in in_progress if not t.get("toolUseId")]

        if with_bridge:
            sections.append(f"## COS In-Progress with native Task panel link ({len(with_bridge)})")
            for t in with_bridge[:5]:
                tui = t.get("toolUseId", "")[:8]
                desc = (t.get("description") or "")[:80]
                sections.append(f"- `{tui}`: {desc}")
            sections.append("")

        if without_bridge:
            sections.append(f"## COS In-Progress (no native link, queued or internal) ({len(without_bridge)})")
            for t in without_bridge[:5]:
                tid = (t.get("id") or "")[:12]
                desc = (t.get("description") or "")[:80]
                sections.append(f"- `{tid}`: {desc}")
            sections.append("")

    if failed:
        sections.append(f"## COS Failed tasks ({len(failed)})")
        for t in failed[:3]:
            desc = (t.get("description") or "")[:80]
            sections.append(f"- {desc}")
        sections.append("")

    return "\n".join(sections).strip()


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("register")
    r.add_argument("--tool-use-id", required=True)
    r.add_argument("--description", required=True)
    r.add_argument("--task-id", default=None)

    c = sub.add_parser("complete")
    c.add_argument("--tool-use-id", required=True)
    c.add_argument("--summary", default="")

    sub.add_parser("panel-context")

    args = p.parse_args()

    if args.cmd == "register":
        entry = register(args.tool_use_id, args.description, args.task_id)
        print(json.dumps(entry))
    elif args.cmd == "complete":
        ok = complete(args.tool_use_id, args.summary)
        print(json.dumps({"completed": ok}))
    elif args.cmd == "panel-context":
        ctx = panel_context()
        if ctx:
            # Emit as hookSpecificOutput so Claude Code injects it
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": ctx,
                }
            }))
    else:
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
