"""Unit tests for OrchestratorCapabilities."""

import os
from unittest.mock import MagicMock, patch

import pytest

from lib.orchestrator_capabilities import OrchestratorCapabilities

CommMode = OrchestratorCapabilities.CommMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_caps(*, executor: bool = False, valkey: bool = False, docker: bool = False, container: bool = False) -> OrchestratorCapabilities:
    caps = OrchestratorCapabilities()
    caps._executor_available = executor
    caps._valkey_available = valkey
    caps._docker_running = docker
    caps._valkey_container_exists = container
    caps._mode = CommMode.CONNECTED if (executor and valkey) else CommMode.FIRE_AND_FORGET
    return caps


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

def test_default_fire_and_forget():
    """Without env vars and no Valkey, mode is FIRE_AND_FORGET."""
    with (
        patch.dict(os.environ, {}, clear=False),
        patch.object(OrchestratorCapabilities, "_check_executor", return_value=False),
        patch.object(OrchestratorCapabilities, "_check_valkey", return_value=False),
        patch.object(OrchestratorCapabilities, "_check_docker", return_value=False),
    ):
        caps = OrchestratorCapabilities().detect()
    assert caps.mode == CommMode.FIRE_AND_FORGET


def test_executor_env_detected():
    """ORCHESTRATOR_MODE=executor → executor_available=True."""
    with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "executor"}):
        caps = OrchestratorCapabilities()
        assert caps._check_executor() is True


def test_valkey_not_running():
    """No Valkey listening → valkey_available=False."""
    with patch("socket.create_connection", side_effect=OSError):
        caps = OrchestratorCapabilities()
        assert caps._check_valkey() is False


def test_connected_mode_both_available():
    """executor + valkey → CONNECTED mode."""
    with (
        patch.object(OrchestratorCapabilities, "_check_executor", return_value=True),
        patch.object(OrchestratorCapabilities, "_check_valkey", return_value=True),
        patch.object(OrchestratorCapabilities, "_check_docker", return_value=False),
    ):
        caps = OrchestratorCapabilities().detect()
    assert caps.mode == CommMode.CONNECTED


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def test_fire_and_forget_capabilities():
    caps = _make_caps(executor=False, valkey=False)
    assert caps.can_send_to_agent is False
    assert caps.can_receive_heartbeat is False
    assert caps.can_ask_questions is False
    assert caps.can_stop_gracefully is False


def test_connected_capabilities():
    caps = _make_caps(executor=True, valkey=True)
    assert caps.can_send_to_agent is True
    assert caps.can_receive_heartbeat is True
    assert caps.can_ask_questions is True
    assert caps.can_stop_gracefully is True


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def test_format_status_fire_and_forget():
    caps = _make_caps(executor=False, valkey=False)
    status = caps.format_status()
    assert "FIRE_AND_FORGET" in status
    assert "❌" in status


def test_format_status_connected():
    caps = _make_caps(executor=True, valkey=True)
    status = caps.format_status()
    assert "CONNECTED" in status
    assert "✅" in status


def test_launch_advice_fire_and_forget():
    caps = _make_caps(executor=False, valkey=False)
    advice = caps.get_agent_launch_advice()
    assert "ALL context" in advice


def test_launch_advice_connected():
    caps = _make_caps(executor=True, valkey=True)
    advice = caps.get_agent_launch_advice()
    assert "bidirectional" in advice


def test_format_capabilities_contains_mode():
    for executor, valkey in [(False, False), (True, True)]:
        caps = _make_caps(executor=executor, valkey=valkey)
        report = caps.format_capabilities()
        assert "Mode:" in report


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def test_serialization():
    caps = _make_caps(executor=True, valkey=True, docker=True, container=True)
    d = caps.to_dict()
    assert d["mode"] == CommMode.CONNECTED
    assert d["valkey_available"] is True
    assert d["executor_available"] is True
    assert d["capabilities"]["send_to_agent"] is True
    assert d["capabilities"]["heartbeat"] is True


def test_serialization_fire_and_forget():
    caps = _make_caps(executor=False, valkey=False)
    d = caps.to_dict()
    assert d["mode"] == CommMode.FIRE_AND_FORGET
    assert d["capabilities"]["send_to_agent"] is False


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_detect_idempotent():
    """Calling detect() twice gives the same result."""
    with (
        patch.object(OrchestratorCapabilities, "_check_executor", return_value=False),
        patch.object(OrchestratorCapabilities, "_check_valkey", return_value=False),
        patch.object(OrchestratorCapabilities, "_check_docker", return_value=False),
    ):
        caps = OrchestratorCapabilities()
        caps.detect()
        mode_first = caps.mode
        caps.detect()  # second call should be no-op
        assert caps.mode == mode_first


# ---------------------------------------------------------------------------
# Guard: accessing properties before detect()
# ---------------------------------------------------------------------------

def test_property_before_detect_raises():
    caps = OrchestratorCapabilities()
    with pytest.raises(RuntimeError, match="detect()"):
        _ = caps.mode
