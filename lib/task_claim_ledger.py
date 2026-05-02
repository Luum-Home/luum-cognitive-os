# SCOPE: both
"""Atomic task-claim ledger for multi-session agent coordination.

The work ledger records what agents did after launch. This module protects the
earlier acquisition point: a second session must not silently start the same
task while the first session still owns a live claim.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.concurrency_safety import project_runtime_dir

try:
    from lib.session_bus import append_event
except Exception:  # pragma: no cover - coordination bus must degrade safely
    append_event = None


DEFAULT_TTL_SECONDS = 1800


@dataclass(frozen=True)
class ClaimResult:
    """Result returned by task claim operations."""

    status: str
    task_id: str
    claim: dict[str, Any] | None = None
    held_by: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"status": self.status, "task_id": self.task_id}
        if self.claim is not None:
            data["claim"] = self.claim
        if self.held_by is not None:
            data["held_by"] = self.held_by
        return data


def claims_path(project_dir: str | Path) -> Path:
    """Return the runtime task-claims file path, creating its parent."""

    path = project_runtime_dir(project_dir) / "task-claims.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def lock_path(project_dir: str | Path) -> Path:
    """Return the flock path guarding the task-claims file."""

    path = project_runtime_dir(project_dir) / "task-claims.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def fingerprint_for(task_id: str, expected_files: list[str], scope: str) -> str:
    """Create a stable task-work fingerprint for duplicate-work diagnostics."""

    payload = {
        "task_id": task_id,
        "expected_files": sorted(expected_files),
        "scope": scope,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_claims(project_dir: str | Path) -> dict[str, Any]:
    """Read the task-claims document, tolerating absence and corruption."""

    path = claims_path(project_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "claims": {}}
    if not isinstance(data, dict) or not isinstance(data.get("claims"), dict):
        return {"version": 1, "claims": {}}
    data.setdefault("version", 1)
    return data


def _write_claims(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _now() -> float:
    return time.time()


def _emit_claim_event(project_dir: str | Path, event_type: str, payload: dict[str, Any], session_id: str | None) -> None:
    if append_event is None:
        return
    try:
        append_event(event_type, payload, project_dir=project_dir, session_id=session_id)
    except Exception:
        return


def _expired(claim: dict[str, Any], now: float) -> bool:
    expires_at = claim.get("expires_at")
    return not isinstance(expires_at, (int, float)) or now >= float(expires_at)


def acquire_claim(
    project_dir: str | Path,
    *,
    task_id: str,
    session_id: str,
    agent_id: str,
    expected_files: list[str] | None = None,
    scope: str = "",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> ClaimResult:
    """Acquire a task claim atomically.

    Returns ``status=blocked`` when another session has a live claim. The same
    session/agent may reacquire to refresh the lease.
    """

    expected = expected_files or []
    now = _now()
    ttl = ttl_seconds if ttl_seconds > 0 else DEFAULT_TTL_SECONDS
    claim = {
        "task_id": task_id,
        "session_id": session_id,
        "agent_id": agent_id,
        "expected_files": expected,
        "scope": scope,
        "fingerprint": fingerprint_for(task_id, expected, scope),
        "claimed_at": now,
        "expires_at": now + ttl,
        "ttl_seconds": ttl,
        "pid": os.getpid(),
        "host": socket.gethostname(),
    }
    with lock_path(project_dir).open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        path = claims_path(project_dir)
        data = read_claims(project_dir)
        claims = data.setdefault("claims", {})
        existing = claims.get(task_id)
        if isinstance(existing, dict) and not _expired(existing, now):
            same_owner = (
                existing.get("session_id") == session_id
                and existing.get("agent_id") == agent_id
            )
            if not same_owner:
                return ClaimResult(status="blocked", task_id=task_id, held_by=existing)
        claims[task_id] = claim
        data["updated_at"] = now
        _write_claims(path, data)
    _emit_claim_event(project_dir, "task_claimed", {"task_id": task_id, "expected_files": expected, "scope": scope}, session_id)
    return ClaimResult(status="acquired", task_id=task_id, claim=claim)


def release_claim(
    project_dir: str | Path,
    *,
    task_id: str,
    session_id: str | None = None,
    agent_id: str | None = None,
) -> ClaimResult:
    """Release a task claim when absent or owned by the requesting actor."""

    with lock_path(project_dir).open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        path = claims_path(project_dir)
        data = read_claims(project_dir)
        claims = data.setdefault("claims", {})
        existing = claims.get(task_id)
        if not isinstance(existing, dict):
            return ClaimResult(status="absent", task_id=task_id)
        if session_id and existing.get("session_id") != session_id:
            return ClaimResult(status="blocked", task_id=task_id, held_by=existing)
        if agent_id and existing.get("agent_id") != agent_id:
            return ClaimResult(status="blocked", task_id=task_id, held_by=existing)
        claims.pop(task_id, None)
        data["updated_at"] = _now()
        _write_claims(path, data)
    _emit_claim_event(project_dir, "task_claim_released", {"task_id": task_id}, session_id or existing.get("session_id"))
    return ClaimResult(status="released", task_id=task_id, claim=existing)


def list_claims(project_dir: str | Path, *, include_expired: bool = False) -> list[dict[str, Any]]:
    """List current claims, hiding expired entries by default."""

    now = _now()
    data = read_claims(project_dir)
    claims = [item for item in data.get("claims", {}).values() if isinstance(item, dict)]
    if include_expired:
        return sorted(claims, key=lambda item: str(item.get("task_id", "")))
    return sorted(
        (item for item in claims if not _expired(item, now)),
        key=lambda item: str(item.get("task_id", "")),
    )

