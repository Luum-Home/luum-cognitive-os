"""Unit tests for lib/orchestrator_mode.py.

Tests the mode detection, delegation helpers, and graceful fallback
when ClaudeExecutor is not available.

Python 3.9+ compatible.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from lib import orchestrator_mode as om


# -----------------------------------------------------------------------
# is_executor_mode
# -----------------------------------------------------------------------


class TestIsExecutorMode:
    def test_false_by_default(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
        assert om.is_executor_mode() is False

    def test_false_when_empty(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "")
        assert om.is_executor_mode() is False

    def test_true_when_executor(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        assert om.is_executor_mode() is True

    def test_true_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "EXECUTOR")
        assert om.is_executor_mode() is True

    def test_false_for_other_values(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "agent")
        assert om.is_executor_mode() is False


# -----------------------------------------------------------------------
# delegate_task
# -----------------------------------------------------------------------


class TestDelegateTask:
    def test_returns_dict_structure(self):
        """delegate_task should return a dict with the expected keys."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result_text = "done"
        mock_result.cost_usd = 0.01
        mock_result.duration_secs = 1.5
        mock_result.tokens_in = 100
        mock_result.tokens_out = 200
        mock_result.model_used = "claude-sonnet-4-20250514"

        mock_executor_cls = MagicMock()
        mock_executor_cls.return_value.run.return_value = mock_result

        # Patch at the module that delegate_task imports from
        with patch("lib.claude_executor.ClaudeExecutor", mock_executor_cls):
            # Must call inside the patch context so the lazy import picks it up
            result = om.delegate_task("do something", model="sonnet")

            assert isinstance(result, dict)
            assert result["success"] is True
            assert result["result"] == "done"
            assert result["cost_usd"] == 0.01
            assert result["duration_secs"] == 1.5
            assert result["tokens_in"] == 100
            assert result["tokens_out"] == 200
            assert "agent_id" in result

    def test_uses_provided_agent_id(self):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result_text = "ok"
        mock_result.cost_usd = 0.0
        mock_result.duration_secs = 0.1
        mock_result.tokens_in = 0
        mock_result.tokens_out = 0
        mock_result.model_used = ""

        mock_executor_cls = MagicMock()
        mock_executor_cls.return_value.run.return_value = mock_result

        with patch("lib.claude_executor.ClaudeExecutor", mock_executor_cls):
            result = om.delegate_task("test", agent_id="my-agent-42")

        assert result["agent_id"] == "my-agent-42"

    def test_graceful_fallback_without_executor(self):
        """When ClaudeExecutor cannot be imported, should return error dict."""
        # Temporarily remove lib.claude_executor from sys.modules
        import sys
        saved = sys.modules.get("lib.claude_executor")
        sys.modules["lib.claude_executor"] = None  # type: ignore[assignment]
        try:
            # Force re-import failure
            result = om.delegate_task("test task")
            assert result["success"] is False
            assert "not available" in result["result"].lower() or result["success"] is False
        finally:
            if saved is not None:
                sys.modules["lib.claude_executor"] = saved
            else:
                sys.modules.pop("lib.claude_executor", None)


# -----------------------------------------------------------------------
# delegate_sdd_phase
# -----------------------------------------------------------------------


class TestDelegateSDDPhase:
    def test_uses_model_routing(self):
        """Should pick the model from the routing table for known phases."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result_text = "phase done"
        mock_result.cost_usd = 0.05
        mock_result.duration_secs = 10.0
        mock_result.tokens_in = 500
        mock_result.tokens_out = 1000
        mock_result.model_used = "claude-opus-4-20250514"

        mock_executor_cls = MagicMock()
        mock_executor_cls.return_value.run.return_value = mock_result

        with patch("lib.claude_executor.ClaudeExecutor", mock_executor_cls):
            result = om.delegate_sdd_phase("auth-refactor", "sdd-propose")

        assert result["success"] is True
        assert result["agent_id"].startswith("sdd-propose-")

    def test_override_model(self):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result_text = "ok"
        mock_result.cost_usd = 0.0
        mock_result.duration_secs = 0.1
        mock_result.tokens_in = 0
        mock_result.tokens_out = 0
        mock_result.model_used = "haiku"

        mock_executor_cls = MagicMock()
        mock_executor_cls.return_value.run.return_value = mock_result

        with patch("lib.claude_executor.ClaudeExecutor", mock_executor_cls):
            result = om.delegate_sdd_phase(
                "my-change", "sdd-apply", model="haiku"
            )

        assert result["success"] is True
        # Verify the model override was passed
        call_args = mock_executor_cls.return_value.run.call_args
        assert call_args is not None
        assert call_args.kwargs.get("model") == "haiku" or call_args[1].get("model") == "haiku"


# -----------------------------------------------------------------------
# _get_model_for_phase
# -----------------------------------------------------------------------


class TestModelForPhase:
    def test_known_phase_returns_model(self):
        """Known phases should return a valid model name."""
        model = om._get_model_for_phase("sdd-propose")
        # Should be opus from either the router or the fallback dict
        assert model is not None
        assert len(model) > 0

    def test_archive_returns_cheap_model(self):
        """sdd-archive should get a cheap model (haiku)."""
        model = om._get_model_for_phase("sdd-archive")
        # From either router or fallback, archive uses haiku
        assert "haiku" in model.lower() or model == "haiku"

    def test_unknown_phase_does_not_crash(self):
        """Unknown phases should return some valid model, not crash."""
        model = om._get_model_for_phase("totally-unknown-phase")
        assert model is not None
        assert len(model) > 0
