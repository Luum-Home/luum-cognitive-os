# SCOPE: both
"""Append-only inter-session event bus for Cognitive OS coordination."""
from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import fcntl


@dataclass(frozen=True)
class PeerSummary:
    """Compact summary of one peer orchestrator session."""

    session_id: str
    branch: str
    last_seen: float
    pid: int
    project_dir: str
    topic_keywords: list[str]
    recent_writes: list[str]
    recent_events: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _session_id(default: str = "unknown") -> str:
    return (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or default
    )


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
        "event_type": event_type.strip().replace("_", "-"),
        "session_id": session_id or _session_id(),
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
    normalized_type = event_type.replace("_", "-") if event_type else None
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if normalized_type and event.get("event_type") != normalized_type:
            continue
        events.append(event)
    return events


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _current_branch(project_dir: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=str(project_dir),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=1,
        ).strip()
    except Exception:
        return ""


def _dedupe(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def peers(
    *,
    project_dir: str | Path | None = None,
    within_seconds: int = 1800,
    alive_only: bool = True,
    current_session_id: str | None = None,
    limit: int = 200,
) -> list[PeerSummary]:
    """Summarize recently active peer sessions from the append-only event log."""
    root = _root(project_dir)
    now = time.time()
    current = current_session_id or _session_id()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in read_events(project_dir=root, limit=limit):
        sid = str(event.get("session_id") or "unknown")
        if sid in {"", "unknown", current}:
            continue
        ts = float(event.get("timestamp_epoch") or 0)
        if within_seconds > 0 and now - ts > within_seconds:
            continue
        grouped.setdefault(sid, []).append(event)

    summaries: list[PeerSummary] = []
    for sid, events in grouped.items():
        events.sort(key=lambda row: float(row.get("timestamp_epoch") or 0))
        last = events[-1]
        pid = int(last.get("pid") or 0)
        if alive_only and not _pid_alive(pid):
            continue
        branch = ""
        topics: list[str] = []
        writes: list[str] = []
        event_types: list[str] = []
        for event in events:
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            event_types.append(str(event.get("event_type") or ""))
            branch = str(payload.get("branch") or branch)
            if isinstance(payload.get("topic_keywords"), list):
                topics.extend(str(item) for item in payload.get("topic_keywords") if item)
            elif payload.get("topic"):
                topics.append(str(payload.get("topic")))
            path = payload.get("path") or payload.get("file_path") or payload.get("target")
            if path and event.get("event_type") in {"file-write-intent", "commit-intent", "commit-landed"}:
                writes.append(str(path))
        if not branch:
            branch = _current_branch(root)
        summaries.append(
            PeerSummary(
                session_id=sid,
                branch=branch,
                last_seen=float(last.get("timestamp_epoch") or 0),
                pid=pid,
                project_dir=str(last.get("project_dir") or root),
                topic_keywords=_dedupe(list(reversed(topics)), limit=5),
                recent_writes=_dedupe(list(reversed(writes)), limit=5),
                recent_events=_dedupe(list(reversed(event_types)), limit=8),
            )
        )
    summaries.sort(key=lambda item: item.last_seen, reverse=True)
    return summaries
