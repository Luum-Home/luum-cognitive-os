"""Exercised chaos test for hooks/session-changelog.sh (ADR-041 Wave B).

Tier: B (Infrastructure — Stop hook, writes session changelog md)
Trigger: Stop

Contract:
  - Without SESSION_ID, exits 0 silently.
  - With SESSION_ID, never blocks session end (always exit 0).
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

_HOOK = HOOKS_DIR / "session-changelog.sh"
_COMPONENT = "hooks/session-changelog.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="session-changelog.sh not found")
def test_session_changelog_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="session-changelog.sh not found")
def test_session_changelog_no_session_exits_zero(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"COGNITIVE_OS_SESSION_ID": ""})
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "no_session_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-changelog.sh not found")
def test_session_changelog_with_session_exits_zero(tmp_path: Path):
    setup_project(tmp_path)
    session_id = "chaos-b-changelog"
    (tmp_path / ".cognitive-os" / "sessions" / session_id).mkdir(parents=True)
    result = run_hook(
        _HOOK, tmp_path, env_extra={"COGNITIVE_OS_SESSION_ID": session_id}, timeout=15
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:400]}"
    write_chaos_run(tmp_path, _COMPONENT, "with_session_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-changelog.sh not found")
def test_session_changelog_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"SO_KILLSWITCH": "1", "COGNITIVE_OS_SESSION_ID": "ks"},
    )
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
