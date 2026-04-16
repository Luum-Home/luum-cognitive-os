"""User Request Queue — persists user messages that arrive while orchestrator is busy.

When a user sends a message via system-reminder (while agents are running),
the orchestrator appends it here immediately. This ensures no request is lost
to context compaction.

The /session-backlog skill reads this file as one of its sources.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _queue_path(session_dir: str | None = None) -> Path:
    """Resolve the queue file path for the current session."""
    if session_dir:
        return Path(session_dir) / "user-requests.jsonl"
    # Fallback: use .cognitive-os/sessions/current/
    cos_dir = os.environ.get("COGNITIVE_OS_DIR", ".cognitive-os")
    session_id = os.environ.get("COGNITIVE_OS_SESSION_ID", "unknown")
    return Path(cos_dir) / "sessions" / session_id / "user-requests.jsonl"


def enqueue_request(message: str, session_dir: str | None = None, status: str = "pending") -> dict:
    """Append a user request to the session queue.

    Args:
        message: The user's message text.
        session_dir: Optional session directory path. Auto-resolved if not given.
        status: One of 'pending', 'in_progress', 'done', 'deferred'.

    Returns:
        The queued entry dict.
    """
    path = _queue_path(session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message[:2000],  # Cap to prevent huge entries
        "status": status,
    }

    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def get_pending_requests(session_dir: str | None = None) -> list[dict]:
    """Read all pending (unresolved) requests from the queue."""
    path = _queue_path(session_dir)
    if not path.exists():
        return []

    pending = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if entry.get("status") == "pending":
                pending.append(entry)
        except json.JSONDecodeError:
            continue
    return pending


def mark_done(message_prefix: str, session_dir: str | None = None) -> bool:
    """Mark a request as done by matching the start of its message.

    Returns True if a matching request was found and updated.
    """
    path = _queue_path(session_dir)
    if not path.exists():
        return False

    lines = path.read_text().splitlines()
    updated = False
    new_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if (entry.get("status") == "pending"
                    and entry.get("message", "").startswith(message_prefix)
                    and not updated):
                entry["status"] = "done"
                updated = True
            new_lines.append(json.dumps(entry, ensure_ascii=False))
        except json.JSONDecodeError:
            new_lines.append(line)

    if updated:
        path.write_text("\n".join(new_lines) + "\n")
    return updated


def get_all_requests(session_dir: str | None = None) -> list[dict]:
    """Read ALL requests (any status) from the queue."""
    path = _queue_path(session_dir)
    if not path.exists():
        return []

    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def format_pending_summary(session_dir: str | None = None) -> str:
    """Format pending requests as a readable summary."""
    pending = get_pending_requests(session_dir)
    if not pending:
        return "No pending user requests."

    lines = [f"**{len(pending)} pending user requests:**"]
    for i, req in enumerate(pending, 1):
        msg = req["message"][:100]
        ts = req.get("timestamp", "?")[:19]
        lines.append(f"{i}. [{ts}] {msg}{'...' if len(req['message']) > 100 else ''}")
    return "\n".join(lines)
