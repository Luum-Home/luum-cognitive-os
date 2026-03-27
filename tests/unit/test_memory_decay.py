"""Unit tests for lib/memory_decay.py

Validates relevance calculation, decay rates per type, search result
re-ranking, pruning threshold, and decay statistics.
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from lib.memory_decay import (
    DECAY_RATES,
    DEFAULT_DECAY_RATE,
    apply_decay_to_search_results,
    calculate_relevance,
    get_decay_stats,
    should_prune,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obs(type_: str = "discovery", days_ago: float = 0, now: Optional[datetime] = None) -> dict:
    """Build an observation dict *days_ago* days before *now*."""
    if now is None:
        now = datetime.now(timezone.utc)
    ts = now - timedelta(days=days_ago)
    return {"type": type_, "timestamp": ts.isoformat()}


def _obs_epoch(type_: str, days_ago: float, now: Optional[datetime] = None) -> dict:
    """Build an observation dict using timestamp_epoch."""
    if now is None:
        now = datetime.now(timezone.utc)
    ts = now - timedelta(days=days_ago)
    return {"type": type_, "timestamp_epoch": ts.timestamp()}


# ---------------------------------------------------------------------------
# calculate_relevance
# ---------------------------------------------------------------------------


class TestCalculateRelevance:
    """Tests for calculate_relevance()."""

    def test_fresh_observation_has_full_relevance(self):
        """A just-created observation should have relevance ~1.0."""
        now = datetime.now(timezone.utc)
        obs = _obs("decision", days_ago=0, now=now)
        assert calculate_relevance(obs, now) == pytest.approx(1.0, abs=0.001)

    def test_bugfix_decays_faster_than_decision(self):
        """After 30 days, a bugfix should be less relevant than a decision."""
        now = datetime.now(timezone.utc)
        bugfix = _obs("bugfix", days_ago=30, now=now)
        decision = _obs("decision", days_ago=30, now=now)
        assert calculate_relevance(bugfix, now) < calculate_relevance(decision, now)

    def test_architecture_barely_decays_over_100_days(self):
        """Architecture decisions should retain >70% relevance after 100 days."""
        now = datetime.now(timezone.utc)
        obs = _obs("architecture", days_ago=100, now=now)
        score = calculate_relevance(obs, now)
        assert score > 0.70

    def test_preference_almost_never_decays(self):
        """Preferences should retain >90% relevance after 100 days."""
        now = datetime.now(timezone.utc)
        obs = _obs("preference", days_ago=100, now=now)
        score = calculate_relevance(obs, now)
        assert score > 0.90

    def test_relevance_never_below_zero(self):
        """Even after a very long time, relevance should not go below 0."""
        now = datetime.now(timezone.utc)
        obs = _obs("bugfix", days_ago=10000, now=now)
        score = calculate_relevance(obs, now)
        assert score >= 0.0

    def test_relevance_never_above_one(self):
        """Relevance should never exceed 1.0."""
        now = datetime.now(timezone.utc)
        obs = _obs("discovery", days_ago=0, now=now)
        score = calculate_relevance(obs, now)
        assert score <= 1.0

    def test_unknown_type_uses_default_rate(self):
        """An unknown type should use DEFAULT_DECAY_RATE."""
        now = datetime.now(timezone.utc)
        obs = _obs("unknown_type_xyz", days_ago=50, now=now)
        expected = math.exp(-DEFAULT_DECAY_RATE * 50)
        assert calculate_relevance(obs, now) == pytest.approx(expected, abs=0.001)

    def test_future_date_returns_full_relevance(self):
        """An observation with a future timestamp should have relevance 1.0."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=10)
        obs = {"type": "decision", "timestamp": future.isoformat()}
        assert calculate_relevance(obs, now) == pytest.approx(1.0, abs=0.001)

    def test_missing_timestamp_returns_full_relevance(self):
        """An observation without any timestamp should default to relevance 1.0."""
        obs = {"type": "bugfix"}
        assert calculate_relevance(obs) == pytest.approx(1.0, abs=0.001)

    def test_epoch_timestamp_works(self):
        """Observations using timestamp_epoch should be handled correctly."""
        now = datetime.now(timezone.utc)
        obs = _obs_epoch("config", days_ago=30, now=now)
        expected = math.exp(-DECAY_RATES["config"] * 30)
        assert calculate_relevance(obs, now) == pytest.approx(expected, abs=0.01)

    def test_config_decays_faster_than_pattern(self):
        """Config changes should decay faster than patterns at 60 days."""
        now = datetime.now(timezone.utc)
        config = _obs("config", days_ago=60, now=now)
        pattern = _obs("pattern", days_ago=60, now=now)
        assert calculate_relevance(config, now) < calculate_relevance(pattern, now)

    def test_exact_decay_formula(self):
        """Verify the exponential decay formula produces correct values."""
        now = datetime.now(timezone.utc)
        days = 20
        obs = _obs("discovery", days_ago=days, now=now)
        expected = math.exp(-DECAY_RATES["discovery"] * days)
        assert calculate_relevance(obs, now) == pytest.approx(expected, abs=0.001)


# ---------------------------------------------------------------------------
# apply_decay_to_search_results
# ---------------------------------------------------------------------------


class TestApplyDecayToSearchResults:
    """Tests for apply_decay_to_search_results()."""

    def test_results_sorted_by_decay_score(self):
        """Results should be sorted descending by decay_score."""
        now = datetime.now(timezone.utc)
        results = [
            _obs("bugfix", days_ago=60, now=now),
            _obs("decision", days_ago=10, now=now),
            _obs("architecture", days_ago=5, now=now),
        ]
        ranked = apply_decay_to_search_results(results, now)
        scores = [r["decay_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_decay_score_key_added(self):
        """Each result dict should have a 'decay_score' key."""
        now = datetime.now(timezone.utc)
        results = [_obs("bugfix", days_ago=10, now=now)]
        ranked = apply_decay_to_search_results(results, now)
        assert "decay_score" in ranked[0]

    def test_original_list_not_mutated(self):
        """The original results list should not be modified."""
        now = datetime.now(timezone.utc)
        results = [_obs("bugfix", days_ago=10, now=now)]
        original_keys = set(results[0].keys())
        apply_decay_to_search_results(results, now)
        assert set(results[0].keys()) == original_keys

    def test_empty_results(self):
        """An empty list should return an empty list."""
        assert apply_decay_to_search_results([]) == []

    def test_fresh_results_all_near_one(self):
        """All fresh results should have decay_score close to 1.0."""
        now = datetime.now(timezone.utc)
        results = [_obs("bugfix", 0, now), _obs("decision", 0, now)]
        ranked = apply_decay_to_search_results(results, now)
        for r in ranked:
            assert r["decay_score"] == pytest.approx(1.0, abs=0.001)


# ---------------------------------------------------------------------------
# should_prune
# ---------------------------------------------------------------------------


class TestShouldPrune:
    """Tests for should_prune()."""

    def test_fresh_observation_not_pruned(self):
        """A fresh observation should not be pruned."""
        now = datetime.now(timezone.utc)
        obs = _obs("bugfix", days_ago=0, now=now)
        assert should_prune(obs, threshold=0.1, now=now) is False

    def test_very_old_bugfix_pruned(self):
        """A very old bugfix should be pruned at default threshold."""
        now = datetime.now(timezone.utc)
        # At 0.02 rate, -ln(0.1)/0.02 ~ 115 days to hit 0.1
        obs = _obs("bugfix", days_ago=200, now=now)
        assert should_prune(obs, threshold=0.1, now=now) is True

    def test_custom_threshold(self):
        """Pruning should respect a custom threshold."""
        now = datetime.now(timezone.utc)
        obs = _obs("bugfix", days_ago=50, now=now)
        # At 50 days: e^(-0.02*50) ~ 0.368
        assert should_prune(obs, threshold=0.5, now=now) is True
        assert should_prune(obs, threshold=0.3, now=now) is False


# ---------------------------------------------------------------------------
# get_decay_stats
# ---------------------------------------------------------------------------


class TestGetDecayStats:
    """Tests for get_decay_stats()."""

    def test_all_fresh_are_active(self):
        """All fresh observations should be counted as active."""
        now = datetime.now(timezone.utc)
        observations = [_obs("decision", 0, now) for _ in range(5)]
        stats = get_decay_stats(observations)
        assert stats["total"] == 5
        assert stats["active"] == 5
        assert stats["fading"] == 0
        assert stats["stale"] == 0

    def test_mixed_ages(self):
        """Mix of ages should distribute across active, fading, stale."""
        now = datetime.now(timezone.utc)
        observations = [
            _obs("bugfix", days_ago=0, now=now),      # active (1.0)
            _obs("bugfix", days_ago=50, now=now),      # fading (e^-1 ~ 0.37)
            _obs("bugfix", days_ago=200, now=now),     # stale (e^-4 ~ 0.018)
        ]
        stats = get_decay_stats(observations)
        assert stats["total"] == 3
        assert stats["active"] == 1
        assert stats["fading"] == 1
        assert stats["stale"] == 1

    def test_empty_list(self):
        """Empty list should return all zeros."""
        stats = get_decay_stats([])
        assert stats == {"total": 0, "active": 0, "fading": 0, "stale": 0}
