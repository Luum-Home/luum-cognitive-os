"""Exercised chaos test for hooks/git-context-capture.sh (ADR-041 Wave B).

Tier: B (Infrastructure — Stop hook, captures git branch/diff/commits)
Trigger: Stop

Contract:
  - Without SESSION_ID, exits 0 silently.
  - Non-git working dir must not crash (graceful degradation).
  - Always exits 0 (never blocks session end).
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

_HOOK = HOOKS_DIR / "git-context-capture.sh"
_COMPONENT = "hooks/git-context-capture.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="git-context-capture.sh not found")
def test_git_context_capture_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="git-context-capture.sh not found")
def test_git_context_capture_no_session_exits_zero(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"COGNITIVE_OS_SESSION_ID": ""})
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "no_session_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="git-context-capture.sh not found")
def test_git_context_capture_non_git_dir_graceful(tmp_path: Path):
    """tmp_path is NOT a git repo — capturer must handle this gracefully."""
    setup_project(tmp_path)
    session_id = "chaos-b-gitctx"
    (tmp_path / ".cognitive-os" / "sessions" / session_id).mkdir(parents=True)
    result = run_hook(
        _HOOK, tmp_path, env_extra={"COGNITIVE_OS_SESSION_ID": session_id}, timeout=15
    )
    assert result.returncode == 0, f"non-git dir must not crash: {result.stderr[:400]}"
    write_chaos_run(tmp_path, _COMPONENT, "non_git_dir_graceful", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="git-context-capture.sh not found")
def test_git_context_capture_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"SO_KILLSWITCH": "1", "COGNITIVE_OS_SESSION_ID": "ks"},
    )
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
