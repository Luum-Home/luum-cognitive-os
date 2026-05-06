# SCOPE: both
"""Branch ownership lease files for cross-session single-writer safety (ADR-182)."""
from __future__ import annotations

import fcntl
import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    from lib.session_bus import append_event
except Exception:  # pragma: no cover
    append_event = None

DEFAULT_TTL_SECONDS = 14_400


def _runtime_dir(project_dir: str | Path) -> Path:
    path = Path(project_dir) / ".cognitive-os" / "runtime" / "branch-locks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slug(branch: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch.strip())
    return cleaned.strip("-") or "detached"


def lock_file(project_dir: str | Path, branch: str) -> Path:
    return _runtime_dir(project_dir) / f"{_slug(branch)}.lock"


def global_lock_file(project_dir: str | Path) -> Path:
    return _runtime_dir(project_dir) / ".branch-locks.lock"


@contextmanager
def _locked(project_dir: str | Path) -> Iterator[None]:
    path = global_lock_file(project_dir)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return row if isinstance(row, dict) else None


def _is_expired(row: dict[str, Any], now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return float(row.get("expires_at_epoch") or 0) <= now


def holder(project_dir: str | Path, branch: str) -> dict[str, Any] | None:
    """Return current lock holder, ignoring expired dead-PID locks."""
    path = lock_file(project_dir, branch)
    row = _read(path)
    if not row:
        return None
    if _is_expired(row) and not _pid_alive(int(row.get("pid") or 0)):
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return row


def acquire(
    project_dir: str | Path,
    *,
    branch: str,
    session_id: str,
    pid: int,
    worktree: str | Path,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Acquire or renew a branch lock; returns {status, lock, held_by?}."""
    now = time.time()
    with _locked(project_dir):
        current = holder(project_dir, branch)
        if current and current.get("session_id") != session_id:
            if _pid_alive(int(current.get("pid") or 0)) or not _is_expired(current, now):
                return {"status": "blocked", "lock": None, "held_by": current}
        expires = now + ttl_seconds
        row = {
            "schema_version": 1,
            "branch": branch,
            "session_id": session_id,
            "pid": int(pid),
            "worktree": str(Path(worktree).resolve()),
            "acquired_at_epoch": now if not current else float(current.get("acquired_at_epoch") or now),
            "renewed_at_epoch": now,
            "ttl_seconds": int(ttl_seconds),
            "expires_at_epoch": expires,
        }
        lock_file(project_dir, branch).write_text(json.dumps(row, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if append_event is not None:
        try:
            append_event("branch-acquire", {"branch": branch, "worktree": str(worktree)}, project_dir=project_dir, session_id=session_id)
        except Exception:
            pass
    return {"status": "acquired", "lock": row, "held_by": None}


def renew(project_dir: str | Path, *, branch: str, session_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    with _locked(project_dir):
        row = holder(project_dir, branch)
        if not row or row.get("session_id") != session_id:
            return False
        now = time.time()
        row["renewed_at_epoch"] = now
        row["ttl_seconds"] = int(ttl_seconds)
        row["expires_at_epoch"] = now + ttl_seconds
        lock_file(project_dir, branch).write_text(json.dumps(row, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return True


def release(project_dir: str | Path, *, branch: str, session_id: str) -> bool:
    with _locked(project_dir):
        row = holder(project_dir, branch)
        if not row or row.get("session_id") != session_id:
            return False
        try:
            lock_file(project_dir, branch).unlink()
        except OSError:
            pass
    if append_event is not None:
        try:
            append_event("branch-release", {"branch": branch}, project_dir=project_dir, session_id=session_id)
        except Exception:
            pass
    return True


def release_all_for_session(project_dir: str | Path, *, session_id: str) -> int:
    count = 0
    with _locked(project_dir):
        for path in _runtime_dir(project_dir).glob("*.lock"):
            if path.name.startswith("."):
                continue
            row = _read(path)
            if row and row.get("session_id") == session_id:
                try:
                    path.unlink()
                    count += 1
                except OSError:
                    pass
    return count


def is_held_by_other(project_dir: str | Path, *, branch: str, session_id: str) -> bool:
    row = holder(project_dir, branch)
    return bool(row and row.get("session_id") != session_id)
