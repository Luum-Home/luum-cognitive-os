"""Unit tests for the Anthropic Advisor Strategy integration.

Tests cover:
- ModelCatalog advisor constants and estimate_advisor_cost()
- model_router ADVISOR_TASKS, SONNET_ADVISOR_TIER, select_model(), estimate_cost()
- is_advisor_available() env-var detection
- ClaudeExecutor.run_with_advisor() — mocked Anthropic SDK
- ClaudeExecutor.run_auto() — routing logic and fallback paths
- ClaudeResult advisor fields
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Ensure lib/ is importable when running tests directly
_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from model_catalog import (
    ModelCatalog,
    ADVISOR_BETA,
    ADVISOR_TOOL_TYPE,
    ADVISOR_TOOL_DEF,
    ADVISOR_EXECUTOR_MODEL,
    ADVISOR_MODEL,
    ADVISOR_TOKENS_PER_USE,
)
from model_router import (
    ADVISOR_TASKS,
    SONNET_ADVISOR_TIER,
    estimate_cost,
    is_advisor_available,
    select_model,
)
from claude_executor import ClaudeExecutor, ClaudeResult, RetryCode, SONNET_ADVISOR_TIER as EXEC_TIER

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ModelCatalog advisor constants
# ---------------------------------------------------------------------------


class TestAdvisorConstants:
    def test_advisor_beta_string(self):
        assert ADVISOR_BETA == "advisor-tool-2026-03-01"

    def test_advisor_tool_type(self):
        assert ADVISOR_TOOL_TYPE == "advisor_20260301"

    def test_advisor_tool_def_keys(self):
        assert set(ADVISOR_TOOL_DEF.keys()) == {"type", "name", "model", "max_uses"}
        assert ADVISOR_TOOL_DEF["type"] == ADVISOR_TOOL_TYPE
        assert ADVISOR_TOOL_DEF["name"] == "advisor"
        assert ADVISOR_TOOL_DEF["model"] == "claude-opus-4-6"
        assert ADVISOR_TOOL_DEF["max_uses"] == 3

    def test_executor_model_is_sonnet(self):
        assert "sonnet" in ADVISOR_EXECUTOR_MODEL.lower()

    def test_advisor_model_is_opus(self):
        assert "opus" in ADVISOR_MODEL.lower()

    def test_advisor_tokens_per_use_is_tuple_of_two_ints(self):
        assert isinstance(ADVISOR_TOKENS_PER_USE, tuple)
        assert len(ADVISOR_TOKENS_PER_USE) == 2
        in_tok, out_tok = ADVISOR_TOKENS_PER_USE
        assert in_tok > 0
        assert out_tok > 0


# ---------------------------------------------------------------------------
# ModelCatalog.estimate_advisor_cost
# ---------------------------------------------------------------------------


class TestEstimateAdvisorCost:
    def test_zero_tokens_zero_cost(self):
        cost = ModelCatalog.estimate_advisor_cost(0, 0, 0)
        assert cost == 0.0

    def test_no_advisor_uses_equals_sonnet_cost(self):
        cost = ModelCatalog.estimate_advisor_cost(10_000, 5_000, 0)
        expected = ModelCatalog.estimate_cost(ADVISOR_EXECUTOR_MODEL, 10_000, 5_000)
        assert cost == expected

    def test_one_advisor_use_adds_opus_cost(self):
        in_tok, out_tok = ADVISOR_TOKENS_PER_USE
        cost = ModelCatalog.estimate_advisor_cost(10_000, 5_000, 1)
        exec_cost = ModelCatalog.estimate_cost(ADVISOR_EXECUTOR_MODEL, 10_000, 5_000)
        adv_cost = ModelCatalog.estimate_cost(ADVISOR_MODEL, in_tok, out_tok)
        assert abs(cost - (exec_cost + adv_cost)) < 1e-9

    def test_three_advisor_uses(self):
        in_tok, out_tok = ADVISOR_TOKENS_PER_USE
        cost = ModelCatalog.estimate_advisor_cost(20_000, 8_000, 3)
        exec_cost = ModelCatalog.estimate_cost(ADVISOR_EXECUTOR_MODEL, 20_000, 8_000)
        adv_cost = ModelCatalog.estimate_cost(ADVISOR_MODEL, in_tok * 3, out_tok * 3)
        assert abs(cost - (exec_cost + adv_cost)) < 1e-9

    def test_advisor_cost_is_cheaper_than_full_opus(self):
        """With 1 advisory call, total cost should be well below pure Opus."""
        mixed = ModelCatalog.estimate_advisor_cost(10_000, 5_000, 1)
        opus_only = ModelCatalog.estimate_cost(ADVISOR_MODEL, 10_000, 5_000)
        assert mixed < opus_only


# ---------------------------------------------------------------------------
# model_router: ADVISOR_TASKS and SONNET_ADVISOR_TIER
# ---------------------------------------------------------------------------


class TestAdvisorTasks:
    def test_advisor_tasks_contains_expected_tasks(self):
        for task in ("sdd-apply", "sdd-verify", "systematic-debugging"):
            assert task in ADVISOR_TASKS, f"{task!r} missing from ADVISOR_TASKS"

    def test_sonnet_advisor_tier_sentinel(self):
        assert SONNET_ADVISOR_TIER == "sonnet+advisor"

    def test_exec_tier_matches_router_tier(self):
        assert EXEC_TIER == SONNET_ADVISOR_TIER


# ---------------------------------------------------------------------------
# is_advisor_available
# ---------------------------------------------------------------------------


class TestIsAdvisorAvailable:
    def test_returns_false_by_default(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
        assert is_advisor_available() is False

    def test_returns_true_when_executor(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        assert is_advisor_available() is True

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "EXECUTOR")
        assert is_advisor_available() is True

    def test_returns_false_for_other_values(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "subprocess")
        assert is_advisor_available() is False


# ---------------------------------------------------------------------------
# select_model with advisor
# ---------------------------------------------------------------------------


class TestSelectModelAdvisor:
    def test_advisor_task_in_executor_mode_returns_sentinel(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        result = select_model("sdd-apply")
        assert result == SONNET_ADVISOR_TIER

    def test_advisor_task_not_in_executor_mode_returns_normal_model(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
        result = select_model("sdd-apply")
        assert result != SONNET_ADVISOR_TIER

    def test_non_advisor_task_in_executor_mode_returns_normal_model(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        result = select_model("sdd-propose")
        assert result != SONNET_ADVISOR_TIER

    def test_advisor_override_true_forces_sentinel(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_MODE", raising=False)
        result = select_model("sdd-verify", use_advisor=True)
        assert result == SONNET_ADVISOR_TIER

    def test_advisor_override_false_suppresses_sentinel(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        result = select_model("sdd-verify", use_advisor=False)
        assert result != SONNET_ADVISOR_TIER

    def test_prefer_local_suppresses_advisor(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        result = select_model("sdd-apply", prefer_local=True)
        # When prefer_local=True, advisor is skipped
        assert result != SONNET_ADVISOR_TIER

    def test_all_advisor_tasks_return_sentinel_in_executor_mode(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MODE", "executor")
        for task in ADVISOR_TASKS:
            result = select_model(task)
            assert result == SONNET_ADVISOR_TIER, (
                f"select_model({task!r}) returned {result!r}, expected {SONNET_ADVISOR_TIER!r}"
            )


# ---------------------------------------------------------------------------
# estimate_cost with sonnet+advisor
# ---------------------------------------------------------------------------


class TestEstimateCostAdvisor:
    def test_sonnet_advisor_tier_no_uses(self):
        cost = estimate_cost(SONNET_ADVISOR_TIER, 10_000, 5_000)
        expected = ModelCatalog.estimate_advisor_cost(10_000, 5_000, 0)
        assert cost == expected

    def test_sonnet_advisor_tier_with_uses(self):
        cost = estimate_cost(SONNET_ADVISOR_TIER, 10_000, 5_000, advisor_uses=2)
        expected = ModelCatalog.estimate_advisor_cost(10_000, 5_000, 2)
        assert cost == expected

    def test_normal_model_ignores_advisor_uses(self):
        cost_no_advice = estimate_cost("claude-sonnet-4", 10_000, 5_000, advisor_uses=3)
        cost_no_advice_plain = estimate_cost("claude-sonnet-4", 10_000, 5_000)
        assert cost_no_advice == cost_no_advice_plain

    def test_unknown_model_raises(self):
        with pytest.raises((KeyError, Exception)):
            estimate_cost("no-such-model", 1_000, 500)


# ---------------------------------------------------------------------------
# ClaudeResult advisor fields
# ---------------------------------------------------------------------------


class TestClaudeResultAdvisorFields:
    def test_default_advisor_fields_are_zero(self):
        r = ClaudeResult(success=True, result_text="ok")
        assert r.advisor_uses == 0
        assert r.advisor_tokens_in == 0
        assert r.advisor_tokens_out == 0

    def test_advisor_fields_can_be_set(self):
        r = ClaudeResult(
            success=True,
            result_text="ok",
            advisor_uses=2,
            advisor_tokens_in=1_000,
            advisor_tokens_out=2_000,
        )
        assert r.advisor_uses == 2
        assert r.advisor_tokens_in == 1_000
        assert r.advisor_tokens_out == 2_000


# ---------------------------------------------------------------------------
# ClaudeExecutor.run_with_advisor — mocked Anthropic SDK
# ---------------------------------------------------------------------------

def _make_mock_response(text="advisor result", tokens_in=100, tokens_out=200, iterations=None):
    """Build a minimal mock Anthropic messages response."""
    content_block = SimpleNamespace(text=text)
    usage = SimpleNamespace(
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        iterations=iterations or [],
    )
    response = SimpleNamespace(content=[content_block], usage=usage)
    return response


class TestRunWithAdvisor:
    def test_returns_success_result_when_api_available(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        mock_response = _make_mock_response(text="advisor answer", tokens_in=500, tokens_out=300)

        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = mock_response

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            executor = ClaudeExecutor()
            result = executor.run_with_advisor("test prompt")

        assert result.success is True
        assert result.result_text == "advisor answer"
        assert result.tokens_in == 500
        assert result.tokens_out == 300
        assert result.model_used == ADVISOR_EXECUTOR_MODEL
        assert result.retry_code == RetryCode.NONE

    def test_includes_advisor_tool_in_api_call(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        mock_response = _make_mock_response()
        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = mock_response

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            executor = ClaudeExecutor()
            executor.run_with_advisor("test prompt", max_advisor_uses=2)

        call_kwargs = mock_client.beta.messages.create.call_args.kwargs
        assert call_kwargs.get("betas") == [ADVISOR_BETA]
        tools = call_kwargs.get("tools", [])
        assert len(tools) == 1
        assert tools[0]["type"] == ADVISOR_TOOL_TYPE
        assert tools[0]["max_uses"] == 2

    def test_extracts_advisor_uses_from_iterations(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        # Simulate 2 advisor iterations
        advisor_iter_1 = SimpleNamespace(
            model="claude-opus-4-6", input_tokens=500, output_tokens=1000
        )
        advisor_iter_2 = SimpleNamespace(
            model="claude-opus-4-6", input_tokens=400, output_tokens=900
        )
        mock_response = _make_mock_response(
            tokens_in=2000,
            tokens_out=500,
            iterations=[advisor_iter_1, advisor_iter_2],
        )

        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = mock_response

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            executor = ClaudeExecutor()
            result = executor.run_with_advisor("test prompt")

        assert result.advisor_uses == 2
        assert result.advisor_tokens_in == 900   # 500 + 400
        assert result.advisor_tokens_out == 1900  # 1000 + 900

    def test_falls_back_to_run_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        executor = ClaudeExecutor()
        with patch.object(executor, "run", return_value=ClaudeResult(success=True, result_text="fallback")) as mock_run:
            result = executor.run_with_advisor("test prompt")

        mock_run.assert_called_once_with(prompt="test prompt", model="sonnet")
        assert result.result_text == "fallback"

    def test_falls_back_to_run_when_package_not_installed(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        # Remove anthropic from sys.modules and block import
        with patch.dict("sys.modules", {"anthropic": None}):
            executor = ClaudeExecutor()
            with patch.object(executor, "run", return_value=ClaudeResult(success=True, result_text="cli-fallback")) as mock_run:
                result = executor.run_with_advisor("test prompt")

        mock_run.assert_called_once_with(prompt="test prompt", model="sonnet")
        assert result.result_text == "cli-fallback"

    def test_returns_error_result_on_api_exception(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_client.beta.messages.create.side_effect = RuntimeError("API error")

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            executor = ClaudeExecutor()
            result = executor.run_with_advisor("test prompt")

        assert result.success is False
        assert "API error" in result.error_message
        assert result.retry_code == RetryCode.EXECUTION_ERROR

    def test_passes_system_prompt_to_api(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        mock_response = _make_mock_response()
        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = mock_response

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            executor = ClaudeExecutor()
            executor.run_with_advisor("test prompt", system_prompt="You are an expert.")

        call_kwargs = mock_client.beta.messages.create.call_args.kwargs
        assert call_kwargs.get("system") == "You are an expert."


# ---------------------------------------------------------------------------
# ClaudeExecutor.run_auto — routing and fallback
# ---------------------------------------------------------------------------


class TestRunAuto:
    def test_routes_to_advisor_when_model_is_sentinel_and_preconditions_met(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        mock_anthropic_module = MagicMock()
        executor = ClaudeExecutor()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            with patch.object(
                executor,
                "run_with_advisor",
                return_value=ClaudeResult(success=True, result_text="advisor"),
            ) as mock_advisor:
                result = executor.run_auto("prompt", model=SONNET_ADVISOR_TIER)

        mock_advisor.assert_called_once()
        assert result.result_text == "advisor"

    def test_falls_back_to_sonnet_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        executor = ClaudeExecutor()
        with patch.object(
            executor, "run", return_value=ClaudeResult(success=True, result_text="sonnet-cli")
        ) as mock_run:
            result = executor.run_auto("prompt", model=SONNET_ADVISOR_TIER)

        mock_run.assert_called_once_with(
            prompt="prompt", model="sonnet", timeout=None, allowed_tools=None
        )
        assert result.result_text == "sonnet-cli"

    def test_falls_back_to_sonnet_when_package_not_installed(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        executor = ClaudeExecutor()
        with patch.dict("sys.modules", {"anthropic": None}):
            with patch.object(
                executor, "run", return_value=ClaudeResult(success=True, result_text="sonnet-cli")
            ) as mock_run:
                result = executor.run_auto("prompt", model=SONNET_ADVISOR_TIER)

        mock_run.assert_called_once_with(
            prompt="prompt", model="sonnet", timeout=None, allowed_tools=None
        )

    def test_non_advisor_model_goes_to_run(self, monkeypatch):
        executor = ClaudeExecutor()
        with patch.object(
            executor, "run", return_value=ClaudeResult(success=True, result_text="haiku")
        ) as mock_run:
            executor.run_auto("prompt", model="haiku")

        mock_run.assert_called_once_with(
            prompt="prompt", model="haiku", timeout=None, allowed_tools=None
        )

    def test_none_model_uses_default(self, monkeypatch):
        executor = ClaudeExecutor(default_model="sonnet")
        with patch.object(
            executor, "run", return_value=ClaudeResult(success=True, result_text="ok")
        ) as mock_run:
            executor.run_auto("prompt")

        # model="" will be passed to run (empty string, not sentinel)
        mock_run.assert_called_once()

    def test_cost_tracking_uses_mixed_billing(self, monkeypatch):
        """Verify that a successful advisor run reports advisor-aware cost."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        advisor_iter = SimpleNamespace(
            model="claude-opus-4-6", input_tokens=500, output_tokens=1000
        )
        mock_response = _make_mock_response(
            tokens_in=10_000,
            tokens_out=5_000,
            iterations=[advisor_iter],
        )

        mock_client = MagicMock()
        mock_client.beta.messages.create.return_value = mock_response

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            executor = ClaudeExecutor()
            result = executor.run_auto("prompt", model=SONNET_ADVISOR_TIER)

        # Cost must include at least Sonnet executor cost
        sonnet_cost = ModelCatalog.estimate_cost(ADVISOR_EXECUTOR_MODEL, 10_000, 5_000)
        assert result.cost_usd >= sonnet_cost
        # And should have advisor_uses > 0
        assert result.advisor_uses == 1
