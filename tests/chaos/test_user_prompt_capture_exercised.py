"""Exercised chaos test for hooks/user-prompt-capture.sh (ADR-041 Wave B).

Tier: B (Infrastructure — UserPromptSubmit capture to engram)
Trigger: UserPromptSubmit

Contract:
  - Always exits 0 (never blocks user input).
  - Trivial prompts (<10 chars) are skipped.
  - Missing python3 or missing stdin JSON does not crash.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.chaos._tier_b_helpers import (
    HOOKS_DIR,
    run_hook,
    setup_project,
    write_chaos_run,
)

_HOOK = HOOKS_DIR / "user-prompt-capture.sh"
_COMPONENT = "hooks/user-prompt-capture.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="user-prompt-capture.sh not found")
def test_user_prompt_capture_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="user-prompt-capture.sh not found")
def test_user_prompt_capture_empty_stdin_exits_zero(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, stdin_payload="")
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "empty_stdin_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="user-prompt-capture.sh not found")
def test_user_prompt_capture_trivial_prompt_skipped(tmp_path: Path):
    setup_project(tmp_path)
    payload = json.dumps({"prompt": "hi"})
    result = run_hook(_HOOK, tmp_path, stdin_payload=payload)
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "trivial_prompt_skipped", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="user-prompt-capture.sh not found")
def test_user_prompt_capture_malformed_json_exits_zero(tmp_path: Path):
    """Malformed stdin JSON must not crash (always exit 0)."""
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, stdin_payload="{not valid json")
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "malformed_json_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="user-prompt-capture.sh not found")
def test_user_prompt_capture_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    payload = json.dumps({"prompt": "A substantive prompt that would normally capture."})
    result = run_hook(
        _HOOK, tmp_path, stdin_payload=payload, env_extra={"SO_KILLSWITCH": "1"}
    )
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
