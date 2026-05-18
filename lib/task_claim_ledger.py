# SCOPE: both
"""Compatibility shim for lib/task_claim_ledger.py.

DEPRECATED: This module now delegates to scripts/cos_task_claims.py, the
canonical single source of truth for task claims per ADR-116 §P1.1.

Canonical store: .cognitive-os/tasks/active-claims.json
Canonical API:   scripts/cos_task_claims.py

Previous behaviour (flock + .cognitive-os/runtime/task-claims.json) is
preserved via delegation to the canonical API, which writes to the
ADR-116-mandated path.  The ClaimResult dataclass and function signatures are
kept intact so callers (tests, lib/session_coordination.py) do not require
changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys

# Ensure repo root is on path so scripts.cos_task_claims is importable.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.cos_task_claims import (  # noqa: E402
    claim_task as _claim_task,
    claims_path,
    prune_claims,
    normalize_claims,
    read_json,
    release_task as _release_task,
)


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


def fingerprint_for(task_id: str, expected_files: list[str], scope: str) -> str:
    """Create a stable task-work fingerprint. Delegates to cos_task_claims logic."""
    import hashlib
    import json as _json

    payload = {
        "task_id": task_id,
        "expected_files": sorted(expected_files),
        "scope": scope,
    }
    raw = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    """Acquire a task claim atomically via the canonical CTC store.

    Returns ``status=blocked`` when another session has a live claim.
    """
    project = Path(project_dir).resolve()
    task = {
        "id": task_id,
        "expected_files": expected_files or [],
    }
    ok, result = _claim_task(
        project,
        task,
        session=session_id,
        expected_files=expected_files or [],
        agent_id=agent_id,
        scope=scope,
        ttl_seconds=ttl_seconds,
    )
    if ok:
        return ClaimResult(status="acquired", task_id=task_id, claim=result)
    else:
        held_by_sid = result.get("held_by")
        held_by = {"session_id": held_by_sid} if held_by_sid else None
        return ClaimResult(status="blocked", task_id=task_id, held_by=held_by)


def release_claim(
    project_dir: str | Path,
    *,
    task_id: str,
    session_id: str | None = None,
    agent_id: str | None = None,
) -> ClaimResult:
    """Release a task claim when absent or owned by the requesting actor."""
    project = Path(project_dir).resolve()
    result = _release_task(project, task_id, session=session_id)
    if result.get("updated"):
        return ClaimResult(status="released", task_id=task_id)
    # Check if it was absent or blocked (wrong owner).
    data = normalize_claims(read_json(claims_path(project), {"claims": []}))
    existing = next(
        (c for c in data.get("claims", []) if c.get("task_id") == task_id and c.get("status") == "active"),
        None,
    )
    if existing is None:
        return ClaimResult(status="absent", task_id=task_id)
    if session_id and existing.get("session_id") != session_id:
        return ClaimResult(status="blocked", task_id=task_id, held_by=existing)
    return ClaimResult(status="absent", task_id=task_id)


def list_claims(project_dir: str | Path, *, include_expired: bool = False) -> list[dict[str, Any]]:
    """List current claims, hiding stale/completed entries by default."""
    project = Path(project_dir).resolve()
    data = prune_claims(project, normalize_claims(read_json(claims_path(project), {"claims": []})))
    all_claims = [c for c in data.get("claims", []) if isinstance(c, dict)]
    if include_expired:
        return sorted(all_claims, key=lambda c: str(c.get("task_id", "")))
    active = [c for c in all_claims if c.get("status") == "active"]
    return sorted(active, key=lambda c: str(c.get("task_id", "")))
