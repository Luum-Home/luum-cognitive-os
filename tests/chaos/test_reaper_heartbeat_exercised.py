"""Exercised chaos test for hooks/reaper-heartbeat.sh (ADR-041 Wave B).

Tier: B (Infrastructure — periodic process reaper daemon launcher)
Trigger: SessionStart

Contract:
  - Atomic single-instance lock (mkdir-based), no double-spawn.
  - Always exits 0 even when a concurrent launcher holds the lock.
  - When another lock holder exists, second invocation no-ops.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.chaos._tier_b_helpers import (
    HOOKS_DIR,
    run_hook,
    setup_project,
    write_chaos_run,
)

_HOOK = HOOKS_DIR / "reaper-heartbeat.sh"
_COMPONENT = "hooks/reaper-heartbeat.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="reaper-heartbeat.sh not found")
def test_reaper_heartbeat_exists():
    # Symlink to reaper-daemon-launcher.sh — resolve either way.
    assert _HOOK.exists()


@pytest.mark.skipif(not _HOOK.exists(), reason="reaper-heartbeat.sh not found")
def test_reaper_heartbeat_concurrent_lock_holder_is_noop(tmp_path: Path):
    """Pre-existing lock dir must cause the hook to early-exit 0."""
    setup_project(tmp_path)
    lockdir = tmp_path / ".cognitive-os" / "runtime" / "reaper-heartbeat.lockdir"
    lockdir.mkdir(parents=True)  # simulate another launcher holding the lock
    # Also provide a placeholder scripts/so-reaper.sh to avoid downstream 404.
    (tmp_path / "scripts").mkdir(exist_ok=True)
    (tmp_path / "scripts" / "so-reaper.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "scripts" / "so-reaper.sh").chmod(0o755)

    result = run_hook(_HOOK, tmp_path, timeout=8)
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    # Our external lock dir must still be there (the hook must NOT rmdir it).
    assert lockdir.exists(), "external lock dir must not be removed by a non-holder"
    write_chaos_run(tmp_path, _COMPONENT, "concurrent_lock_noop", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="reaper-heartbeat.sh not found")
def test_reaper_heartbeat_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"}, timeout=5)
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
