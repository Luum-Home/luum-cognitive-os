"""Exercised chaos test for hooks/session-hygiene.sh (ADR-041 Wave B).

Tier: B (Infrastructure — Stop hook, cleans stale state)
Trigger: Stop

Contract:
  - Python-driven hygiene with 30s timeout.
  - Missing lib.session_hygiene must not crash the hook.
  - Always exits 0 (|| true guard).
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

_HOOK = HOOKS_DIR / "session-hygiene.sh"
_COMPONENT = "hooks/session-hygiene.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="session-hygiene.sh not found")
def test_session_hygiene_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="session-hygiene.sh not found")
def test_session_hygiene_runs_and_exits_zero(tmp_path: Path):
    """Even with no lib/ in tmp_path, the hook must exit 0."""
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, timeout=35)
    assert result.returncode == 0, (
        f"hygiene must never block session end: exit={result.returncode}\n"
        f"stderr: {result.stderr[:400]}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "runs_and_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="session-hygiene.sh not found")
def test_session_hygiene_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"}, timeout=5)
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
