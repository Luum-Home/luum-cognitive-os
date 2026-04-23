"""Unit tests for lib/execution_profile.py."""

import pytest

from lib.execution_profile import (
    BALANCED_GENERAL,
    LONG_CONTEXT_ANALYSIS,
    LOW_COST_BULK,
    resolve_execution_profile,
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
