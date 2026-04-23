"""Unit tests for lib/execution_profile.py."""

import pytest

from lib.execution_profile import (
    BALANCED_GENERAL,
    FAST_TURNAROUND,
    FRONTIER_REASONING,
    LONG_CONTEXT_ANALYSIS,
    LOW_COST_BULK,
    provider_cascade_for_profile,
    resolve_execution_profile,
    resolve_runtime_execution_profile,
)

pytestmark = pytest.mark.unit


class TestResolveExecutionProfile:
    def test_known_task_maps_to_expected_profile(self):
        profile = resolve_execution_profile("sdd-explore")
        assert profile.id == LONG_CONTEXT_ANALYSIS.id
        assert profile.min_context_window >= 200_000

    def test_unknown_task_uses_balanced_general(self):
        profile = resolve_execution_profile("totally-unknown-task")
        assert profile.id == BALANCED_GENERAL.id

    def test_local_preference_switches_to_local_requirement(self):
        profile = resolve_execution_profile("sdd-apply", prefer_local=True)
        assert profile.require_local is True
        assert profile.id.endswith("+local")

    def test_budget_floor_prefers_free_models(self):
        profile = resolve_execution_profile("document-feature", budget_remaining=0.0)
        assert profile.prefer_free is True
        assert profile.max_total_cost_per_1m == 0.0

    def test_skill_tier_frontier_maps_to_frontier_profile(self):
        profile = resolve_runtime_execution_profile(
            "unknown-task",
            skill_requirements={"tier": "frontier"},
        )
        assert profile.id == FRONTIER_REASONING.id

    def test_skill_long_context_overrides_tier(self):
        profile = resolve_runtime_execution_profile(
            "unknown-task",
            skill_requirements={"tier": "cheap", "need_long_context": True},
        )
        assert profile.id == LONG_CONTEXT_ANALYSIS.id

    def test_explicit_skill_execution_profile_wins(self):
        profile = resolve_runtime_execution_profile(
            "sdd-propose",
            skill_requirements={"execution_profile": "fast_turnaround"},
        )
        assert profile.id == FAST_TURNAROUND.id


class TestExecutionProfileMatching:
    def test_budget_profile_rejects_expensive_candidate(self):
        expensive = {
            "reasoning": 9,
            "speed": 9,
            "code": 9,
            "context": 1_000_000,
            "cost_per_1m_in": 15.0,
            "cost_per_1m_out": 75.0,
        }
        assert LOW_COST_BULK.matches_capabilities(expensive) is False

    def test_long_context_profile_accepts_large_context_candidate(self):
        candidate = {
            "reasoning": 8,
            "speed": 5,
            "code": 7,
            "context": 1_000_000,
            "cost_per_1m_in": 1.25,
            "cost_per_1m_out": 5.0,
        }
        assert LONG_CONTEXT_ANALYSIS.matches_capabilities(candidate) is True


class TestProviderCascadeForProfile:
    def test_frontier_profile_prefers_claude_before_qwen(self):
        cascade = provider_cascade_for_profile(FRONTIER_REASONING, ["qwen", "claude"])
        assert cascade == ["claude", "qwen"]

    def test_low_cost_profile_prefers_qwen_before_claude(self):
        cascade = provider_cascade_for_profile(LOW_COST_BULK, ["claude", "qwen"])
        assert cascade == ["qwen", "claude"]

    def test_balanced_profile_preserves_existing_order(self):
        cascade = provider_cascade_for_profile(BALANCED_GENERAL, ["claude", "qwen"])
        assert cascade == ["claude", "qwen"]
