"""Unit tests for lib/file_lock_registry.py -- file-based fallback path.

All tests use the file-based backend by ensuring Valkey is unreachable
(via monkeypatching).  This guarantees deterministic, infrastructure-free tests.

Python 3.9+ compatible.
"""

import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# We import after potentially patching env vars, but the module itself is
# safe to import at top-level -- it only connects lazily.
from lib import file_lock_registry as flr


@pytest.fixture(autouse=True)
def _isolate_lock_dir(tmp_path, monkeypatch):
    """Point the lock directory at a temp location and disable Valkey."""
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    monkeypatch.setenv("COGNITIVE_OS_LOCK_DIR", str(lock_dir))
    # Force file-based fallback by making Valkey unreachable
    monkeypatch.setenv("VALKEY_HOST", "192.0.2.1")  # non-routable TEST-NET
    monkeypatch.setenv("VALKEY_PORT", "1")


@pytest.fixture
def lock_dir(tmp_path) -> Path:
    return tmp_path / "locks"


# -----------------------------------------------------------------------
# Basic acquire / release
# -----------------------------------------------------------------------


class TestAcquireRelease:
    def test_acquire_and_release(self):
        assert flr.acquire_lock("agent-1", "/tmp/foo.py") is True
        assert flr.release_lock("agent-1", "/tmp/foo.py") is True

    def test_check_returns_holder(self):
        flr.acquire_lock("agent-A", "/tmp/bar.py")
        assert flr.check_lock("/tmp/bar.py") == "agent-A"

    def test_check_returns_none_when_unlocked(self):
        assert flr.check_lock("/tmp/nonexistent.py") is None

    def test_acquire_fails_if_held_by_another(self):
        flr.acquire_lock("agent-1", "/tmp/shared.py")
        assert flr.acquire_lock("agent-2", "/tmp/shared.py") is False

    def test_acquire_succeeds_if_held_by_same_agent(self):
        """Same agent re-acquiring should refresh the lock."""
        flr.acquire_lock("agent-1", "/tmp/refresh.py", ttl_seconds=10)
        assert flr.acquire_lock("agent-1", "/tmp/refresh.py", ttl_seconds=20) is True
        # Holder should still be agent-1
        assert flr.check_lock("/tmp/refresh.py") == "agent-1"

    def test_release_fails_for_wrong_agent(self):
        flr.acquire_lock("agent-1", "/tmp/owned.py")
        assert flr.release_lock("agent-2", "/tmp/owned.py") is False
        # Lock should still be held
        assert flr.check_lock("/tmp/owned.py") == "agent-1"

    def test_release_nonexistent_returns_false(self):
        assert flr.release_lock("agent-1", "/tmp/never-locked.py") is False


# -----------------------------------------------------------------------
# TTL expiry
# -----------------------------------------------------------------------


class TestTTLExpiry:
    def test_expired_lock_becomes_available(self, lock_dir):
        flr.acquire_lock("agent-1", "/tmp/expiring.py", ttl_seconds=1)
        time.sleep(1.1)
        # After TTL, another agent should be able to acquire
        assert flr.acquire_lock("agent-2", "/tmp/expiring.py") is True
        assert flr.check_lock("/tmp/expiring.py") == "agent-2"

    def test_check_cleans_expired(self, lock_dir):
        flr.acquire_lock("agent-1", "/tmp/stale.py", ttl_seconds=1)
        time.sleep(1.1)
        assert flr.check_lock("/tmp/stale.py") is None

    def test_cleanup_expired_removes_old_locks(self, lock_dir):
        flr.acquire_lock("agent-1", "/tmp/old1.py", ttl_seconds=1)
        flr.acquire_lock("agent-1", "/tmp/old2.py", ttl_seconds=1)
        flr.acquire_lock("agent-1", "/tmp/fresh.py", ttl_seconds=3600)
        time.sleep(1.1)
        removed = flr.cleanup_expired()
        assert removed == 2
        # Fresh lock should still exist
        assert flr.check_lock("/tmp/fresh.py") == "agent-1"


# -----------------------------------------------------------------------
# wait_for_lock
# -----------------------------------------------------------------------


class TestWaitForLock:
    def test_wait_timeout_returns_false(self):
        flr.acquire_lock("agent-1", "/tmp/blocked.py", ttl_seconds=60)
        # With a very short timeout, agent-2 cannot acquire
        assert flr.wait_for_lock("agent-2", "/tmp/blocked.py", timeout=1) is False

    def test_wait_acquires_when_released(self):
        flr.acquire_lock("agent-1", "/tmp/will-release.py", ttl_seconds=60)

        def _release_later():
            time.sleep(0.5)
            flr.release_lock("agent-1", "/tmp/will-release.py")

        t = threading.Thread(target=_release_later)
        t.start()
        acquired = flr.wait_for_lock("agent-2", "/tmp/will-release.py", timeout=5)
        t.join()
        assert acquired is True
        assert flr.check_lock("/tmp/will-release.py") == "agent-2"


# -----------------------------------------------------------------------
# list_locks
# -----------------------------------------------------------------------


class TestListLocks:
    def test_list_locks_returns_active(self):
        flr.acquire_lock("agent-A", "/tmp/a.py")
        flr.acquire_lock("agent-B", "/tmp/b.py")
        locks = flr.list_locks()
        agents = {l["agent_id"] for l in locks}
        assert "agent-A" in agents
        assert "agent-B" in agents

    def test_list_locks_excludes_expired(self):
        flr.acquire_lock("agent-X", "/tmp/expired.py", ttl_seconds=1)
        time.sleep(1.1)
        locks = flr.list_locks()
        agents = {l["agent_id"] for l in locks}
        assert "agent-X" not in agents


# -----------------------------------------------------------------------
# release_all_for_agent
# -----------------------------------------------------------------------


class TestReleaseAllForAgent:
    def test_release_all(self):
        flr.acquire_lock("agent-Z", "/tmp/z1.py")
        flr.acquire_lock("agent-Z", "/tmp/z2.py")
        flr.acquire_lock("agent-Y", "/tmp/y1.py")
        released = flr.release_all_for_agent("agent-Z")
        assert released == 2
        assert flr.check_lock("/tmp/z1.py") is None
        assert flr.check_lock("/tmp/z2.py") is None
        # Agent-Y should be untouched
        assert flr.check_lock("/tmp/y1.py") == "agent-Y"


# -----------------------------------------------------------------------
# Concurrent acquire
# -----------------------------------------------------------------------


class TestConcurrentAcquire:
    def test_sequential_acquire_second_fails(self):
        """Two sequential acquires by different agents -- second should fail."""
        assert flr.acquire_lock("agent-1", "/tmp/race.py") is True
        assert flr.acquire_lock("agent-2", "/tmp/race.py") is False
        # Only agent-1 holds it
        assert flr.check_lock("/tmp/race.py") == "agent-1"


# -----------------------------------------------------------------------
# File-based fallback works
# -----------------------------------------------------------------------


class TestFileFallback:
    def test_lock_file_created_on_disk(self, lock_dir):
        flr.acquire_lock("agent-disk", "/tmp/disk-test.py")
        lock_files = list(lock_dir.glob("*.json"))
        assert len(lock_files) >= 1
        data = json.loads(lock_files[0].read_text())
        assert data["agent_id"] == "agent-disk"
        assert data["file_path"] == "/tmp/disk-test.py"
        assert "acquired_at" in data
        assert "ttl" in data
