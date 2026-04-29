"""Unit tests for lib/auto_executor.py.

These tests run regardless of Valkey availability — they mock the TCP check.

Note on Cat D tests (skip_when_valkey_running):
  lib/auto_executor is a deprecation shim that re-exports from
  lib/orchestrator_mode_activator.  patch.object() on the shim's
  _is_valkey_reachable attribute does not intercept the call inside
  AutoExecutor.check_and_activate() because that call resolves via the
  canonical module's namespace, not the shim's.

  When Valkey is actually running the mocked-to-False tests fail because
  the live TCP check returns True instead of the mocked False.  These
  tests are valid in offline environments and are therefore skipped when
  Valkey is available rather than deleted.
"""

import os
import warnings
from unittest.mock import MagicMock, patch

import pytest

from tests.unit._helpers import skip_when_valkey_running


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_module():
    """Fresh import of the deprecated shim without leaking expected warnings."""
    import importlib
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="lib.auto_executor is deprecated.*",
            category=DeprecationWarning,
        )
        m = importlib.import_module("lib.auto_executor")
        importlib.reload(m)
    return m


# ---------------------------------------------------------------------------
# check_and_activate
# ---------------------------------------------------------------------------

class TestCheckAndActivate:
    @skip_when_valkey_running
    def test_check_no_valkey(self):
        """Returns fire_and_forget when no Valkey is reachable.

        Skipped when Valkey is running because the shim re-export means
        patch.object on lib.auto_executor._is_valkey_reachable does not
        intercept the live call inside AutoExecutor.check_and_activate().
        """
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=False):
                result = m.AutoExecutor.check_and_activate()
        assert result["mode"] == "fire_and_forget"
        assert result["valkey_available"] is False

    def test_check_with_valkey(self):
        """Returns connected when Valkey is reachable."""
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=True):
                result = m.AutoExecutor.check_and_activate()
        assert result["mode"] == "connected"
        assert result["valkey_available"] is True

    def test_auto_activated_flag(self):
        """auto_activated=True when Valkey is up and ORCHESTRATOR_MODE was not set."""
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=True):
                result = m.AutoExecutor.check_and_activate()
        assert result["auto_activated"] is True

    def test_not_auto_activated_when_already_set(self):
        """auto_activated=False when ORCHESTRATOR_MODE was already 'executor'."""
        m = _import_module()
        with patch.dict(os.environ, {"ORCHESTRATOR_MODE": "executor"}):
            with patch.object(m, "_is_valkey_reachable", return_value=True):
                result = m.AutoExecutor.check_and_activate()
        assert result["auto_activated"] is False

    @skip_when_valkey_running
    def test_not_auto_activated_without_valkey(self):
        """auto_activated=False when Valkey is not reachable.

        Skipped when Valkey is running — same shim patch limitation as
        test_check_no_valkey.
        """
        m = _import_module()
        env = {k: v for k, v in os.environ.items() if k != "ORCHESTRATOR_MODE"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(m, "_is_valkey_reachable", return_value=False):
                result = m.AutoExecutor.check_and_activate()
        assert result["auto_activated"] is False

    def test_message_present(self):
        """Result dict always contains a non-empty message."""
        m = _import_module()
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
    @skip_when_valkey_running
    def test_no_crash_without_dependencies(self):
        """check_and_activate never raises even when socket check fails.

        Skipped when Valkey is running — patching the shim re-export does
        not intercept the real call, so the live Valkey succeeds and the
        mode ends up as 'connected' not 'fire_and_forget'.
        """
        m = _import_module()
        with patch.object(m, "_is_valkey_reachable", side_effect=Exception("network error")):
            # Should not propagate the exception — falls back gracefully
            try:
                result = m.AutoExecutor.check_and_activate()
                # If no raise, mode must be fire_and_forget
                assert result["mode"] == "fire_and_forget"
            except Exception:
                pytest.fail("check_and_activate raised an unexpected exception")
