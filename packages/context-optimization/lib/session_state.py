# SCOPE: both
# scope: both
"""Session State Persistence — survives compaction and crashes.

Manages `.cognitive-os/session-state.json` so a new session can recover
knowledge of running agents, pending tasks, and progress from the
previous session. Python 3.9+ compatible, stdlib only.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Default location relative to project root
_DEFAULT_STATE_DIR = ".cognitive-os"
_STATE_FILENAME = "session-state.json"


def _state_path(project_dir: Optional[str] = None) -> str:
    """Resolve absolute path to the session-state.json file."""
    base = project_dir or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return os.path.join(base, _DEFAULT_STATE_DIR, _STATE_FILENAME)


def _now_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _empty_state(session_id: str = "") -> Dict[str, Any]:
    """Return a blank state structure."""
    return {
        "session_id": session_id,
        "started_at": _now_iso(),
        "last_checkpoint": _now_iso(),
        "checkpoint_note": "",
        "agents": [],
        "pending_tasks": [],
        "completed_tasks": [],
        "stats": {},
    }


def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically via temp file + rename to prevent corruption."""
    dir_name = os.path.dirname(path)
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp", prefix=".session-state-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_state(project_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load the last persisted session state, or None if no state file exists.

    Args:
        project_dir: Project root directory. Falls back to CLAUDE_PROJECT_DIR or cwd.

    Returns:
        Parsed state dict, or None if the file does not exist or is invalid JSON.
    """
    path = _state_path(project_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        # Basic structural validation
        if not isinstance(data, dict) or "session_id" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def save_state(
    session_id: str,
    agents: Optional[List[Dict[str, Any]]] = None,
    pending_tasks: Optional[List[str]] = None,
    checkpoint_note: str = "",
    stats: Optional[Dict[str, Any]] = None,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a full session state snapshot.

    Args:
        session_id: Unique session identifier.
        agents: List of agent dicts (id, description, status, files_expected, files_created).
        pending_tasks: List of pending task descriptions.
        checkpoint_note: Human-readable note about current progress.
        stats: Arbitrary stats dict (tests_passed, commits, etc.).
        project_dir: Project root directory.

    Returns:
        The state dict that was written.
    """
    # Preserve existing completed_tasks if updating an existing state
    existing = load_state(project_dir)
    completed_tasks: List[str] = []
    if existing is not None and existing.get("session_id") == session_id:
        completed_tasks = existing.get("completed_tasks", [])

    state: Dict[str, Any] = {
        "session_id": session_id,
        "started_at": existing["started_at"] if existing and existing.get("session_id") == session_id else _now_iso(),
        "last_checkpoint": _now_iso(),
        "checkpoint_note": checkpoint_note,
        "agents": agents or [],
        "pending_tasks": pending_tasks or [],
        "completed_tasks": completed_tasks,
        "stats": stats or {},
    }
    _atomic_write(_state_path(project_dir), state)
    return state


def record_agent(
    agent_id: str,
    description: str,
    files_expected: Optional[List[str]] = None,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new agent entry to the current state.

    Args:
        agent_id: Unique identifier for the agent.
        description: What the agent is doing.
        files_expected: Files the agent is expected to create/modify.
        project_dir: Project root directory.

    Returns:
        The updated state dict.
    """
    state = load_state(project_dir) or _empty_state()
    agent_entry: Dict[str, Any] = {
        "id": agent_id,
        "description": description,
        "status": "running",
        "files_expected": files_expected or [],
        "files_created": [],
    }
    # Replace existing agent with same id, or append
    agents = [a for a in state.get("agents", []) if a.get("id") != agent_id]
    agents.append(agent_entry)
    state["agents"] = agents
    state["last_checkpoint"] = _now_iso()
    _atomic_write(_state_path(project_dir), state)
    return state


def mark_agent_complete(
    agent_id: str,
    files_created: Optional[List[str]] = None,
    status: str = "completed",
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an agent's status and record files it created.

    Args:
        agent_id: The agent to update.
        files_created: List of files the agent actually created/modified.
        status: New status (typically 'completed' or 'failed').
        project_dir: Project root directory.

    Returns:
        The updated state dict.

    Raises:
        KeyError: If agent_id is not found in current state.
    """
    state = load_state(project_dir)
    if state is None:
        raise KeyError(f"No session state exists; cannot update agent '{agent_id}'")

    found = False
    for agent in state.get("agents", []):
        if agent.get("id") == agent_id:
            agent["status"] = status
            agent["files_created"] = files_created or []
            found = True
            break

    if not found:
        raise KeyError(f"Agent '{agent_id}' not found in session state")

    state["last_checkpoint"] = _now_iso()
    _atomic_write(_state_path(project_dir), state)
    return state


def add_pending_task(
    task_description: str,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a task to the pending list.

    Args:
        task_description: Description of the task.
        project_dir: Project root directory.

    Returns:
        The updated state dict.
    """
    state = load_state(project_dir) or _empty_state()
    pending = state.get("pending_tasks", [])
    if task_description not in pending:
        pending.append(task_description)
    state["pending_tasks"] = pending
    state["last_checkpoint"] = _now_iso()
    _atomic_write(_state_path(project_dir), state)
    return state


def complete_pending_task(
    task_description: str,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Move a task from pending to completed.

    Args:
        task_description: Description of the task to complete.
        project_dir: Project root directory.

    Returns:
        The updated state dict.

    Raises:
        KeyError: If the task is not in the pending list.
    """
    state = load_state(project_dir)
    if state is None:
        raise KeyError(f"No session state exists; cannot complete task '{task_description}'")

    pending = state.get("pending_tasks", [])
    if task_description not in pending:
        raise KeyError(f"Task '{task_description}' not found in pending tasks")

    pending.remove(task_description)
    state["pending_tasks"] = pending

    completed = state.get("completed_tasks", [])
    if task_description not in completed:
        completed.append(task_description)
    state["completed_tasks"] = completed

    state["last_checkpoint"] = _now_iso()
    _atomic_write(_state_path(project_dir), state)
    return state


def checkpoint(
    note: str,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Update the checkpoint timestamp and note without changing other state.

    Args:
        note: Human-readable progress note.
        project_dir: Project root directory.

    Returns:
        The updated state dict.
    """
    state = load_state(project_dir) or _empty_state()
    state["last_checkpoint"] = _now_iso()
    state["checkpoint_note"] = note
    _atomic_write(_state_path(project_dir), state)
    return state
