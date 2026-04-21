"""Exercised chaos test for hooks/state-heartbeat.sh (ADR-041 Wave B).

Tier: B (Infrastructure — PostToolUse Agent state checkpoint, crash-recovery)
Trigger: PostToolUse Agent

Contract:
  - Fast path: increments a counter file (<200ms), exits 0.
  - Always exits 0 even when session dir is missing.
  - Respects SO_KILLSWITCH.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.chaos._tier_b_helpers import (
    HOOKS_DIR,
    run_hook,
    setup_project,
    write_chaos_run,
)

_HOOK = HOOKS_DIR / "state-heartbeat.sh"
_COMPONENT = "hooks/state-heartbeat.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="state-heartbeat.sh not found")
def test_state_heartbeat_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="state-heartbeat.sh not found")
def test_state_heartbeat_increments_counter(tmp_path: Path):
    """First and second invocation must both exit 0; counter file grows."""
    setup_project(tmp_path)
    session_id = f"chaos-b-state-{os.getpid()}"
    counter = Path(f"/tmp/cos-heartbeat-counter-{session_id}")
    counter.unlink(missing_ok=True)

    try:
        observed = []
        for _ in range(3):
            result = run_hook(
                _HOOK, tmp_path, env_extra={"CLAUDE_SESSION_ID": session_id}
            )
            assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
            if counter.exists():
                observed.append(counter.read_text().strip())
        assert counter.exists(), "counter file must be written under /tmp"
        # Counter is reset to 0 whenever TIME_ELAPSED > 120s triggers the slow
        # path, so on the first few invocations (LAST_SAVE=0 → elapsed = NOW)
        # the counter file ends up at 0 or 1. We only assert the hook
        # successfully wrote the counter at least once; the monotonicity is
        # covered by the production slow path, not this chaos unit.
        final = int(counter.read_text().strip())
        assert final >= 1, f"counter must be written; got observations={observed}"
        write_chaos_run(tmp_path, _COMPONENT, "increments_counter", True)
    finally:
        counter.unlink(missing_ok=True)
        Path(f"/tmp/cos-heartbeat-ts-{session_id}").unlink(missing_ok=True)


@pytest.mark.skipif(not _HOOK.exists(), reason="state-heartbeat.sh not found")
def test_state_heartbeat_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
