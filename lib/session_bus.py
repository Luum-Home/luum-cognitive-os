"""Append-only inter-session event bus for Cognitive OS coordination."""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import fcntl


def _root(project_dir: str | Path | None = None) -> Path:
    return Path(project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()


def events_path(project_dir: str | Path | None = None) -> Path:
    return _root(project_dir) / ".cognitive-os" / "sessions" / "events.jsonl"


def lock_path(project_dir: str | Path | None = None) -> Path:
    return _root(project_dir) / ".cognitive-os" / "sessions" / "events.lock"


@contextmanager
def _locked(project_dir: str | Path | None = None) -> Iterator[None]:
    path = lock_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    project_dir: str | Path | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Append one coordination event and return the stored event."""
    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")
    root = _root(project_dir)
    event = {
        "schema_version": 1,
        "timestamp_epoch": time.time(),
        "event_type": event_type.strip(),
        "session_id": session_id or os.environ.get("COGNITIVE_OS_SESSION_ID") or "unknown",
        "pid": os.getpid(),
        "project_dir": str(root),
        "payload": payload or {},
    }
    path = events_path(root)
    with _locked(root):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def read_events(
    *,
    project_dir: str | Path | None = None,
    limit: int | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Read recent coordination events from newest window preserving file order."""
    path = events_path(project_dir)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if limit is not None and limit > 0:
        lines = lines[-limit:]
    events: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event_type and event.get("event_type") != event_type:
            continue
        events.append(event)
    return events
