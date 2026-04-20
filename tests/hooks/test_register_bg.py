"""Behavioral tests for hooks/_lib/register-bg.sh.

Tests invoke the bash function directly via a wrapper script and verify that
the process registry receives the expected records. All tests use tmp_path and
COGNITIVE_OS_PROJECT_DIR override so no real project state is touched.

Isolation: each test overrides COGNITIVE_OS_PROJECT_DIR to a fresh tmp directory
and reloads lib.process_registry to pick up the new path.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTER_BG = PROJECT_ROOT / "hooks" / "_lib" / "register-bg.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_registry(project_dir: Path):
    """Force-reload process_registry with the given COGNITIVE_OS_PROJECT_DIR."""
    os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    if "lib.process_registry" in sys.modules:
        del sys.modules["lib.process_registry"]
    sys.path.insert(0, str(PROJECT_ROOT))
    import lib.process_registry as reg  # noqa: PLC0415
    return reg


def _run_register_bg(
    tmp_path: Path,
    owner: str,
    ttl: int,
    kind: str,
    *command: str,
    timeout: int = 8,
) -> subprocess.CompletedProcess:
    """Source register-bg.sh and call _register_bg in a subshell, return stdout (PID)."""
    script = (
        f'source "{REGISTER_BG}" && '
        f'_register_bg "{owner}" {ttl} "{kind}" {" ".join(command)}'
    )
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegisterBgShell:
    """Shell-level tests for _register_bg function."""

    def test_register_bg_exits_zero(self, tmp_path):
        result = _run_register_bg(tmp_path, "test-hook", 5, "short_lived", "sleep", "0.1")
        assert result.returncode == 0, result.stderr

    def test_register_bg_prints_pid(self, tmp_path):
        """_register_bg must echo the background PID to stdout."""
        result = _run_register_bg(tmp_path, "test-hook", 5, "short_lived", "sleep", "0.1")
        pid_str = result.stdout.strip()
        assert pid_str.isdigit(), f"Expected a PID on stdout, got: {pid_str!r}"

    def test_pid_appears_in_processes_live_json(self, tmp_path):
        """After _register_bg, the spawned PID should appear in processes-live.json."""
        result = _run_register_bg(tmp_path, "test-hook", 60, "short_lived", "sleep", "1")
        pid_str = result.stdout.strip()
        assert pid_str.isdigit(), f"Expected a PID on stdout, got: {pid_str!r}"
        pid = int(pid_str)

        # The registration happens in a background subshell; give it up to 1 second.
        live_json = tmp_path / ".cognitive-os" / "runtime" / "processes-live.json"
        deadline = time.monotonic() + 2.0
        found = False
        while time.monotonic() < deadline:
            if live_json.exists():
                try:
                    records = json.loads(live_json.read_text())
                    if any(r.get("pid") == pid for r in records):
                        found = True
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
            time.sleep(0.05)

        assert found, (
            f"PID {pid} not found in processes-live.json after 2s. "
            f"File contents: {live_json.read_text() if live_json.exists() else '<missing>'}"
        )

    def test_live_record_has_correct_owner_and_kind(self, tmp_path):
        """The registry record must carry the correct owner, kind, and ttl fields."""
        result = _run_register_bg(tmp_path, "my-owner-hook", 42, "short_lived", "sleep", "1")
        pid_str = result.stdout.strip()
        assert pid_str.isdigit()
        pid = int(pid_str)

        live_json = tmp_path / ".cognitive-os" / "runtime" / "processes-live.json"
        deadline = time.monotonic() + 2.0
        record = None
        while time.monotonic() < deadline:
            if live_json.exists():
                try:
                    records = json.loads(live_json.read_text())
                    for r in records:
                        if r.get("pid") == pid:
                            record = r
                            break
                except (json.JSONDecodeError, TypeError):
                    pass
            if record:
                break
            time.sleep(0.05)

        assert record is not None, f"PID {pid} not registered within 2s"
        assert record["owner"] == "my-owner-hook", f"owner mismatch: {record}"
        assert record["kind"] == "short_lived", f"kind mismatch: {record}"
        assert record["ttl_seconds"] == 42, f"ttl_seconds mismatch: {record}"


class TestRegisterBgPythonCleanup:
    """Python lib.process_registry cleanup_expired removes expired records."""

    def test_cleanup_expired_removes_finished_process(self, tmp_path, monkeypatch):
        """Expired records (ttl_seconds=0, registered_at in the past) are removed by cleanup."""
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
        reg = _reload_registry(tmp_path)

        # Register a record with ttl=0 so it immediately expires.
        reg.register(pid=99991, owner="expiry-test", ttl_seconds=0, kind="short_lived")

        # Force registered_at to the past so it's definitely expired.
        live = reg._load_live()
        for r in live:
            if r.pid == 99991:
                r.registered_at = time.time() - 10.0  # 10 seconds ago
        reg._save_live(live)

        reg.cleanup_expired()

        remaining = reg.list_live()
        assert all(r.pid != 99991 for r in remaining), (
            f"Expired PID 99991 still in registry: {remaining}"
        )

    def test_cleanup_keeps_non_expired_records(self, tmp_path, monkeypatch):
        """cleanup_expired must NOT remove records that are still within their TTL."""
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
        reg = _reload_registry(tmp_path)

        reg.register(pid=99992, owner="long-lived-test", ttl_seconds=3600, kind="detached_daemon")
        reg.cleanup_expired()

        remaining = reg.list_live()
        assert any(r.pid == 99992 for r in remaining), (
            f"Non-expired PID 99992 was incorrectly removed: {remaining}"
        )

    def test_register_and_deregister_round_trip(self, tmp_path, monkeypatch):
        """register + deregister removes the record; list_live is empty afterwards."""
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
        reg = _reload_registry(tmp_path)

        reg.register(pid=88881, owner="round-trip-test", ttl_seconds=60, kind="short_lived")
        assert any(r.pid == 88881 for r in reg.list_live())

        removed = reg.deregister(88881)
        assert removed is True
        assert all(r.pid != 88881 for r in reg.list_live())
