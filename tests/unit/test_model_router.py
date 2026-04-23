"""Unit tests for lib/model_router.py

Validates model selection by task type, budget constraints,
local preference, cost estimation, and routing table formatting.
"""

import pytest
from unittest.mock import patch

from lib.model_router import (
    MODEL_CAPABILITIES,
    TASK_REQUIREMENTS,
    estimate_cost,
    format_routing_table,
    get_model_capabilities,
    route_and_execute,
    select_model,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# get_model_capabilities
# ---------------------------------------------------------------------------


class TestGetModelCapabilities:
    """Tests for get_model_capabilities()."""

    def test_known_model_returns_dict(self):
        caps = get_model_capabilities("claude-opus-4-6")
        assert isinstance(caps, dict)
        assert "reasoning" in caps
        assert "speed" in caps
        assert "code" in caps
        assert "cost_per_1m_in" in caps
        assert "cost_per_1m_out" in caps
        assert "context" in caps

    def test_unknown_model_raises(self):
        with pytest.raises(KeyError, match="Unknown model"):
            get_model_capabilities("nonexistent-model")

    def test_returns_copy_not_reference(self):
        """Should return a copy so modifying it doesn't affect the original."""
        caps = get_model_capabilities("claude-opus-4-6")
        caps["reasoning"] = 0
        assert MODEL_CAPABILITIES["claude-opus-4-6"]["reasoning"] == 9

    def test_all_models_have_required_fields(self):
        """Every model must have all required capability fields."""
        required = {"reasoning", "speed", "code", "cost_per_1m_in", "cost_per_1m_out", "context"}
        for model_name, caps in MODEL_CAPABILITIES.items():
            for field in required:
                assert field in caps, f"Model {model_name} missing field: {field}"

    def test_local_models_have_zero_cost(self):
        """Local models should have zero API cost."""
        for model_name, caps in MODEL_CAPABILITIES.items():
            if caps.get("local", False):
                assert caps["cost_per_1m_in"] == 0, f"{model_name} should have zero input cost"
                assert caps["cost_per_1m_out"] == 0, f"{model_name} should have zero output cost"


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


class TestEstimateCost:
    """Tests for estimate_cost()."""

    def test_zero_tokens_zero_cost(self):
        assert estimate_cost("claude-opus-4-6", 0, 0) == 0.0

    def test_known_cost_calculation(self):
        """Verify exact cost for a known model."""
        # claude-opus-4-6: $15/1M in, $75/1M out
        # 1M input + 1M output = $15 + $75 = $90
        cost = estimate_cost("claude-opus-4-6", 1_000_000, 1_000_000)
        assert cost == 90.0

    def test_haiku_is_cheapest_cloud(self):
        """Haiku should be significantly cheaper than opus."""
        opus_cost = estimate_cost("claude-opus-4-6", 10_000, 5_000)
        haiku_cost = estimate_cost("claude-haiku-3.5", 10_000, 5_000)
        assert haiku_cost < opus_cost
        assert haiku_cost < opus_cost * 0.1  # at least 10x cheaper

    def test_local_model_free(self):
        """Local models should have zero cost."""
        cost = estimate_cost("llama-3-70b", 100_000, 50_000)
        assert cost == 0.0

    def test_unknown_model_raises(self):
        with pytest.raises(KeyError):
            estimate_cost("nonexistent", 1000, 1000)

    def test_small_token_counts(self):
        """Should handle small token counts without rounding to zero incorrectly."""
        cost = estimate_cost("claude-opus-4-6", 100, 100)
        assert cost > 0

    def test_sonnet_cost(self):
        """Verify sonnet cost is between haiku and opus."""
        tokens_in, tokens_out = 50_000, 20_000
        haiku = estimate_cost("claude-haiku-3.5", tokens_in, tokens_out)
        sonnet = estimate_cost("claude-sonnet-4", tokens_in, tokens_out)
        opus = estimate_cost("claude-opus-4-6", tokens_in, tokens_out)
        assert haiku < sonnet < opus


# ---------------------------------------------------------------------------
# select_model — by task type
# ---------------------------------------------------------------------------


class TestSelectModelByTask:
    """Tests for select_model() task-based routing."""

    def test_reasoning_task_picks_high_reasoning(self):
        """Reasoning tasks should pick a model with high reasoning score."""
        model = select_model("sdd-propose")
        caps = get_model_capabilities(model)
        assert caps["reasoning"] >= 8

    def test_speed_task_picks_fast_model(self):
        """Speed tasks should pick a model with high speed score."""
        model = select_model("sdd-archive")
        caps = get_model_capabilities(model)
        assert caps["speed"] >= 7

    def test_code_task_picks_code_model(self):
        """Code tasks should pick a model with high code score."""
        model = select_model("sdd-apply", use_advisor=False)
        caps = get_model_capabilities(model)
        assert caps["code"] >= 7

    def test_long_context_picks_large_context(self):
        """Long context tasks should pick a model with large context window."""
        model = select_model("sdd-explore")
        caps = get_model_capabilities(model)
        assert caps["context"] >= 200_000

    def test_budget_task_picks_cheap_model(self):
        """Budget tasks should pick a cost-efficient model."""
        model = select_model("document-feature")
        caps = get_model_capabilities(model)
        total_cost = caps["cost_per_1m_in"] + caps["cost_per_1m_out"]
        # Should not pick the most expensive model
        opus_cost = 15.0 + 75.0
        assert total_cost < opus_cost

    def test_unknown_task_returns_valid_model(self):
        """Unknown task types should still return a valid model."""
        model = select_model("completely-unknown-task")
        assert model in MODEL_CAPABILITIES

    def test_all_known_tasks_return_valid_model(self):
        """All task types in TASK_REQUIREMENTS should route to a valid model."""
        for capability, tasks in TASK_REQUIREMENTS.items():
            for task in tasks:
                model = select_model(task, use_advisor=False)
                assert model in MODEL_CAPABILITIES, f"Task {task} routed to unknown model {model}"


# ---------------------------------------------------------------------------
# select_model — budget constraints
# ---------------------------------------------------------------------------


class TestSelectModelBudget:
    """Tests for select_model() with budget constraints."""

    def test_tight_budget_avoids_expensive_models(self):
        """With a very tight budget, should avoid opus."""
        model = select_model("sdd-propose", budget_remaining=0.01)
        caps = get_model_capabilities(model)
        # Should not pick opus ($15/$75)
        assert caps["cost_per_1m_in"] < 15.0

    def test_zero_budget_picks_local_or_cheapest(self):
        """With zero budget, should pick a free/local model if possible."""
        model = select_model("sdd-apply", budget_remaining=0.0, use_advisor=False)
        caps = get_model_capabilities(model)
        total_cost = caps["cost_per_1m_in"] + caps["cost_per_1m_out"]
        assert total_cost == 0.0

    def test_large_budget_allows_opus(self):
        """With large budget, opus should be selectable for reasoning tasks."""
        model = select_model("sdd-propose", budget_remaining=100.0)
        caps = get_model_capabilities(model)
        assert caps["reasoning"] >= 8

    def test_none_budget_no_constraint(self):
        """None budget should mean no budget constraint."""
        model = select_model("sdd-propose", budget_remaining=None)
        assert model in MODEL_CAPABILITIES


# ---------------------------------------------------------------------------
# select_model — local preference
# ---------------------------------------------------------------------------


class TestSelectModelLocal:
    """Tests for select_model() with local model preference."""

    def test_prefer_local_picks_local(self):
        """When prefer_local=True, should pick a local model."""
        model = select_model("sdd-apply", prefer_local=True)
        caps = get_model_capabilities(model)
        assert caps.get("local", False) is True

    def test_prefer_local_with_code_task(self):
        """Local preference with code task should pick best local coder."""
        model = select_model("sdd-apply", prefer_local=True)
        caps = get_model_capabilities(model)
        assert caps.get("local", False) is True
        assert caps["code"] >= 4

    def test_no_local_preference_by_default(self):
        """By default, cloud models should be considered."""
        model = select_model("sdd-propose")
        # Should pick a high-reasoning model, likely cloud
        caps = get_model_capabilities(model)
        assert caps["reasoning"] >= 8

    def test_local_preference_with_budget(self):
        """Local preference combined with budget should work."""
        model = select_model("sdd-apply", budget_remaining=0.0, prefer_local=True)
        caps = get_model_capabilities(model)
        assert caps.get("local", False) is True
        assert caps["cost_per_1m_in"] == 0.0


class TestRouteAndExecuteCapabilityProfile:
    @patch("lib.gateway_selector._check_litellm_health")
    def test_prefer_local_does_not_fall_back_to_claude_when_local_gateway_down(self, mock_litellm):
        """Local/private execution must fail closed instead of using Claude fallback."""
        from lib.gateway_selector import GatewayConfig

        mock_litellm.return_value = GatewayConfig(
            name="litellm",
            base_url="http://localhost:4000",
            is_available=False,
        )

        result = route_and_execute(
            "sdd-apply",
            messages=[{"role": "user", "content": "hello"}],
            prefer_local=True,
        )

        assert result.success is False
        assert result.provider == "none"
        assert "+local" in result.error


# ---------------------------------------------------------------------------
# format_routing_table
# ---------------------------------------------------------------------------


class TestFormatRoutingTable:
    """Tests for format_routing_table()."""

    def test_returns_string(self):
        result = format_routing_table()
        assert isinstance(result, str)

    def test_contains_all_task_types(self):
        """Routing table should list all known task types."""
        table = format_routing_table()
        for capability, tasks in TASK_REQUIREMENTS.items():
            for task in tasks:
                assert task in table, f"Task {task} not found in routing table"

    def test_contains_all_models(self):
        """Model capabilities section should list all models."""
        table = format_routing_table()
        for model_name in MODEL_CAPABILITIES:
            assert model_name in table, f"Model {model_name} not found in routing table"

    def test_contains_header(self):
        table = format_routing_table()
        assert "Dynamic Model Routing Table" in table

    def test_contains_capabilities_section(self):
        table = format_routing_table()
        assert "Model Capabilities:" in table

    def test_shows_local_flag(self):
        """Should indicate which models are local."""
        table = format_routing_table()
        assert "Local" in table or "local" in table
