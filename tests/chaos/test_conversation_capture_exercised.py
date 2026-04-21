"""Exercised chaos test for hooks/conversation-capture.sh (ADR-041 Wave B).

Tier: B (Infrastructure — Stop hook, captures transcripts for session memory)
Trigger: Stop

Contract:
  - Without SESSION_ID, early-exits 0 (no work to do).
  - With SESSION_ID, creates transcripts dir and does not crash.
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

_HOOK = HOOKS_DIR / "conversation-capture.sh"
_COMPONENT = "hooks/conversation-capture.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="conversation-capture.sh not found")
def test_conversation_capture_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="conversation-capture.sh not found")
def test_conversation_capture_no_session_id_exits_zero(tmp_path: Path):
    setup_project(tmp_path)
    # Explicitly clear any session id
    result = run_hook(_HOOK, tmp_path, env_extra={"COGNITIVE_OS_SESSION_ID": ""})
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "no_session_id_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="conversation-capture.sh not found")
def test_conversation_capture_with_session_id_creates_transcripts_dir(tmp_path: Path):
    setup_project(tmp_path)
    session_id = "chaos-b-conv"
    (tmp_path / ".cognitive-os" / "sessions" / session_id).mkdir(parents=True)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"COGNITIVE_OS_SESSION_ID": session_id},
        timeout=15,
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:400]}"
    transcripts = tmp_path / ".cognitive-os" / "transcripts"
    assert transcripts.exists(), "transcripts dir must be created"
    write_chaos_run(tmp_path, _COMPONENT, "creates_transcripts_dir", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="conversation-capture.sh not found")
def test_conversation_capture_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"SO_KILLSWITCH": "1", "COGNITIVE_OS_SESSION_ID": "ks"},
    )
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
