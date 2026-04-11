"""Unit tests for lib/auto_executor.py.

These tests run regardless of Valkey availability — they mock the TCP check.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_module():
    """Fresh import (module may cache env-var state)."""
    import importlib
    import lib.auto_executor as m
    importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# check_and_activate
# ---------------------------------------------------------------------------

class TestCheckAndActivate:
    def test_check_no_valkey(self):
        """Returns fire_and_forget when no Valkey is reachable."""
        import lib.auto_executor as m
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=False):
                result = m.AutoExecutor.check_and_activate()
        assert result["mode"] == "fire_and_forget"
        assert result["valkey_available"] is False

    def test_check_with_valkey(self):
        """Returns connected when Valkey is reachable."""
        import lib.auto_executor as m
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=True):
                result = m.AutoExecutor.check_and_activate()
        assert result["mode"] == "connected"
        assert result["valkey_available"] is True

    def test_auto_activated_flag(self):
        """auto_activated=True when Valkey is up and ORCHESTRATOR_MODE was not set."""
        import lib.auto_executor as m
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=True):
                result = m.AutoExecutor.check_and_activate()
        assert result["auto_activated"] is True

    def test_not_auto_activated_when_already_set(self):
        """auto_activated=False when ORCHESTRATOR_MODE was already 'executor'."""
        import lib.auto_executor as m
        with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "executor"}):
            with patch.object(m, "_is_valkey_reachable", return_value=True):
                result = m.AutoExecutor.check_and_activate()
        assert result["auto_activated"] is False

    def test_not_auto_activated_without_valkey(self):
        """auto_activated=False when Valkey is not reachable."""
        import lib.auto_executor as m
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=False):
                result = m.AutoExecutor.check_and_activate()
        assert result["auto_activated"] is False

    def test_message_present(self):
        """Result dict always contains a non-empty message."""
        import lib.auto_executor as m
        with patch.object(m, "_is_valkey_reachable", return_value=False):
            result = m.AutoExecutor.check_and_activate()
        assert result.get("message")


# ---------------------------------------------------------------------------
# should_use_executor
# ---------------------------------------------------------------------------

class TestShouldUseExecutor:
    def test_should_use_executor_env_var_set(self):
        """Returns True when ORCHESTRATOR_MODE=executor."""
        m = _import_module()
        with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "executor"}):
            assert m.AutoExecutor.should_use_executor() is True

    def test_should_use_executor_env_var_unset(self):
        """Returns False when ORCHESTRATOR_MODE is not set."""
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert m.AutoExecutor.should_use_executor() is False

    def test_should_use_executor_case_insensitive(self):
        """Handles EXECUTOR (uppercase) variant."""
        m = _import_module()
        with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "EXECUTOR"}):
            assert m.AutoExecutor.should_use_executor() is True


# ---------------------------------------------------------------------------
# get_launch_function
# ---------------------------------------------------------------------------

class TestGetLaunchFunction:
    def test_get_launch_function_fire_and_forget(self):
        """Returns None in fire-and-forget mode."""
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert m.AutoExecutor.get_launch_function() is None

    def test_get_launch_function_connected(self):
        """Returns a callable when executor mode is active and lib is available."""
        m = _import_module()
        mock_delegate = MagicMock()
        with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "executor"}):
            with patch.dict("sys.modules", {"lib.orchestrator_mode": MagicMock(delegate_task=mock_delegate)}):
                fn = m.AutoExecutor.get_launch_function()
        assert fn is not None
        assert callable(fn)


# ---------------------------------------------------------------------------
# format_launch_advice
# ---------------------------------------------------------------------------

class TestFormatLaunchAdvice:
    def test_format_advice_fire_and_forget(self):
        """Advice mentions 'Agent tool' in fire-and-forget mode."""
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            advice = m.AutoExecutor.format_launch_advice()
        assert "Agent tool" in advice

    def test_format_advice_connected(self):
        """Advice mentions 'delegate_task' in connected mode."""
        m = _import_module()
        with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "executor"}):
            advice = m.AutoExecutor.format_launch_advice()
        assert "delegate_task" in advice


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    def test_no_crash_without_dependencies(self):
        """check_and_activate never raises even when socket check fails."""
        import lib.auto_executor as m
        with patch.object(m, "_is_valkey_reachable", side_effect=Exception("network error")):
            # Should not propagate the exception — falls back gracefully
            try:
                result = m.AutoExecutor.check_and_activate()
                # If no raise, mode must be fire_and_forget
                assert result["mode"] == "fire_and_forget"
            except Exception:
                pytest.fail("check_and_activate raised an unexpected exception")
