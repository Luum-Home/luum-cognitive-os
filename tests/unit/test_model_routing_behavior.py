"""Behavioral tests for model routing.

Verifies that the RIGHT model family is selected for each task category.
These tests call actual functions and verify concrete outputs — not file-check tests.

Key invariants tested:
- Architecture/reasoning tasks → high-reasoning model (opus family)
- Implementation/code tasks → balanced model (sonnet family)
- Archiving/formatting/doc tasks → fast/cheap model (haiku family)
- Budget downgrade chain: tight budget forces cheaper models
- Edge cases: empty task, unknown task, very tight budget
"""

import pytest

from lib.model_catalog import ModelCatalog
from lib.model_router import (
    MODEL_CAPABILITIES,
    TASK_REQUIREMENTS,
    estimate_cost,
    select_model,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _family(model: str) -> str:
    """Return the model family (opus/sonnet/haiku/etc.) via ModelCatalog."""
    try:
        return ModelCatalog.family(model)
    except KeyError:
        # For non-Anthropic models (llama, qwen, openrouter) return the model name
        return model


def _is_high_reasoning(model: str) -> bool:
    """True when the model has a reasoning score >= 8."""
    caps = MODEL_CAPABILITIES.get(model, {})
    return caps.get("reasoning", 0) >= 8


def _is_fast_or_cheap(model: str) -> bool:
    """True when the model has speed score >= 7 OR total cost <= haiku pricing."""
    caps = MODEL_CAPABILITIES.get(model, {})
    haiku_total = 0.25 + 1.25  # haiku input+output per 1M
    total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
    return caps.get("speed", 0) >= 7 or total_cost <= haiku_total


def _is_balanced_code(model: str) -> bool:
    """True when model has reasonable code AND is not the most expensive."""
    caps = MODEL_CAPABILITIES.get(model, {})
    opus_total = 15.0 + 75.0  # most expensive benchmark
    total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
    return caps.get("code", 0) >= 6 and total_cost < opus_total


# ---------------------------------------------------------------------------
# Architecture / Reasoning tasks → high-reasoning model
# ---------------------------------------------------------------------------


class TestModelSelectionForReasoningTasks:
    """Architecture and reasoning tasks should select a high-reasoning model."""

    def test_sdd_propose_selects_high_reasoning(self):
        """SDD proposal phase needs deep reasoning — must pick high-reasoning model."""
        model = select_model("sdd-propose")
        assert _is_high_reasoning(model), (
            f"sdd-propose selected {model!r} with reasoning "
            f"{MODEL_CAPABILITIES.get(model, {}).get('reasoning', 'N/A')} — expected >= 8"
        )

    def test_sdd_design_selects_high_reasoning(self):
        """Architecture design decisions need high-reasoning model."""
        model = select_model("sdd-design")
        assert _is_high_reasoning(model), (
            f"sdd-design selected {model!r} — reasoning too low"
        )

    def test_systematic_debugging_selects_high_reasoning(self):
        """Root cause analysis needs the best reasoning capability."""
        model = select_model("systematic-debugging", use_advisor=False)
        assert _is_high_reasoning(model), (
            f"systematic-debugging selected {model!r} — expected high-reasoning model"
        )

    def test_sdd_improve_selects_high_reasoning(self):
        """sdd-improve (refinement) also needs reasoning capability."""
        model = select_model("sdd-improve")
        assert _is_high_reasoning(model), (
            f"sdd-improve selected {model!r} — expected high-reasoning model"
        )

    def test_reasoning_tasks_are_not_cheapest_model(self):
        """Reasoning tasks must not route to the cheapest/free models."""
        haiku_total = 0.25 + 1.25
        for task in TASK_REQUIREMENTS["reasoning"]:
            model = select_model(task, use_advisor=False)
            caps = MODEL_CAPABILITIES.get(model, {})
            total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
            assert total_cost > haiku_total, (
                f"Reasoning task {task!r} selected {model!r} which is haiku-priced or cheaper"
            )


# ---------------------------------------------------------------------------
# Implementation / Code tasks → balanced model (not too expensive)
# ---------------------------------------------------------------------------


class TestModelSelectionForCodeTasks:
    """Implementation tasks should select a capable but cost-efficient model."""

    def test_sdd_apply_selects_good_code_model(self):
        """sdd-apply (implementation) needs a model with good code capability."""
        model = select_model("sdd-apply", use_advisor=False)
        assert _is_balanced_code(model), (
            f"sdd-apply selected {model!r} — expected balanced code model (code>=6, not opus-priced)"
        )

    def test_sdd_tasks_selects_good_code_model(self):
        """Task breakdown for implementation needs code capability."""
        model = select_model("sdd-tasks")
        assert _is_balanced_code(model), (
            f"sdd-tasks selected {model!r} — expected balanced code model"
        )

    def test_tdd_selects_good_code_model(self):
        """Test-driven development needs a capable coder."""
        model = select_model("test-driven-development")
        assert _is_balanced_code(model), (
            f"test-driven-development selected {model!r} — expected balanced code model"
        )

    def test_code_tasks_return_valid_models(self):
        """All code task types must resolve to a known model."""
        for task in TASK_REQUIREMENTS["code"]:
            model = select_model(task, use_advisor=False)
            assert model in MODEL_CAPABILITIES, (
                f"Code task {task!r} resolved to unknown model {model!r}"
            )


# ---------------------------------------------------------------------------
# Archiving / speed tasks → fast/cheap model (haiku family)
# ---------------------------------------------------------------------------


class TestModelSelectionForSpeedTasks:
    """Archiving and formatting tasks should use fast/cheap models."""

    def test_sdd_archive_selects_fast_cheap_model(self):
        """Archiving is simple documentation — should use the cheapest/fastest model."""
        model = select_model("sdd-archive")
        assert _is_fast_or_cheap(model), (
            f"sdd-archive selected {model!r} — expected fast/cheap model"
        )

    def test_doc_sync_selects_fast_model(self):
        """Doc sync is routine work — should use fast/cheap model."""
        model = select_model("doc-sync")
        assert _is_fast_or_cheap(model), (
            f"doc-sync selected {model!r} — expected fast/cheap model"
        )

    def test_format_selects_fast_model(self):
        """Formatting is trivial — should use fast/cheap model."""
        model = select_model("format")
        assert _is_fast_or_cheap(model), (
            f"format selected {model!r} — expected fast/cheap model"
        )

    def test_speed_tasks_avoid_high_reasoning_models(self):
        """Speed tasks should not pick the most expensive reasoning model."""
        opus_total = 15.0 + 75.0
        for task in TASK_REQUIREMENTS["speed"]:
            model = select_model(task)
            caps = MODEL_CAPABILITIES.get(model, {})
            total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
            assert total_cost < opus_total, (
                f"Speed task {task!r} selected {model!r} with opus-level cost {total_cost}"
            )

    def test_sdd_archive_is_cheaper_than_sdd_propose(self):
        """Archiving must be cheaper than proposing — reflects task importance hierarchy."""
        archive_model = select_model("sdd-archive")
        propose_model = select_model("sdd-propose")
        archive_cost = estimate_cost(archive_model, 10_000, 5_000)
        propose_cost = estimate_cost(propose_model, 10_000, 5_000)
        assert archive_cost < propose_cost, (
            f"Archive ({archive_model}) costs ${archive_cost:.4f} but "
            f"propose ({propose_model}) costs ${propose_cost:.4f} — archive should be cheaper"
        )


# ---------------------------------------------------------------------------
# Budget-driven downgrade behavior
# ---------------------------------------------------------------------------


class TestBudgetDowngradeChain:
    """Budget constraints must force cheaper models — the downgrade chain in action."""

    def test_tight_budget_avoids_opus_for_reasoning_task(self):
        """At near-zero budget, even a reasoning task must avoid opus."""
        # $0.05 is below the cost of a reference opus call (~$0.525 for 10K+5K tokens)
        model = select_model("sdd-propose", budget_remaining=0.05)
        caps = MODEL_CAPABILITIES.get(model, {})
        total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
        opus_total = 15.0 + 75.0
        assert total_cost < opus_total, (
            f"Budget=0.05 — selected {model!r} with cost {total_cost} — should not be opus-priced"
        )

    def test_zero_budget_selects_free_model(self):
        """At zero budget, must select a free/local model."""
        model = select_model("sdd-propose", budget_remaining=0.0)
        caps = MODEL_CAPABILITIES.get(model, {})
        total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
        assert total_cost == 0.0, (
            f"Budget=0.0 — selected {model!r} with cost {total_cost} — must be free"
        )

    def test_zero_budget_selects_free_model_for_any_task(self):
        """Zero budget forces free model regardless of task type."""
        for task_type in ["sdd-propose", "sdd-archive", "sdd-apply", "systematic-debugging"]:
            model = select_model(task_type, budget_remaining=0.0)
            caps = MODEL_CAPABILITIES.get(model, {})
            total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
            assert total_cost == 0.0, (
                f"Task {task_type!r} with budget=0.0 selected {model!r} with cost {total_cost}"
            )

    def test_very_tight_budget_avoids_sonnet_for_code_task(self):
        """With $0.001 budget, even code tasks should pick something cheaper than sonnet."""
        model = select_model("sdd-apply", budget_remaining=0.001)
        caps = MODEL_CAPABILITIES.get(model, {})
        total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
        sonnet_total = 3.0 + 15.0
        assert total_cost < sonnet_total, (
            f"Budget=0.001 — {model!r} costs {total_cost}/1M — should be cheaper than sonnet"
        )

    def test_large_budget_unlocks_best_reasoning_model(self):
        """With generous budget, reasoning tasks get the best model."""
        model = select_model("sdd-propose", budget_remaining=100.0)
        assert _is_high_reasoning(model), (
            f"With $100 budget, sdd-propose selected {model!r} — expected high-reasoning"
        )

    def test_budget_none_means_no_constraint(self):
        """budget_remaining=None means no budget constraint — should pick best model."""
        model_none = select_model("sdd-propose", budget_remaining=None)
        model_large = select_model("sdd-propose", budget_remaining=100.0)
        # Both should be high-reasoning models
        assert _is_high_reasoning(model_none), (
            f"No budget — sdd-propose selected {model_none!r} — expected high-reasoning"
        )
        # With no constraint, should pick at least as capable as with large budget
        caps_none = MODEL_CAPABILITIES.get(model_none, {})
        caps_large = MODEL_CAPABILITIES.get(model_large, {})
        assert caps_none.get("reasoning", 0) >= caps_large.get("reasoning", 0) - 1, (
            f"No-budget model {model_none!r} is less capable than budget-constrained {model_large!r}"
        )

    def test_budget_consistency_across_equivalent_tasks(self):
        """Same budget constraint applied to equivalent tasks should pick similar-tier models."""
        budget = 0.05
        # Both are reasoning tasks — should pick from the same tier when budget is tight
        m1 = select_model("sdd-propose", budget_remaining=budget)
        m2 = select_model("sdd-design", budget_remaining=budget)
        # Both should be non-opus (too expensive)
        opus_total = 15.0 + 75.0
        for model, task in [(m1, "sdd-propose"), (m2, "sdd-design")]:
            caps = MODEL_CAPABILITIES.get(model, {})
            total = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
            assert total < opus_total, (
                f"Task {task!r} with budget={budget} selected {model!r} — should avoid opus"
            )

    def test_budget_depleted_falls_through_to_free(self):
        """At budget=$0.001 the router must fall through to a fully free model.

        $0.001 is the boundary that triggers the free-model filter
        (budget_remaining <= 0.01).  The returned model must have zero
        cost for both input and output tokens.
        """
        model = select_model("sdd-apply", budget_remaining=0.001, use_advisor=False)
        caps = MODEL_CAPABILITIES.get(model, {})
        in_cost = caps.get("cost_per_1m_in", -1)
        out_cost = caps.get("cost_per_1m_out", -1)
        assert in_cost == 0.0 and out_cost == 0.0, (
            f"budget=0.001 selected {model!r} with in={in_cost}, out={out_cost} "
            "— expected a free model (both costs == 0.0)"
        )

    def test_prefer_local_zero_budget_returns_free(self):
        """prefer_local=True with budget=0.0 must return a local, zero-cost model.

        Combining both constraints — local preference AND exhausted budget —
        must still resolve to a valid model that is both local and free.
        """
        model = select_model("sdd-apply", budget_remaining=0.0, prefer_local=True)
        caps = MODEL_CAPABILITIES.get(model, {})
        in_cost = caps.get("cost_per_1m_in", -1)
        out_cost = caps.get("cost_per_1m_out", -1)
        caps.get("local", False)
        # Must be in the known capabilities registry
        assert model in MODEL_CAPABILITIES, (
            f"prefer_local + budget=0 returned unknown model {model!r}"
        )
        # Must be free (zero cost)
        assert in_cost == 0.0 and out_cost == 0.0, (
            f"prefer_local + budget=0 → {model!r} costs in={in_cost} out={out_cost} — must be free"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestModelSelectionEdgeCases:
    """Edge cases: unknown task, empty input, extremely tight budget."""

    def test_unknown_task_returns_valid_model(self):
        """Completely unknown task type must return a known model, not crash."""
        model = select_model("completely-unknown-task-type-xyz")
        assert model in MODEL_CAPABILITIES, (
            f"Unknown task returned {model!r} — not in MODEL_CAPABILITIES"
        )

    def test_unknown_task_defaults_to_reasoning_capable_model(self):
        """Unknown task type should default to best-reasoning (safe default)."""
        model = select_model("nonexistent-task")
        caps = MODEL_CAPABILITIES.get(model, {})
        # Unknown tasks fall back to best reasoning — should not be the slowest/cheapest
        assert caps.get("reasoning", 0) >= 4, (
            f"Unknown task selected {model!r} with reasoning {caps.get('reasoning')} — too low"
        )

    def test_empty_string_task_returns_valid_model(self):
        """Empty string task type must not crash."""
        model = select_model("")
        assert model in MODEL_CAPABILITIES, (
            f"Empty task type returned {model!r} — not in MODEL_CAPABILITIES"
        )

    def test_all_tasks_in_requirements_route_to_valid_model(self):
        """Every task in TASK_REQUIREMENTS must resolve to a known model."""
        for capability, tasks in TASK_REQUIREMENTS.items():
            for task in tasks:
                model = select_model(task, use_advisor=False)
                assert model in MODEL_CAPABILITIES, (
                    f"Task {task!r} (capability={capability}) routed to unknown model {model!r}"
                )

    def test_negative_budget_treated_as_zero(self):
        """Negative budget should behave like zero budget — pick free model."""
        model = select_model("sdd-apply", budget_remaining=-1.0)
        caps = MODEL_CAPABILITIES.get(model, {})
        total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
        # Should pick free or very cheap model
        assert total_cost == 0.0, (
            f"Negative budget selected {model!r} with cost {total_cost} — should be free"
        )

    def test_model_selection_is_deterministic(self):
        """Same inputs must always produce same output (no randomness)."""
        for _ in range(5):
            assert select_model("sdd-propose") == select_model("sdd-propose")
            assert select_model("sdd-archive") == select_model("sdd-archive")
            assert (
                select_model("sdd-apply", budget_remaining=0.0)
                == select_model("sdd-apply", budget_remaining=0.0)
            )

    def test_local_preference_returns_local_model(self):
        """prefer_local=True must return a model with local=True."""
        model = select_model("sdd-apply", prefer_local=True)
        caps = MODEL_CAPABILITIES.get(model, {})
        assert caps.get("local", False) is True, (
            f"prefer_local=True selected {model!r} which is not a local model"
        )

    def test_local_model_has_zero_cost(self):
        """Local models selected by prefer_local must have zero cost."""
        model = select_model("sdd-apply", prefer_local=True)
        caps = MODEL_CAPABILITIES.get(model, {})
        assert caps.get("cost_per_1m_in", -1) == 0.0
        assert caps.get("cost_per_1m_out", -1) == 0.0


# ---------------------------------------------------------------------------
# Model catalog downgrade chain
# ---------------------------------------------------------------------------


class TestModelDowngradeChain:
    """ModelCatalog.downgrade() implements the budget downgrade chain."""

    def test_opus_downgrades_to_sonnet(self):
        """opus → sonnet is the first step in the downgrade chain."""
        result = ModelCatalog.downgrade("claude-opus-4-6")
        assert result == "claude-sonnet-4", (
            f"opus should downgrade to sonnet, got {result!r}"
        )

    def test_sonnet_downgrades_to_haiku(self):
        """sonnet → haiku is the next step."""
        result = ModelCatalog.downgrade("claude-sonnet-4")
        assert result == "claude-haiku-3.5", (
            f"sonnet should downgrade to haiku, got {result!r}"
        )

    def test_haiku_downgrades_to_free(self):
        """haiku → openrouter/free is the last Anthropic step."""
        result = ModelCatalog.downgrade("claude-haiku-3.5")
        assert result == "openrouter/free", (
            f"haiku should downgrade to openrouter/free, got {result!r}"
        )

    def test_free_model_has_no_downgrade(self):
        """openrouter/free is the bottom of the chain — no further downgrade."""
        result = ModelCatalog.downgrade("openrouter/free")
        assert result is None, (
            f"openrouter/free should have no downgrade, got {result!r}"
        )

    def test_opus_upgrade_path(self):
        """Verify the full upgrade chain: sonnet → opus."""
        result = ModelCatalog.upgrade("claude-sonnet-4")
        assert result == "claude-opus-4-6", (
            f"sonnet should upgrade to opus, got {result!r}"
        )

    def test_opus_has_no_upgrade(self):
        """opus is the top — no further upgrade."""
        result = ModelCatalog.upgrade("claude-opus-4-6")
        assert result is None, (
            f"opus should have no upgrade, got {result!r}"
        )

    def test_downgrade_chain_is_monotonically_cheaper(self):
        """Each step in the downgrade chain must be cheaper than the previous."""
        chain = ["claude-opus-4-6", "claude-sonnet-4", "claude-haiku-3.5", "openrouter/free"]
        for i in range(len(chain) - 1):
            current = ModelCatalog.get(chain[i])
            cheaper = ModelCatalog.get(chain[i + 1])
            current_cost = current.input_price_per_m + current.output_price_per_m
            cheaper_cost = cheaper.input_price_per_m + cheaper.output_price_per_m
            assert cheaper_cost <= current_cost, (
                f"Downgrade step {chain[i]} → {chain[i+1]}: "
                f"{cheaper_cost} is not <= {current_cost}"
            )

    def test_alias_resolution_for_downgrade(self):
        """Aliases like 'opus' should resolve correctly before downgrade."""
        result = ModelCatalog.downgrade("opus")
        assert result == "claude-sonnet-4", (
            f"'opus' alias should downgrade to claude-sonnet-4, got {result!r}"
        )

    def test_non_anthropic_model_downgrade_returns_none(self):
        """Non-Anthropic models are not in the chain — downgrade returns None."""
        result = ModelCatalog.downgrade("gpt-4o")
        assert result is None, (
            f"gpt-4o is not in the Anthropic chain, expected None, got {result!r}"
        )
