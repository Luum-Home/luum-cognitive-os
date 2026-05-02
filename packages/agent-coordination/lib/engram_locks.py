# SCOPE: both
"""P5.2 — Engram-backed cross-session advisory locks.

Advisory lock protocol
-----------------------
A lock is a lightweight engram observation stored at topic key
``lock/<resource>``.  It carries::

    {
        "resource": str,
        "session_id": str,
        "acquired_at": ISO-8601,
        "ttl_seconds": int,
        "heartbeat_at": ISO-8601,
    }

TTL semantics
~~~~~~~~~~~~~
A lock is considered *live* when::

    now - heartbeat_at  <  ttl_seconds + GRACE_SECONDS

The grace period avoids race conditions when a heartbeat is slightly late.
When ``acquire_lock`` detects a stale lock (heartbeat older than
``ttl_seconds + GRACE_SECONDS``) it silently replaces the lock with the new
owner's record — auto-release.

Heartbeat
~~~~~~~~~
The lock holder must call ``heartbeat_lock`` every ~60 s (or whatever interval
suits the workload) to extend the lock's effective lifetime.

Injection pattern for unit tests
---------------------------------
Replace the module-level ``_save_fn`` and ``_search_fn`` references::

    import engram_locks
    engram_locks._save_fn  = my_mock_save
    engram_locks._search_fn = my_mock_search
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Low-level engram wrappers (replaced in unit tests via module-level patching)
# ---------------------------------------------------------------------------

_ENGRAM_BIN = os.environ.get("ENGRAM_BIN", "engram")
_PROJECT = "luum-cognitive-os"

# Grace period added to ttl_seconds before a lock is considered stale.
GRACE_SECONDS: int = 30


def _default_save_fn(
    title: str,
    content: str,
    *,
    type_: str = "architecture",
    topic_key: str = "",
    project: str = _PROJECT,
) -> dict[str, Any] | None:
    cmd = [
        _ENGRAM_BIN, "save",
        "--json",
        "--title", title,
        "--content", content,
        "--type", type_,
    ]
    if topic_key:
        cmd.extend(["--topic-key", topic_key])
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return None
        output = proc.stdout.strip()
        if not output:
            return None
        data = json.loads(output)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _default_search_fn(
    query: str,
    *,
    limit: int = 5,
    project: str = _PROJECT,
) -> list[dict[str, Any]]:
    cmd = [_ENGRAM_BIN, "search", "--json", "--limit", str(limit), query]
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return []
        output = proc.stdout.strip()
        if not output:
            return []
        data = json.loads(output)
        if isinstance(data, list):
            return data[:limit]
        if isinstance(data, dict) and "results" in data:
            return data["results"][:limit]
        return []
    except Exception:
        return []


# Module-level function references — replace in tests to inject mocks.
_save_fn = _default_save_fn
_search_fn = _default_search_fn


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware datetime."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _seconds_since(ts: str) -> float:
    """Return seconds elapsed since *ts* (ISO-8601)."""
    try:
        then = _parse_iso(ts)
        now = datetime.now(timezone.utc)
        return (now - then).total_seconds()
    except Exception:
        # Unparseable timestamp — treat as very old so stale check triggers.
        return float("inf")


def _is_stale(lock: dict[str, Any]) -> bool:
    """Return True if the lock's heartbeat is older than ttl + grace."""
    heartbeat_at = lock.get("heartbeat_at", lock.get("acquired_at", ""))
    ttl = int(lock.get("ttl_seconds", 300))
    return _seconds_since(heartbeat_at) > (ttl + GRACE_SECONDS)


def _topic_key(resource: str) -> str:
    return f"lock/{resource}"


def _title_for(resource: str) -> str:
    return f"lock:{resource}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def acquire_lock(
    resource: str,
    session_id: str,
    ttl_seconds: int = 300,
) -> dict[str, Any] | None:
    """Acquire an advisory lock on *resource* for *session_id*.

    Returns:
        The lock record dict if acquired (or refreshed for the same session).
        ``None`` if the resource is already locked by a different live session.

    Auto-stale-release:
        If an existing lock's heartbeat is older than ``ttl_seconds + GRACE_SECONDS``
        the stale lock is overwritten regardless of owner.
    """
    existing = find_lock(resource)

    if existing is not None:
        holder = existing.get("session_id")
        if holder == session_id:
            # Idempotent: same session re-acquires — refresh heartbeat.
            return _write_lock(resource, session_id, ttl_seconds)
        # Different session — check staleness.
        if not _is_stale(existing):
            return None  # Locked by another live session.
        # Stale lock — auto-release and fall through to acquire.

    return _write_lock(resource, session_id, ttl_seconds)


def _write_lock(
    resource: str,
    session_id: str,
    ttl_seconds: int,
) -> dict[str, Any]:
    """Write (or overwrite) the lock record and return it."""
    now = _now_iso()
    record: dict[str, Any] = {
        "resource": resource,
        "session_id": session_id,
        "acquired_at": now,
        "ttl_seconds": ttl_seconds,
        "heartbeat_at": now,
    }
    _save_fn(
        _title_for(resource),
        json.dumps(record),
        type_="architecture",
        topic_key=_topic_key(resource),
        project=_PROJECT,
    )
    return record


def release_lock(resource: str, session_id: str) -> bool:
    """Release the lock on *resource* if held by *session_id*.

    Returns ``True`` if released, ``False`` if not held by this session or
    engram is unavailable.
    """
    existing = find_lock(resource)
    if not existing:
        return False
    if existing.get("session_id") != session_id:
        return False

    # Write a tombstone record to overwrite the live lock.
    now = _now_iso()
    record: dict[str, Any] = {
        "resource": resource,
        "session_id": session_id,
        "released_at": now,
        "ttl_seconds": 0,
        "heartbeat_at": now,
        "status": "released",
    }
    _save_fn(
        _title_for(resource),
        json.dumps(record),
        type_="architecture",
        topic_key=_topic_key(resource),
        project=_PROJECT,
    )
    return True


def heartbeat_lock(resource: str, session_id: str) -> bool:
    """Extend the lock's effective TTL by refreshing ``heartbeat_at``.

    Must be called by the lock holder at least every ``ttl_seconds - 30 s``
    to prevent auto-stale-release by competing sessions.

    Returns ``True`` if the heartbeat was written, ``False`` if the lock is
    not held by *session_id* (or does not exist).
    """
    existing = find_lock(resource)
    if not existing:
        return False
    if existing.get("session_id") != session_id:
        return False
    if existing.get("status") == "released":
        return False

    updated: dict[str, Any] = {
        **existing,
        "heartbeat_at": _now_iso(),
    }
    _save_fn(
        _title_for(resource),
        json.dumps(updated),
        type_="architecture",
        topic_key=_topic_key(resource),
        project=_PROJECT,
    )
    return True


def find_lock(resource: str) -> dict[str, Any] | None:
    """Return the current lock record for *resource*, or ``None``.

    A ``"released"`` lock is treated as absent (returns ``None``).
    """
    results = _search_fn(_topic_key(resource), limit=3, project=_PROJECT)
    for obs in results:
        topic = obs.get("topic_key", "")
        if topic == _topic_key(resource):
            content = obs.get("content", "")
            try:
                record = json.loads(content)
                if isinstance(record, dict) and record.get("resource") == resource:
                    if record.get("status") == "released":
                        return None
                    return record
            except (json.JSONDecodeError, ValueError):
                continue
    # Fallback: parse content from any hit
    for obs in results:
        content = obs.get("content", "")
        try:
            record = json.loads(content)
            if isinstance(record, dict) and record.get("resource") == resource:
                if record.get("status") == "released":
                    return None
                return record
        except (json.JSONDecodeError, ValueError):
            continue
    return None
