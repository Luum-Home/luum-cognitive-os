"""Contract tests for lib/process_registry.py — ADR-028 D1.B."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the registry to a temporary project directory."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    # Reload the module so cached _project_root() picks up the new env var
    if "lib.process_registry" in sys.modules:
        del sys.modules["lib.process_registry"]
    # Also evict metric_event if it was cached (it picks up paths at import)
    # metric_event itself uses open() paths passed in, so no reload needed.
    return tmp_path


def _import_registry(tmp_project: Path):
    """Import process_registry fresh after the env var has been set."""
    import importlib

    if "lib.process_registry" in sys.modules:
        del sys.modules["lib.process_registry"]
    import lib.process_registry as reg

    return reg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterDeregister:
    """register / deregister round-trip."""

    def test_register_creates_live_record(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        rec = reg.register(12345, owner="test-hook.sh", ttl_seconds=60, kind="short_lived")
        assert rec.pid == 12345
        assert rec.owner == "test-hook.sh"
        assert rec.kind == "short_lived"

        live = reg.list_live()
        assert any(r.pid == 12345 for r in live)

    def test_deregister_removes_record(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        reg.register(22222, owner="test-hook.sh", ttl_seconds=60, kind="short_lived")
        removed = reg.deregister(22222)
        assert removed is True
        assert all(r.pid != 22222 for r in reg.list_live())

    def test_deregister_missing_returns_false(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        assert reg.deregister(99999) is False

    def test_register_deduplicates_by_pid(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        reg.register(33333, owner="hook-a.sh", ttl_seconds=30, kind="short_lived")
        reg.register(33333, owner="hook-b.sh", ttl_seconds=60, kind="short_lived")
        live = reg.list_live()
        matching = [r for r in live if r.pid == 33333]
        assert len(matching) == 1
        # Second registration wins
        assert matching[0].owner == "hook-b.sh"


class TestKindValidation:
    """register rejects invalid kind values."""

    def test_invalid_kind_raises_value_error(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        with pytest.raises(ValueError, match="kind must be one of"):
            reg.register(44444, owner="hook.sh", ttl_seconds=60, kind="invalid_kind")

    def test_valid_kinds_accepted(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        rec1 = reg.register(55551, owner="hook.sh", ttl_seconds=60, kind="short_lived")
        rec2 = reg.register(55552, owner="hook.sh", ttl_seconds=600, kind="detached_daemon")
        assert rec1.kind == "short_lived"
        assert rec2.kind == "detached_daemon"


class TestCleanupExpired:
    """cleanup_expired behaviour."""

    def test_no_expired_returns_empty(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        reg.register(66666, owner="hook.sh", ttl_seconds=3600, kind="short_lived")
        expired = reg.cleanup_expired(dry_run=True)
        assert expired == []

    def test_expired_short_lived_returned(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        # Register with ttl=1 and backdate registered_at so it's already expired
        rec = reg.register(77777, owner="hook.sh", ttl_seconds=1, kind="short_lived")
        # Manually backdate the live record to force expiry without sleeping
        live = reg._load_live()
        for r in live:
            if r.pid == 77777:
                r.registered_at = time.time() - 10  # 10 s ago → expired
        reg._save_live(live)

        expired = reg.cleanup_expired(dry_run=True)
        assert any(r.pid == 77777 for r in expired)

    def test_detached_daemon_never_reaped(self, tmp_project: Path) -> None:
        """detached_daemon is whitelisted — cleanup_expired must never return it."""
        reg = _import_registry(tmp_project)
        rec = reg.register(88888, owner="daemon.sh", ttl_seconds=1, kind="detached_daemon")
        # Backdate to force expiry
        live = reg._load_live()
        for r in live:
            if r.pid == 88888:
                r.registered_at = time.time() - 100
        reg._save_live(live)

        expired = reg.cleanup_expired(dry_run=True)
        assert all(r.pid != 88888 for r in expired)

    def test_cleanup_does_not_kill_unregistered_pid(self, tmp_project: Path) -> None:
        """Safe-kill: cleanup_expired only touches registry entries."""
        reg = _import_registry(tmp_project)
        # Register a real, long-lived process (our own PID) as short_lived but
        # with a far-future TTL so it's not expired → cleanup_expired returns []
        # and os.kill is never called.
        my_pid = os.getpid()
        reg.register(my_pid, owner="self-test", ttl_seconds=3600, kind="short_lived")

        killed_pids: list[int] = []
        original_kill = os.kill

        def mock_kill(pid: int, sig: int) -> None:
            killed_pids.append(pid)

        with patch("os.kill", side_effect=mock_kill):
            expired = reg.cleanup_expired(dry_run=False)

        # Nothing expired → our PID was never sent a signal
        assert my_pid not in killed_pids
        assert expired == []


class TestAtomicWrite:
    """processes-live.json is valid JSON after a successful save."""

    def test_live_json_is_valid_after_register(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        reg.register(11111, owner="hook.sh", ttl_seconds=30, kind="short_lived")

        live_json = tmp_project / ".cognitive-os" / "runtime" / "processes-live.json"
        assert live_json.is_file()
        data = json.loads(live_json.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert any(r["pid"] == 11111 for r in data)


class TestDetectOrphans:
    """detect_orphans returns empty when no matching ps entries exist."""

    def test_no_matching_commands_returns_empty(self, tmp_project: Path) -> None:
        reg = _import_registry(tmp_project)
        # Use a basename that will never appear in a real ps output
        result = reg.detect_orphans(["__nonexistent_hook_xyz_abc__.sh"])
        assert result == []

    def test_registered_pid_not_reported_as_orphan(self, tmp_project: Path) -> None:
        """A PID present in the registry must not be flagged as an orphan."""
        reg = _import_registry(tmp_project)
        my_pid = os.getpid()
        # Find a fragment of our own command that ps will show
        ps_out = subprocess.run(
            ["ps", "-p", str(my_pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        )
        if ps_out.returncode != 0 or not ps_out.stdout.strip():
            pytest.skip("Cannot inspect own process via ps")

        cmd_fragment = ps_out.stdout.strip().split()[-1]  # last token of command
        reg.register(my_pid, owner="self-test", ttl_seconds=3600, kind="short_lived")

        orphans = reg.detect_orphans([cmd_fragment])
        # Our PID is registered → must NOT appear in orphans
        assert all(o["pid"] != my_pid for o in orphans)
