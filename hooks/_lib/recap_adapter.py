#!/usr/bin/env python3
# SCOPE: os-only
"""Recap Adapter — exposes COS session state to Claude Code's native /recap UI.

Implements ADR-021 (vendor-agnostic state with provider adapters).

Claude Code has a native /recap slash command that summarizes the current
session for the user. The Cognitive OS already maintains its own canonical
session state under .cognitive-os/sessions/{SESSION_ID}/ (backlog, summary,
metrics, learning notes). This adapter reads that canonical state and
emits additionalContext JSON so /recap shows COS-managed work alongside
Claude Code's native event log.

One-way sync: COS -> Claude Code UI. /recap output never overwrites the COS
state files; the .cognitive-os/sessions/ directory remains the source of truth.

When running under Codex/Gemini/Cursor/Windsurf, other adapters handle the
same role. This module is specific to Claude Code.

Used by hooks/recap-sync.sh on the Stop event.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.harness_environment import is_claude_code as _is_claude_code


def _resolve_session_id(project_dir: Path) -> str | None:
    """Find the active session ID for this process.

    Tries (in order): COGNITIVE_OS_SESSION_ID env var, PID-based marker file,
    most recently modified session directory.
    """
    sid = os.environ.get("COGNITIVE_OS_SESSION_ID")
    if sid:
        return sid

    sessions_dir = project_dir / ".cognitive-os" / "sessions"
    if not sessions_dir.is_dir():
        return None

    pid_marker = sessions_dir / f".current-session-{os.getpid()}"
    if pid_marker.is_file():
        try:
            return pid_marker.read_text().strip() or None
        except Exception:
            pass

    # Fallback: most recently touched session directory (excluding hidden)
    candidates = [
        p for p in sessions_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


def _read_text(path: Path, max_chars: int = 4000) -> str:
    """Read a text file safely, truncating to max_chars."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n... (truncated)"
    return text


def _load_backlog(session_dir: Path) -> str:
    """Read the session backlog markdown if present."""
    backlog = session_dir / "backlog.md"
    if not backlog.is_file():
        return ""
    return _read_text(backlog, max_chars=2000)


def _load_summary(session_dir: Path) -> str:
    """Read the most recent session summary markdown if present."""
    for name in ("summary.md", "session-summary.md", "wrapup.md"):
        candidate = session_dir / name
        if candidate.is_file():
            return _read_text(candidate, max_chars=2000)
    return ""


def _load_metrics(session_dir: Path) -> dict:
    """Aggregate quick counts from session metrics, if any."""
    metrics_dir = session_dir / "metrics"
    if not metrics_dir.is_dir():
        return {}
    counts: dict[str, int] = {}
    for jl in metrics_dir.glob("*.jsonl"):
        try:
            with open(jl, "r", encoding="utf-8") as fh:
                for _ in fh:
                    counts[jl.stem] = counts.get(jl.stem, 0) + 1
        except Exception:
            continue
    return counts


def _load_active_tasks(project_dir: Path, session_id: str) -> list[dict]:
    """Read tasks from this session out of active-tasks.json."""
    tasks_file = project_dir / ".cognitive-os" / "tasks" / "active-tasks.json"
    if not tasks_file.is_file():
        return []
    try:
        with open(tasks_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return []
    tasks = data.get("tasks", []) if isinstance(data, dict) else []
    # Best-effort filter to current session; if no session_id field, include all
    return [
        t for t in tasks
        if not t.get("session_id") or t.get("session_id") == session_id
    ]


def _format_recap(
    session_id: str,
    summary: str,
    backlog: str,
    metrics: dict,
    tasks: list[dict],
) -> str:
    """Compose the markdown block injected into Claude Code's /recap context."""
    lines: list[str] = []
    lines.append("## COS Session Recap")
    lines.append(f"_Source: `.cognitive-os/sessions/{session_id}/` (canonical)_")
    lines.append("")

    if summary:
        lines.append("### Summary")
        lines.append(summary.strip())
        lines.append("")

    if tasks:
        completed = [t for t in tasks if t.get("status") == "completed"]
        in_progress = [t for t in tasks if t.get("status") == "in_progress"]
        failed = [t for t in tasks if t.get("status") in ("failed", "lost")]
        lines.append("### Tasks This Session")
        lines.append(
            f"- Completed: {len(completed)}  "
            f"In progress: {len(in_progress)}  "
            f"Failed/lost: {len(failed)}"
        )
        for t in completed[:5]:
            desc = (t.get("description") or "")[:80]
            lines.append(f"  - [done] {desc}")
        for t in in_progress[:3]:
            desc = (t.get("description") or "")[:80]
            lines.append(f"  - [active] {desc}")
        lines.append("")

    if metrics:
        lines.append("### Metrics")
        for name, count in sorted(metrics.items()):
            lines.append(f"- `{name}`: {count} entries")
        lines.append("")

    if backlog:
        lines.append("### Pending Backlog")
        lines.append(backlog.strip())
        lines.append("")

    if len(lines) <= 3:
        # Only the header survived — nothing useful to report.
        return ""

    return "\n".join(lines).rstrip()


def build_recap_context(project_dir: Path) -> str:
    """Public helper: assemble the recap markdown for the active session.

    Returns an empty string if no session state is available.
    """
    session_id = _resolve_session_id(project_dir)
    if not session_id:
        return ""

    session_dir = project_dir / ".cognitive-os" / "sessions" / session_id
    if not session_dir.is_dir():
        return ""

    summary = _load_summary(session_dir)
    backlog = _load_backlog(session_dir)
    metrics = _load_metrics(session_dir)
    tasks = _load_active_tasks(project_dir, session_id)

    return _format_recap(session_id, summary, backlog, metrics, tasks)


def main() -> int:
    if not _is_claude_code():
        # Other providers have their own adapters
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    context = build_recap_context(project_dir)
    if not context:
        return 0

    # Emit hookSpecificOutput with additionalContext for Claude Code /recap
    output = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
