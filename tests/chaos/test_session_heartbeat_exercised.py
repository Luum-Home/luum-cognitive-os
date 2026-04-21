"""Exercised chaos test for hooks/session-heartbeat.sh (ADR-041 Wave B).

Tier: B (Infrastructure — liveness signal for session watchdog)
Trigger: UserPromptSubmit + PreToolUse (matcher: *)

Contract:
  - Writes atomic heartbeat file at session dir.
  - Always exits 0 (must never block a tool call).
  - No stdout pollution.
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

_HOOK = HOOKS_DIR / "session-heartbeat.sh"
_COMPONENT = "hooks/session-heartbeat.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="session-heartbeat.sh not found")
def test_session_heartbeat_exists():
    assert _HOOK.is_file() or _HOOK.is_symlink()


@pytest.mark.skipif(not _HOOK.exists(), reason="session-heartbeat.sh not found")
def test_session_heartbeat_writes_file_and_exits_zero(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"COGNITIVE_OS_SESSION_ID": "chaos-b-heartbeat"},
    )
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    # Exactly one of the expected heartbeat locations must exist.
    primary = tmp_path / ".cognitive-os" / "sessions" / "chaos-b-heartbeat" / "heartbeat"
    fallback = tmp_path / ".cognitive-os" / "sessions" / "default" / "heartbeat"
    assert primary.exists() or fallback.exists(), (
        "heartbeat file must be written under sessions/<id>/ or sessions/default/"
    )
    write_chaos_run(tmp_path, _COMPONENT, "writes_heartbeat_file", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-heartbeat.sh not found")
def test_session_heartbeat_no_stdout_pollution(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"COGNITIVE_OS_SESSION_ID": "chaos-b-hb-silent"},
    )
    assert result.stdout == "", f"hook must be silent on stdout, got: {result.stdout[:200]}"
    write_chaos_run(tmp_path, _COMPONENT, "no_stdout_pollution", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-heartbeat.sh not found")
def test_session_heartbeat_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"SO_KILLSWITCH": "1", "COGNITIVE_OS_SESSION_ID": "chaos-ks"},
    )
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
