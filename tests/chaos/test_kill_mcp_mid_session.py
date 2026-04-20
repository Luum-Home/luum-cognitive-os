"""ADR-028 D6 — Chaos test 1: SIGKILL an MCP-like subprocess mid-session.

Contract: the process registry must survive the death of a registered process.
- list_live() still returns without exception after the child is killed.
- The dead PID can be deregister()ed without crash.
- os.kill(dead_pid, 0) raises ProcessLookupError, proving the process truly died.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so lib imports resolve.
_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))


@pytest.fixture()
def isolated_registry(tmp_path, monkeypatch):
    """Point process_registry at a tmp runtime dir so real .cognitive-os/ is untouched."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    # Force the module to re-resolve its runtime dir on next call.
    import importlib
    import lib.process_registry as _reg
    importlib.reload(_reg)
    yield _reg
    importlib.reload(_reg)  # restore module-level state after the test


def test_registry_survives_sigkill(isolated_registry, tmp_path):
    """Registry must not panic when a registered PID is SIGKILLed externally."""
    reg = isolated_registry

    # Spawn a long-lived child that does nothing (simulates an MCP server).
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = child.pid

    try:
        # Register the child in the registry as a detached daemon (like an MCP server).
        rec = reg.register(pid, "mock-mcp", 60, "detached_daemon")
        assert rec.pid == pid

        # Confirm it's actually alive before we kill it.
        assert reg._is_alive(pid), "child should be alive before SIGKILL"

        # SIGKILL from outside — simulates the MCP server crashing mid-session.
        os.kill(pid, signal.SIGKILL)
        child.wait(timeout=5)  # reap the zombie

        # Confirm the process truly died — this is the proof the test isn't a no-op.
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)

        # --- The registry must survive the death ---

        # 1. list_live() must not raise.
        live = reg.list_live()
        assert isinstance(live, list)

        # 2. The PID is still in the registry (we didn't auto-deregister it).
        assert any(r.pid == pid for r in live), (
            "dead PID should still appear in registry until explicitly deregistered"
        )

        # 3. deregister() must not crash on a dead PID.
        result = reg.deregister(pid)
        assert result is True, "deregister should return True for a known PID"

        # 4. After deregistration the PID is gone from live list.
        live_after = reg.list_live()
        assert not any(r.pid == pid for r in live_after)

    finally:
        # Teardown: ensure child is fully dead even if the test failed early.
        try:
            child.kill()
        except (ProcessLookupError, OSError):
            pass
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
