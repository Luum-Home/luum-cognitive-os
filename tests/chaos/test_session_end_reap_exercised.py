"""Exercised chaos test for hooks/session-end-reap.sh (ADR-041 Wave B).

Tier: B (Infrastructure — Stop hook, invokes so-reaper.sh)
Trigger: Stop

Contract:
  - Missing scripts/so-reaper.sh: errors are swallowed (exit 0).
  - Reaper exit=1: session-end-reap must still exit 0 (|| true guard).
  - Respects SO_KILLSWITCH.
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

_HOOK = HOOKS_DIR / "session-end-reap.sh"
_COMPONENT = "hooks/session-end-reap.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="session-end-reap.sh not found")
def test_session_end_reap_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="session-end-reap.sh not found")
def test_session_end_reap_missing_reaper_graceful(tmp_path: Path):
    """No scripts/so-reaper.sh → must swallow the error (|| true) and exit 0."""
    setup_project(tmp_path)
    # Do NOT create scripts/so-reaper.sh.
    result = run_hook(_HOOK, tmp_path, timeout=8)
    assert result.returncode == 0, (
        f"missing reaper must be swallowed: exit={result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "missing_reaper_graceful", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-end-reap.sh not found")
def test_session_end_reap_failing_reaper_swallowed(tmp_path: Path):
    """Reaper exit=1 must be swallowed; hook still exits 0."""
    setup_project(tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    reaper = scripts / "so-reaper.sh"
    reaper.write_text("#!/bin/bash\necho 'simulated reaper failure' >&2\nexit 1\n")
    reaper.chmod(0o755)
    result = run_hook(_HOOK, tmp_path, timeout=8)
    assert result.returncode == 0, (
        f"failing reaper must not propagate: exit={result.returncode}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "failing_reaper_swallowed", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-end-reap.sh not found")
def test_session_end_reap_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"}, timeout=5)
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
