# SCOPE: both
"""Cross-cutting audit ID for linking metrics across sessions, sprints, and changes."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class AuditContext:
    session_id: str
    sprint_id: str
    change_id: str
    branch: str


def _read_text(path: Path) -> str:
    """Return file contents stripped, or '' if missing/unreadable."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _git_branch(project_dir: str) -> str:
    """Return current git branch or '' on error."""
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _extract_sprint_id(yaml_content: str) -> str:
    """
    Extract the sprint_id value from sprint-status.yaml content using regex.

    Matches lines like:
        sprint_id: "2026-w15"
        sprint_id: 2026-w15
    """
    match = re.search(r'sprint_id\s*:\s*["\']?([^\s"\']+)["\']?', yaml_content)
    if match:
        return match.group(1)
    return ""


def get_current_audit_context(
    project_dir: str, session_id: str = ""
) -> AuditContext:
    """
    Build an AuditContext from environment and project state.

    Sources:
    - session_id: parameter > COGNITIVE_OS_SESSION_ID env var > ""
    - sprint_id:  .cognitive-os/workflows/state/sprint-status.yaml  (regex, no yaml dep)
    - change_id:  .cognitive-os/pipeline-state/current-change.txt
    - branch:     git rev-parse --abbrev-ref HEAD
    """
    # session_id
    resolved_session = session_id or os.environ.get("COGNITIVE_OS_SESSION_ID", "")

    # sprint_id
    sprint_file = (
        Path(project_dir)
        / ".cognitive-os"
        / "workflows"
        / "state"
        / "sprint-status.yaml"
    )
    sprint_content = _read_text(sprint_file)
    sprint_id = _extract_sprint_id(sprint_content)

    # change_id
    change_file = (
        Path(project_dir)
        / ".cognitive-os"
        / "pipeline-state"
        / "current-change.txt"
    )
    change_id = _read_text(change_file)

    # branch
    branch = _git_branch(project_dir)

    return AuditContext(
        session_id=resolved_session,
        sprint_id=sprint_id,
        change_id=change_id,
        branch=branch,
    )


def enrich_jsonl_entry(entry: dict, ctx: AuditContext) -> dict:
    """
    Add audit fields to a JSONL entry dict.

    Only adds fields that are not already present (non-destructive).
    Mutates the dict in place and returns it.
    """
    for key, value in [
        ("session_id", ctx.session_id),
        ("sprint_id", ctx.sprint_id),
        ("change_id", ctx.change_id),
        ("branch", ctx.branch),
    ]:
        if key not in entry:
            entry[key] = value
    return entry


def stamp_active_task(task: dict, ctx: AuditContext) -> dict:
    """
    Enrich a task dict with audit fields and an audit_timestamp.

    Non-destructive: existing fields are never overwritten.
    Mutates the dict in place and returns it.
    """
    enrich_jsonl_entry(task, ctx)
    if "audit_timestamp" not in task:
        task["audit_timestamp"] = datetime.now(timezone.utc).isoformat()
    return task
