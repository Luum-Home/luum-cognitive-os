# SCOPE: os-only
"""Changelog generator from session and sprint data.

Reads session metadata, git context, task records, and cost events to produce
structured changelog objects for individual sessions and sprints.

Author: luum
Python 3.9+ compatible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Union


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SessionChangelog:
    """Changelog for a single coding session."""

    session_id: str
    date: str
    duration_minutes: float
    commits: List[dict]
    tasks_completed: List[str]
    decisions: List[str]
    files_changed_count: int
    cost_usd: float


@dataclass
class SprintChangelog:
    """Aggregated changelog across multiple sessions in a sprint."""

    sprint_id: str
    sessions: List[SessionChangelog]
    total_commits: int
    total_tasks: int
    total_cost: float
    features_completed: List[str]
    bugs_fixed: List[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    """Read a JSON file; return empty dict on any error."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _read_jsonl(path: Path) -> List[dict]:
    """Read a JSONL file; return empty list on any error."""
    try:
        lines = path.read_text().splitlines()
        result = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return result
    except Exception:
        return []


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp, returning UTC datetime."""
    # Handle trailing 'Z'
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return datetime.now(tz=timezone.utc)


def _duration_minutes(start_ts: str, end_ts: str) -> float:
    """Return the duration in minutes between two ISO timestamps."""
    try:
        start = _parse_iso(start_ts)
        end = _parse_iso(end_ts)
        delta = (end - start).total_seconds()
        return round(max(delta, 0) / 60.0, 2)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_session_changelog(project_dir: str, session_id: str) -> SessionChangelog:
    """Generate a SessionChangelog from on-disk session data.

    Args:
        project_dir: Root of the project (parent of .cognitive-os/).
        session_id: The session identifier.

    Returns:
        SessionChangelog populated from available files; zero/empty values
        are used when files are absent.
    """
    root = Path(project_dir)
    cos = root / ".cognitive-os"

    # --- meta.json -----------------------------------------------------------
    meta = _read_json(cos / "sessions" / session_id / "meta.json")
    date_str = meta.get("date") or meta.get("start_time", "")[:10] or ""
    start_time = meta.get("start_time", "")

    # --- git-context.json ---------------------------------------------------
    git_ctx = _read_json(cos / "sessions" / session_id / "git-context.json")
    commits: List[dict] = git_ctx.get("commits", [])
    files_added: int = git_ctx.get("files_added", 0)
    files_modified: int = git_ctx.get("files_modified", 0)
    files_changed_count: int = files_added + files_modified

    # --- active-tasks.json --------------------------------------------------
    tasks_data = _read_json(cos / "tasks" / "active-tasks.json")
    raw_tasks = tasks_data.get("tasks", [])
    if isinstance(raw_tasks, list):
        tasks_completed = [
            t.get("description", t.get("id", ""))
            for t in raw_tasks
            if isinstance(t, dict)
            and t.get("status") == "completed"
            and (not session_id or t.get("session_id", session_id) == session_id)
        ]
    else:
        tasks_completed = []

    # --- cost-events.jsonl --------------------------------------------------
    cost_events = _read_jsonl(cos / "metrics" / "cost-events.jsonl")
    session_costs = [
        e for e in cost_events
        if not session_id or e.get("session_id", session_id) == session_id
    ]
    cost_usd: float = sum(e.get("estimated_cost_usd", e.get("cost_usd", 0.0)) for e in session_costs)
    cost_usd = round(cost_usd, 6)

    # --- duration -----------------------------------------------------------
    last_ts = ""
    if session_costs:
        last_ts = session_costs[-1].get("timestamp", "")
    if start_time and last_ts:
        duration_minutes = _duration_minutes(start_time, last_ts)
    else:
        duration_minutes = 0.0

    # --- decisions (from engram-style or meta) ------------------------------
    decisions: List[str] = meta.get("decisions", [])

    return SessionChangelog(
        session_id=session_id,
        date=date_str,
        duration_minutes=duration_minutes,
        commits=commits,
        tasks_completed=tasks_completed,
        decisions=decisions,
        files_changed_count=files_changed_count,
        cost_usd=cost_usd,
    )


def generate_sprint_changelog(project_dir: str, sprint_id: str) -> SprintChangelog:
    """Generate a SprintChangelog by aggregating session changelogs.

    The function discovers sessions via:
    1. ``.cognitive-os/changelogs/{session_id}.md`` files, OR
    2. ``.cognitive-os/metrics/session-audit.jsonl`` entries matching the sprint.

    Args:
        project_dir: Root of the project.
        sprint_id: Sprint identifier (e.g. "2026-w15").

    Returns:
        SprintChangelog aggregated across all discovered sessions.
    """
    root = Path(project_dir)
    cos = root / ".cognitive-os"

    # Collect session IDs -------------------------------------------------
    session_ids: List[str] = []

    # Strategy 1: changelogs directory
    changelogs_dir = cos / "changelogs"
    if changelogs_dir.is_dir():
        for md_file in changelogs_dir.glob("*.md"):
            session_ids.append(md_file.stem)

    # Strategy 2: session-audit.jsonl
    audit_path = cos / "metrics" / "session-audit.jsonl"
    if audit_path.exists():
        for entry in _read_jsonl(audit_path):
            if entry.get("sprint_id") == sprint_id:
                sid = entry.get("session_id", "")
                if sid and sid not in session_ids:
                    session_ids.append(sid)

    # Build per-session changelogs ----------------------------------------
    sessions: List[SessionChangelog] = [
        generate_session_changelog(project_dir, sid) for sid in session_ids
    ]

    # Aggregate -----------------------------------------------------------
    total_commits = sum(len(s.commits) for s in sessions)
    total_tasks = sum(len(s.tasks_completed) for s in sessions)
    total_cost = round(sum(s.cost_usd for s in sessions), 6)

    features_completed: List[str] = []
    bugs_fixed: List[str] = []
    for s in sessions:
        for task in s.tasks_completed:
            if task.startswith("feat:"):
                features_completed.append(task)
            elif task.startswith("fix:"):
                bugs_fixed.append(task)

    return SprintChangelog(
        sprint_id=sprint_id,
        sessions=sessions,
        total_commits=total_commits,
        total_tasks=total_tasks,
        total_cost=total_cost,
        features_completed=features_completed,
        bugs_fixed=bugs_fixed,
    )


def format_changelog_md(changelog: Union[SessionChangelog, SprintChangelog]) -> str:
    """Format a changelog object to Markdown.

    Works for both SessionChangelog and SprintChangelog.

    Args:
        changelog: A SessionChangelog or SprintChangelog instance.

    Returns:
        Markdown-formatted string.
    """
    if isinstance(changelog, SessionChangelog):
        return _format_session_md(changelog)
    elif isinstance(changelog, SprintChangelog):
        return _format_sprint_md(changelog)
    else:
        raise TypeError(f"Unsupported changelog type: {type(changelog)}")


# ---------------------------------------------------------------------------
# Internal formatters
# ---------------------------------------------------------------------------


def _format_session_md(sc: SessionChangelog) -> str:
    lines: List[str] = [
        f"# Session Changelog: {sc.session_id}",
        "",
        f"**Date**: {sc.date}  ",
        f"**Duration**: {sc.duration_minutes} minutes  ",
        f"**Cost**: ${sc.cost_usd:.2f}  ",
        f"**Files changed**: {sc.files_changed_count}",
        "",
        f"## Commits ({len(sc.commits)})",
    ]
    for commit in sc.commits:
        sha = commit.get("sha", "")[:7] if commit.get("sha") else ""
        msg = commit.get("message", "")
        lines.append(f"- `{sha}` {msg}")
    if not sc.commits:
        lines.append("_No commits recorded._")

    lines += [
        "",
        f"## Tasks Completed ({len(sc.tasks_completed)})",
    ]
    for task in sc.tasks_completed:
        lines.append(f"- {task}")
    if not sc.tasks_completed:
        lines.append("_No tasks completed._")

    lines += [
        "",
        "## Decisions",
    ]
    for decision in sc.decisions:
        lines.append(f"- {decision}")
    if not sc.decisions:
        lines.append("_No decisions recorded._")

    return "\n".join(lines) + "\n"


def _format_sprint_md(sc: SprintChangelog) -> str:
    lines: List[str] = [
        f"# Sprint Changelog: {sc.sprint_id}",
        "",
        f"**Sessions**: {len(sc.sessions)}  ",
        f"**Total commits**: {sc.total_commits}  ",
        f"**Total tasks**: {sc.total_tasks}  ",
        f"**Total cost**: ${sc.total_cost:.2f}",
        "",
        "## Features Completed",
    ]
    for feat in sc.features_completed:
        lines.append(f"- {feat}")
    if not sc.features_completed:
        lines.append("_No features recorded._")

    lines += [
        "",
        "## Bugs Fixed",
    ]
    for bug in sc.bugs_fixed:
        lines.append(f"- {bug}")
    if not sc.bugs_fixed:
        lines.append("_No bugs recorded._")

    lines += [
        "",
        "## Session Breakdown",
        "| Session | Date | Commits | Tasks | Cost |",
        "|---------|------|---------|-------|------|",
    ]
    for s in sc.sessions:
        lines.append(
            f"| {s.session_id} | {s.date} | {len(s.commits)} | {len(s.tasks_completed)} | ${s.cost_usd:.2f} |"
        )
    if not sc.sessions:
        lines.append("| _none_ | — | — | — | — |")

    return "\n".join(lines) + "\n"
