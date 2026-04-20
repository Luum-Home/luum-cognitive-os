"""ADR-028 D6 — Chaos test 2: Hook timeout / reaper integration.

Contract: a short_lived hook registered with a 2-second TTL must be
terminated by cleanup_expired() after 3 seconds.

Behavioral assertions:
- cleanup_expired() returns the expired record in its result list.
- The subprocess is no longer alive after cleanup (poll() returns non-None).
"""
from __future__ import annotations

import importlib
import subprocess
import sys
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))


@pytest.fixture()
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    import lib.process_registry as _reg
    importlib.reload(_reg)
    yield _reg
    importlib.reload(_reg)


def test_hook_timeout_reaper(isolated_registry, tmp_path):
    """Reaper must terminate a short_lived hook whose TTL has expired."""
    reg = isolated_registry

    # Write a "slow hook" script that would run for 120 seconds if not reaped.
    hook_script = tmp_path / "fake_hook.sh"
    hook_script.write_text("#!/bin/bash\nsleep 120\n")
    hook_script.chmod(0o755)

    child = subprocess.Popen(
        [str(hook_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = child.pid

    try:
        # Register with a very short TTL (2 seconds).
        reg.register(pid, "fake-hook", ttl_seconds=2, kind="short_lived")

        # Wait past the TTL.
        time.sleep(3)

        # Run the reaper.
        expired = reg.cleanup_expired()

        # --- Behavioral assertions ---

        # 1. The expired list must contain our PID.
        expired_pids = [r.pid for r in expired]
        assert pid in expired_pids, (
            f"PID {pid} must appear in cleanup_expired() result; got {expired_pids}"
        )

        # 2. Give the OS a moment to deliver SIGTERM/SIGKILL and reap the process.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if child.poll() is not None:
                break
            time.sleep(0.2)

        # poll() returning non-None means the process has exited.
        assert child.poll() is not None, (
            "Subprocess must have terminated after cleanup_expired(); "
            f"poll() = {child.poll()}"
        )

    finally:
        # Ensure cleanup even on test failure.
        try:
            child.kill()
        except (ProcessLookupError, OSError):
            pass
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
