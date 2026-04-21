"""Exercised chaos test for hooks/agent-bus-monitor.sh (ADR-041 Wave B).

Tier: B (Infrastructure — Valkey bus monitor, feature-gated)
Trigger: SessionStart

Contract:
  - AGENT_BUS_ENABLED != true → exit 0 silently (default OFF).
  - AGENT_BUS_ENABLED=true + no redis-cli → exit 0 with stderr advisory.
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

_HOOK = HOOKS_DIR / "agent-bus-monitor.sh"
_COMPONENT = "hooks/agent-bus-monitor.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="agent-bus-monitor.sh not found")
def test_agent_bus_monitor_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="agent-bus-monitor.sh not found")
def test_agent_bus_monitor_disabled_exits_zero(tmp_path: Path):
    """Default disabled state must short-circuit."""
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"AGENT_BUS_ENABLED": "false"})
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "disabled_exits_zero", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="agent-bus-monitor.sh not found")
def test_agent_bus_monitor_enabled_unreachable_valkey_graceful(tmp_path: Path):
    """Enabled but Valkey unreachable (bogus host) → exit 0, no crash."""
    setup_project(tmp_path)
    # Point VALKEY_HOST at a guaranteed-unroutable address so redis-cli (if
    # installed) can't connect. The hook must still exit 0 — operational
    # blindness is acceptable, a crash is not.
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={
            "AGENT_BUS_ENABLED": "true",
            "VALKEY_HOST": "127.0.0.1",
            "VALKEY_PORT": "1",  # reserved port, nothing listens
        },
        timeout=8,
    )
    assert result.returncode == 0, (
        f"unreachable Valkey must not crash: exit={result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "enabled_unreachable_valkey_graceful", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="agent-bus-monitor.sh not found")
def test_agent_bus_monitor_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={"SO_KILLSWITCH": "1", "AGENT_BUS_ENABLED": "true"},
    )
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
