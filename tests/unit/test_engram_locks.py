"""Unit tests for lib/engram_locks.py (P5.2).

All engram I/O is mocked via the _save_fn / _search_fn injection points.
No live engram daemon is required.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

# Ensure lib/ is on sys.path so the symlinked module resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "lib"))

import engram_locks  # noqa: E402 — after path setup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeLockStore:
    """In-memory store that mimics engram's save/search behavior for locks."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self.save_calls: list[dict] = []

    def save(self, title: str, content: str, *, type_: str = "architecture",
             topic_key: str = "", project: str = "") -> dict[str, Any] | None:
        self.save_calls.append({"title": title, "content": content,
                                 "topic_key": topic_key})
        if topic_key:
            self._store[topic_key] = content
        return {"id": 1, "title": title, "content": content, "topic_key": topic_key}

    def search(self, query: str, *, limit: int = 5,
               project: str = "") -> list[dict[str, Any]]:
        results = []
        for tk, content in self._store.items():
            if query in tk or query in content:
                results.append({
                    "id": 1,
                    "title": tk,
                    "content": content,
                    "topic_key": tk,
                })
        return results[:limit]

    def inject_stale_lock(self, resource: str, session_id: str,
                          ttl_seconds: int, age_seconds: int) -> None:
        """Directly insert a lock record whose heartbeat is *age_seconds* old."""
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
        record = {
            "resource": resource,
            "session_id": session_id,
            "acquired_at": stale_time.isoformat(),
            "ttl_seconds": ttl_seconds,
            "heartbeat_at": stale_time.isoformat(),
        }
        self._store[f"lock/{resource}"] = json.dumps(record)


@pytest.fixture(autouse=True)
def patch_engram_locks(monkeypatch):
    """Replace module-level _save_fn / _search_fn with a FakeLockStore."""
    store = FakeLockStore()
    monkeypatch.setattr(engram_locks, "_save_fn", store.save)
    monkeypatch.setattr(engram_locks, "_search_fn", store.search)
    return store


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestAcquireLock:
    def test_acquire_fresh_lock(self, patch_engram_locks):
        """acquire_lock returns a record when the resource is free."""
        result = engram_locks.acquire_lock("R1", "session-A", ttl_seconds=300)

        assert result is not None
        assert result["resource"] == "R1"
        assert result["session_id"] == "session-A"
        assert result["ttl_seconds"] == 300
        assert "heartbeat_at" in result

    def test_acquire_saves_to_engram(self, patch_engram_locks):
        """acquire_lock invokes _save_fn with the correct topic_key."""
        engram_locks.acquire_lock("R2", "session-B")

        assert any(c["topic_key"] == "lock/R2" for c in patch_engram_locks.save_calls)

    def test_double_acquire_same_session_is_idempotent(self, patch_engram_locks):
        """Same session acquiring the same lock twice succeeds (refresh)."""
        engram_locks.acquire_lock("R3", "session-C", ttl_seconds=300)
        result2 = engram_locks.acquire_lock("R3", "session-C", ttl_seconds=300)

        assert result2 is not None
        assert result2["session_id"] == "session-C"

    def test_double_acquire_different_session_is_blocked(self, patch_engram_locks):
        """A second session cannot acquire a live lock held by another session."""
        engram_locks.acquire_lock("R4", "session-D", ttl_seconds=300)
        result = engram_locks.acquire_lock("R4", "session-E", ttl_seconds=300)

        assert result is None, "Expected None — lock should be held by session-D"


class TestHeartbeat:
    def test_heartbeat_updates_heartbeat_at(self, patch_engram_locks):
        """heartbeat_lock writes a new heartbeat_at timestamp."""
        engram_locks.acquire_lock("R5", "session-F", ttl_seconds=300)
        ok = engram_locks.heartbeat_lock("R5", "session-F")

        assert ok is True
        lock = engram_locks.find_lock("R5")
        assert lock is not None
        assert lock["session_id"] == "session-F"

    def test_heartbeat_wrong_session_fails(self, patch_engram_locks):
        """heartbeat_lock returns False if the caller is not the lock owner."""
        engram_locks.acquire_lock("R6", "session-G", ttl_seconds=300)
        ok = engram_locks.heartbeat_lock("R6", "session-H")  # wrong session

        assert ok is False

    def test_heartbeat_on_nonexistent_lock_fails(self, patch_engram_locks):
        """heartbeat_lock returns False for a resource that has no lock."""
        ok = engram_locks.heartbeat_lock("nonexistent", "session-Z")
        assert ok is False


class TestStaleAutoRelease:
    def test_stale_lock_is_auto_released_on_acquire(self, patch_engram_locks):
        """A second session can acquire a stale lock (heartbeat > ttl + grace)."""
        ttl = 60
        # Inject a lock whose heartbeat is well past ttl + GRACE_SECONDS.
        patch_engram_locks.inject_stale_lock(
            "R7", "session-I", ttl_seconds=ttl,
            age_seconds=ttl + engram_locks.GRACE_SECONDS + 10,
        )

        result = engram_locks.acquire_lock("R7", "session-J", ttl_seconds=300)

        assert result is not None, "Should acquire — old lock is stale"
        assert result["session_id"] == "session-J"

    def test_live_lock_not_auto_released(self, patch_engram_locks):
        """A lock whose heartbeat is within TTL cannot be stolen."""
        ttl = 300
        patch_engram_locks.inject_stale_lock(
            "R8", "session-K", ttl_seconds=ttl,
            age_seconds=10,  # very fresh
        )

        result = engram_locks.acquire_lock("R8", "session-L", ttl_seconds=300)
        assert result is None, "Should be blocked — lock is live"


class TestReleaseLock:
    def test_release_own_lock_returns_true(self, patch_engram_locks):
        """release_lock returns True when the caller owns the lock."""
        engram_locks.acquire_lock("R9", "session-M", ttl_seconds=300)
        ok = engram_locks.release_lock("R9", "session-M")

        assert ok is True

    def test_release_other_session_lock_returns_false(self, patch_engram_locks):
        """release_lock returns False when the caller does not own the lock."""
        engram_locks.acquire_lock("R10", "session-N", ttl_seconds=300)
        ok = engram_locks.release_lock("R10", "session-O")

        assert ok is False

    def test_released_lock_is_treated_as_absent_by_find(self, patch_engram_locks):
        """find_lock returns None after the lock has been released."""
        engram_locks.acquire_lock("R11", "session-P", ttl_seconds=300)
        engram_locks.release_lock("R11", "session-P")

        found = engram_locks.find_lock("R11")
        assert found is None


class TestFindLock:
    def test_find_returns_none_for_free_resource(self, patch_engram_locks):
        """find_lock returns None when no lock has been acquired."""
        assert engram_locks.find_lock("free-resource") is None

    def test_find_returns_lock_record(self, patch_engram_locks):
        """find_lock returns the live lock record."""
        engram_locks.acquire_lock("R12", "session-Q", ttl_seconds=120)
        found = engram_locks.find_lock("R12")

        assert found is not None
        assert found["resource"] == "R12"
        assert found["session_id"] == "session-Q"


# ---------------------------------------------------------------------------
# Portability tests
# ---------------------------------------------------------------------------

class TestPortability:
    def test_module_importable_without_engram_binary(self, monkeypatch):
        """Module loads even when engram binary is absent."""
        monkeypatch.setenv("ENGRAM_BIN", "/nonexistent/engram-binary")
        import importlib
        importlib.reload(engram_locks)

    def test_grace_seconds_is_positive_integer(self):
        """GRACE_SECONDS constant is a positive int (protocol guarantee)."""
        assert isinstance(engram_locks.GRACE_SECONDS, int)
        assert engram_locks.GRACE_SECONDS > 0

    def test_is_stale_with_unparseable_timestamp(self, patch_engram_locks):
        """_is_stale treats an unparseable timestamp as infinitely old (stale)."""
        bad_record = {
            "resource": "R-bad",
            "session_id": "s",
            "heartbeat_at": "not-a-timestamp",
            "ttl_seconds": 300,
        }
        assert engram_locks._is_stale(bad_record) is True
