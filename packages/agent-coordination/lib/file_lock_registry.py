"""File Lock Registry -- Distributed file locking for agent coordination.

Provides file-level locking so that multiple concurrent agents (or sessions)
can coordinate writes. Uses Valkey (Redis-compatible) when available, with a
file-based fallback stored in ``.cognitive-os/locks/``.

Each lock is scoped to an ``agent_id`` and has a TTL (default 300 s).
Expired locks are automatically cleaned on any lock operation.

Python 3.9+ compatible.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default lock directory for file-based fallback
_DEFAULT_LOCK_DIR = ".cognitive-os/locks"

# Default TTL for locks
DEFAULT_TTL_SECONDS = 300


def _now_epoch() -> float:
    """Return current UNIX epoch as a float."""
    return time.time()


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _file_hash(file_path: str) -> str:
    """Return an MD5 hex digest of *file_path* for use as a lock filename."""
    return hashlib.md5(file_path.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Valkey (Redis-compatible) backend
# ---------------------------------------------------------------------------

def _get_valkey_client():
    """Return a connected Valkey/Redis client or *None*."""
    try:
        import redis

        host = os.environ.get("VALKEY_HOST", "localhost")
        port = int(os.environ.get("VALKEY_PORT", "6379"))
        client = redis.Redis(host=host, port=port, socket_connect_timeout=2, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


_VALKEY_PREFIX = "cos:lock:"


def _valkey_lock_key(file_path: str) -> str:
    return "%s%s" % (_VALKEY_PREFIX, _file_hash(file_path))


# ---------------------------------------------------------------------------
# File-based fallback backend
# ---------------------------------------------------------------------------

def _lock_dir() -> Path:
    lock_dir = Path(os.environ.get("COGNITIVE_OS_LOCK_DIR", _DEFAULT_LOCK_DIR))
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir


def _lock_file_path(file_path: str) -> Path:
    return _lock_dir() / ("%s.json" % _file_hash(file_path))


def _read_lock_file(lock_path: Path) -> Optional[Dict]:
    """Read a lock file, returning *None* if missing or corrupt."""
    if not lock_path.exists():
        return None
    try:
        data = json.loads(lock_path.read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _write_lock_file(lock_path: Path, data: Dict) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(data))


def _is_expired(lock_data: Dict) -> bool:
    """Return *True* if the lock has exceeded its TTL."""
    acquired = lock_data.get("acquired_at_epoch", 0)
    ttl = lock_data.get("ttl", DEFAULT_TTL_SECONDS)
    return _now_epoch() - acquired > ttl


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def acquire_lock(agent_id: str, file_path: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
    """Acquire a lock on *file_path* for *agent_id*.

    If the lock is already held by the same agent the TTL is refreshed and
    the call returns ``True``.  If held by a different agent and not expired,
    returns ``False``.

    Args:
        agent_id: Unique identifier of the requesting agent.
        file_path: Absolute or relative path of the file to lock.
        ttl_seconds: Time-to-live in seconds (default 300).

    Returns:
        ``True`` if the lock was acquired (or refreshed), ``False`` otherwise.
    """
    lock_data = {
        "agent_id": agent_id,
        "file_path": file_path,
        "acquired_at": _now_iso(),
        "acquired_at_epoch": _now_epoch(),
        "ttl": ttl_seconds,
    }

    # Try Valkey first
    client = _get_valkey_client()
    if client is not None:
        key = _valkey_lock_key(file_path)
        try:
            existing = client.get(key)
            if existing is not None:
                holder = json.loads(existing)
                if holder.get("agent_id") == agent_id:
                    # Same agent -> refresh
                    client.setex(key, ttl_seconds, json.dumps(lock_data))
                    return True
                # Different agent -> fail (Valkey TTL handles expiry)
                return False
            # No existing lock -> acquire
            # Use SET NX for atomicity
            acquired = client.set(key, json.dumps(lock_data), nx=True, ex=ttl_seconds)
            return bool(acquired)
        except Exception as exc:
            logger.warning("Valkey acquire_lock failed (%s), falling back to file", exc)

    # File-based fallback
    lp = _lock_file_path(file_path)
    existing = _read_lock_file(lp)
    if existing is not None:
        if existing.get("agent_id") == agent_id:
            # Refresh
            _write_lock_file(lp, lock_data)
            return True
        if not _is_expired(existing):
            return False
        # Expired -> overwrite

    _write_lock_file(lp, lock_data)
    return True


def release_lock(agent_id: str, file_path: str) -> bool:
    """Release a lock on *file_path* only if held by *agent_id*.

    Returns:
        ``True`` if the lock was held by this agent and released,
        ``False`` otherwise.
    """
    client = _get_valkey_client()
    if client is not None:
        key = _valkey_lock_key(file_path)
        try:
            existing = client.get(key)
            if existing is not None:
                holder = json.loads(existing)
                if holder.get("agent_id") == agent_id:
                    client.delete(key)
                    return True
            return False
        except Exception as exc:
            logger.warning("Valkey release_lock failed (%s), falling back to file", exc)

    lp = _lock_file_path(file_path)
    existing = _read_lock_file(lp)
    if existing is None:
        return False
    if existing.get("agent_id") != agent_id:
        return False
    try:
        lp.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def check_lock(file_path: str) -> Optional[str]:
    """Return the *agent_id* that holds the lock, or ``None`` if unlocked.

    Expired locks are treated as absent.
    """
    client = _get_valkey_client()
    if client is not None:
        key = _valkey_lock_key(file_path)
        try:
            existing = client.get(key)
            if existing is not None:
                return json.loads(existing).get("agent_id")
            return None
        except Exception as exc:
            logger.warning("Valkey check_lock failed (%s), falling back to file", exc)

    lp = _lock_file_path(file_path)
    existing = _read_lock_file(lp)
    if existing is None:
        return None
    if _is_expired(existing):
        try:
            lp.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return existing.get("agent_id")


def wait_for_lock(
    agent_id: str,
    file_path: str,
    timeout: int = 60,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """Block until the lock on *file_path* can be acquired.

    Polls every second.  Returns ``True`` if the lock was acquired within
    *timeout* seconds, ``False`` on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if acquire_lock(agent_id, file_path, ttl_seconds=ttl_seconds):
            return True
        time.sleep(1.0)
    return False


def list_locks() -> List[Dict]:
    """Return a list of all currently active (non-expired) locks.

    Each element is a dict with ``agent_id``, ``file_path``,
    ``acquired_at``, and ``ttl``.
    """
    locks: List[Dict] = []

    # Valkey path
    client = _get_valkey_client()
    if client is not None:
        try:
            keys = client.keys("%s*" % _VALKEY_PREFIX)
            for key in keys:
                raw = client.get(key)
                if raw is not None:
                    try:
                        data = json.loads(raw)
                        locks.append({
                            "agent_id": data.get("agent_id", ""),
                            "file_path": data.get("file_path", ""),
                            "acquired_at": data.get("acquired_at", ""),
                            "ttl": data.get("ttl", DEFAULT_TTL_SECONDS),
                        })
                    except (json.JSONDecodeError, ValueError):
                        continue
            return locks
        except Exception as exc:
            logger.warning("Valkey list_locks failed (%s), falling back to file", exc)

    # File fallback
    ld = _lock_dir()
    for lock_file in ld.glob("*.json"):
        data = _read_lock_file(lock_file)
        if data is None:
            continue
        if _is_expired(data):
            try:
                lock_file.unlink(missing_ok=True)
            except OSError:
                pass
            continue
        locks.append({
            "agent_id": data.get("agent_id", ""),
            "file_path": data.get("file_path", ""),
            "acquired_at": data.get("acquired_at", ""),
            "ttl": data.get("ttl", DEFAULT_TTL_SECONDS),
        })
    return locks


def cleanup_expired() -> int:
    """Remove all expired locks.  Returns the count of locks removed."""
    removed = 0

    # Valkey handles TTL natively, nothing to clean
    # File fallback
    ld = _lock_dir()
    for lock_file in ld.glob("*.json"):
        data = _read_lock_file(lock_file)
        if data is None:
            continue
        if _is_expired(data):
            try:
                lock_file.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
    return removed


def release_all_for_agent(agent_id: str) -> int:
    """Release every lock held by *agent_id*.

    Useful for cleaning up when an agent dies.  Returns the count of
    locks released.
    """
    released = 0

    # Valkey path
    client = _get_valkey_client()
    if client is not None:
        try:
            keys = client.keys("%s*" % _VALKEY_PREFIX)
            for key in keys:
                raw = client.get(key)
                if raw is not None:
                    try:
                        data = json.loads(raw)
                        if data.get("agent_id") == agent_id:
                            client.delete(key)
                            released += 1
                    except (json.JSONDecodeError, ValueError):
                        continue
            return released
        except Exception as exc:
            logger.warning("Valkey release_all failed (%s), falling back to file", exc)

    # File fallback
    ld = _lock_dir()
    for lock_file in ld.glob("*.json"):
        data = _read_lock_file(lock_file)
        if data is None:
            continue
        if data.get("agent_id") == agent_id:
            try:
                lock_file.unlink(missing_ok=True)
                released += 1
            except OSError:
                pass
    return released
