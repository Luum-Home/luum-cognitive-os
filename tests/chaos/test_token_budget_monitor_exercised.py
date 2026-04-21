"""Exercised chaos test for hooks/token-budget-monitor.sh (ADR-041 Wave B).

Tier: B (Infrastructure — token consumption monitor, blocks at >95%)
Trigger: PreToolUse Agent

Contract:
  - RATE_LIMIT_OVERRIDE=true short-circuits with exit 0.
  - Empty cost-events.jsonl means 0% usage → exit 0.
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

_HOOK = HOOKS_DIR / "token-budget-monitor.sh"
_COMPONENT = "hooks/token-budget-monitor.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="token-budget-monitor.sh not found")
def test_token_budget_monitor_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="token-budget-monitor.sh not found")
def test_token_budget_monitor_override_short_circuits(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"RATE_LIMIT_OVERRIDE": "true"})
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "override_short_circuits", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="token-budget-monitor.sh not found")
def test_token_budget_monitor_empty_cost_events_exits_zero(tmp_path: Path):
    """No cost-events.jsonl → 0% usage → exit 0 (no BLOCK)."""
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path)
    # Per contract: <50% is INFO (silent), >95% is BLOCK(2). Zero usage is <50%.
    assert result.returncode == 0, (
        f"expected exit 0 at 0% usage, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "empty_cost_events_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="token-budget-monitor.sh not found")
def test_token_budget_monitor_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
