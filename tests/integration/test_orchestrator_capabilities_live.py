"""Integration tests for OrchestratorCapabilities against the live environment.

These tests run against the real Docker/Valkey environment — no mocks.
Tests that require a running Valkey are automatically skipped when unavailable.
"""

import pytest

from lib.orchestrator_capabilities import OrchestratorCapabilities

# ---------------------------------------------------------------------------
# Session-level fixture: detect once, share across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def caps() -> OrchestratorCapabilities:
    return OrchestratorCapabilities().detect()


def _valkey_available() -> bool:
    return OrchestratorCapabilities()._check_valkey()


# ---------------------------------------------------------------------------
# Always-run tests
# ---------------------------------------------------------------------------

def test_live_detect_runs():
    """detect() must not raise in any environment."""
    c = OrchestratorCapabilities().detect()
    assert c.mode in (
        OrchestratorCapabilities.CommMode.FIRE_AND_FORGET,
        OrchestratorCapabilities.CommMode.CONNECTED,
    )


def test_live_format_status(caps):
    status = caps.format_status()
    assert isinstance(status, str)
    assert len(status) > 0
    assert "FIRE_AND_FORGET" in status or "CONNECTED" in status


def test_live_format_capabilities(caps):
    report = caps.format_capabilities()
    assert isinstance(report, str)
    assert "Mode:" in report


def test_live_launch_advice(caps):
    advice = caps.get_agent_launch_advice()
    assert isinstance(advice, str)
    assert len(advice) > 10


def test_live_to_dict(caps):
    d = caps.to_dict()
    assert "mode" in d
    assert "valkey_available" in d
    assert "executor_available" in d
    assert "capabilities" in d
    assert isinstance(d["capabilities"], dict)


def test_live_docker_check(caps):
    """Docker check must return a boolean (True or False — not crash)."""
    assert isinstance(caps._docker_running, bool)


def test_live_executor_check(caps):
    """Executor check reflects env var OR a live executor daemon marker."""
    import os
    from pathlib import Path

    expected = os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor"
    if not expected:
        project = Path(
            os.environ.get(
                "COGNITIVE_OS_PROJECT_DIR",
                os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()),
            )
        )
        state = project / ".cognitive-os" / "runtime" / "orchestrator-mode"
        pid_file = project / ".cognitive-os" / "runtime" / "cos-executor.pid"
        if state.exists() and state.read_text().strip().lower() == "executor":
            try:
                pid = int(pid_file.read_text().strip() or "0")
                if pid > 0:
                    os.kill(pid, 0)
                    expected = True
            except (OSError, ValueError):
                expected = False
    assert caps._executor_available is expected


# ---------------------------------------------------------------------------
# Valkey-dependent tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _valkey_available(), reason="Valkey not running")
def test_valkey_connected_mode(caps):
    """When Valkey is reachable, and executor mode is set, mode is CONNECTED."""
    import os
    if os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor":
        assert caps.mode == OrchestratorCapabilities.CommMode.CONNECTED


@pytest.mark.skipif(not _valkey_available(), reason="Valkey not running")
def test_valkey_capabilities_true(caps):
    """When Valkey is available, valkey_available is True."""
    assert caps._valkey_available is True
