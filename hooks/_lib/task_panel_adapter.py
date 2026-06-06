#!/usr/bin/env python3
# SCOPE: both
"""Task Panel Adapter — mirrors COS task state to Claude Code's native UI.

Implements ADR-021 (vendor-agnostic state with provider adapters).

Reads canonical state from .cognitive-os/tasks/active-tasks.json and emits
additionalContext JSON that Claude Code adds to the agent's context window.
One-way sync: COS → Claude Code UI. The COS file remains the source of truth.

When running under Codex/Gemini/Cursor/Devin, other adapters handle the
same role. This file is specific to Claude Code.
"""

import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.harness_environment import is_claude_code as _is_claude_code


def _load_active_tasks(project_dir: Path) -> list[dict]:
    """Read active-tasks.json, return list of task dicts."""
    tasks_file = project_dir / ".cognitive-os" / "tasks" / "active-tasks.json"
    if not tasks_file.is_file():
        return []
    try:
        with open(tasks_file) as f:
            data = json.load(f)
        return data.get("tasks", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _format_for_claude_panel(tasks: list[dict]) -> str:
    """Format tasks as markdown suitable for Claude Code's context.

    Claude Code's native Task panel shows Agent + Bash tool calls, but not
    our orchestration layer (circuit breaker, workload scheduler, queue).
    This formatted block gives the agent visibility into that hidden state.

    Dedup: tasks with `toolUseId` are already emitted by hooks/_lib/task_bridge.py
    as "COS In-Progress with native Task panel link". We skip them here to
    avoid listing the same task twice in the orchestrator context.
    """
    if not tasks:
        return ""

    # Filter out tasks already emitted by task_bridge.py (those with toolUseId).
    tasks = [t for t in tasks if not t.get("toolUseId")]
    if not tasks:
        return ""

    by_status: dict[str, list[dict]] = {}
    for task in tasks:
        status = task.get("status", "unknown")
        by_status.setdefault(status, []).append(task)

    # Only emit if there is something actionable. Empty/completed-only state
    # produces noise with no signal.
    if not any(by_status.get(s) for s in ("in_progress", "queued", "failed")):
        return ""

    lines = ["## COS Task State (not visible in native Task panel)\n"]

    for status in ("in_progress", "queued", "failed"):
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"### {status.replace('_', ' ').title()} ({len(items)})")
        for t in items[:5]:
            desc = (t.get("description") or "")[:80]
            skill = t.get("skill_name", "")
            added = (t.get("added_at") or t.get("created_at", ""))[:16]
            prefix = f"[{skill}]" if skill else ""
            lines.append(f"- {prefix} {desc} ({added})")
        if len(items) > 5:
            lines.append(f"- ... and {len(items) - 5} more")
        lines.append("")

    return "\n".join(lines).strip()


def main() -> int:
    if not _is_claude_code():
        # Other providers have their own adapters
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    tasks = _load_active_tasks(project_dir)
    context = _format_for_claude_panel(tasks)

    if not context:
        return 0

    # Emit hookSpecificOutput with additionalContext for Claude Code
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
