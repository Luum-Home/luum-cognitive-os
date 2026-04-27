"""Unit tests for lib.engram_lifecycle — Phase 1 of ADR-071.

Covers all 18 tests listed in the feature plan:
  .cognitive-os/plans/features/engram-lifecycle-evolution.md

Pure-function tests need no mocking.  Integration-flavoured tests
(save, search, reinforce) stub engram_client via unittest.mock.patch.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest

from lib.engram_lifecycle import (
    EngramLifecycle,
    adjusted_score,
    decay_retention,
    reinforce_confidence,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXED_NOW = datetime(2026, 4, 27, 15, 30, 0)


def _make_lc(now: datetime = _FIXED_NOW) -> EngramLifecycle:
    """Return an EngramLifecycle with a fixed clock for deterministic tests."""
    return EngramLifecycle(now=lambda: now)


def _obs(
    content: str = "",
    title: str = "t",
    obs_type: str = "manual",
    topic_key: str = "",
    project: str = "",
    obs_id: int = 1,
) -> dict[str, Any]:
    return {
        "id": obs_id,
        "title": title,
        "content": content,
        "type": obs_type,
        "topic_key": topic_key,
        "project": project,
        "created_at": "2026-04-27T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Trailer round-trip
# ---------------------------------------------------------------------------


class TestTrailerRoundTrip:
    def test_trailer_round_trip(self):
        lc = _make_lc()
        content = "Some observation text."
        enriched = lc.build_content_with_trailer(content, "decision")
        trailer = lc._parse_trailer(enriched)

        assert trailer is not None
        assert trailer["confidence"] == 0.5
        assert trailer["decay_class"] == "decision"
        assert trailer["reinforcement_count"] == 0
        assert "last_reinforced" in trailer

    def test_trailer_missing_returns_none(self):
        lc = _make_lc()
        result = lc._parse_trailer("observation content with no lifecycle block")
        assert result is None

    def test_trailer_malformed_returns_none(self):
        lc = _make_lc()
        malformed = "text\n<engram-lifecycle>\n{bad json{{{\n</engram-lifecycle>"
        result = lc._parse_trailer(malformed)
        assert result is None

    def test_trailer_truncated_json_returns_none(self):
        lc = _make_lc()
        truncated = 'text\n<engram-lifecycle>\n{"confidence": 0.5, "last_re\n</engram-lifecycle>'
        result = lc._parse_trailer(truncated)
        assert result is None


# ---------------------------------------------------------------------------
# decay_retention
# ---------------------------------------------------------------------------


class TestDecayRetention:
    def test_decay_at_zero_days_is_one(self):
        for tau in EngramLifecycle.DECAY_TAU.values():
            r = decay_retention(0, tau)
            assert abs(r - 1.0) < 1e-9, f"R(0) must be 1.0 for tau={tau}, got {r}"

    def test_decay_monotonically_decreasing(self):
        for tau in EngramLifecycle.DECAY_TAU.values():
            r0 = decay_retention(0, tau)
            r30 = decay_retention(30, tau)
            r90 = decay_retention(90, tau)
            r365 = decay_retention(365, tau)
            assert r0 >= r30 >= r90 >= r365, (
                f"Monotonicity violated for tau={tau}: {r0}, {r30}, {r90}, {r365}"
            )
            # Strict inequality for all tau values when days differ meaningfully
            assert r0 > r365, f"R(0) must be > R(365) for tau={tau}"

    def test_decay_bounds_never_negative(self):
        for tau in EngramLifecycle.DECAY_TAU.values():
            for t in range(0, 3651, 100):
                r = decay_retention(float(t), tau)
                assert r > 0, f"decay_retention({t}, {tau}) returned {r} — must be > 0"
                assert r <= 1.0, f"decay_retention({t}, {tau}) returned {r} — must be <= 1.0"


# ---------------------------------------------------------------------------
# reinforce_confidence
# ---------------------------------------------------------------------------


class TestReinforceConfidence:
    def test_reinforcement_increases_confidence(self):
        c = 0.5
        prev = c
        for _ in range(20):
            c = reinforce_confidence(c)
            assert c > prev, "Confidence must strictly increase on each reinforcement"
            prev = c

    def test_reinforcement_never_reaches_one(self):
        c = 0.5
        for i in range(50):
            c = reinforce_confidence(c)
            assert c < 1.0, f"Confidence reached 1.0 after {i + 1} reinforcements"

    def test_reinforcement_starts_from_zero_point_five(self):
        c = 0.5
        beta = 0.15
        for _ in range(30):
            c = reinforce_confidence(c, beta)
        # After 30 steps, confidence should be above 0.98 (convergence check)
        expected_lower = 1.0 - (0.5 * (1 - beta) ** 30)
        assert c > expected_lower * 0.99, (
            f"Confidence {c} is unexpectedly low after 30 reinforcements"
        )
        assert c < 1.0


# ---------------------------------------------------------------------------
# adjusted_score
# ---------------------------------------------------------------------------


class TestAdjustedScore:
    def test_adjusted_score_bounded(self):
        rng = random.Random(42)
        for _ in range(1000):
            base = rng.random()
            confidence = rng.random()
            retention = rng.random()
            score = adjusted_score(base, confidence, retention, alpha=0.3)
            assert 0.0 <= score <= 1.0, f"Score out of bounds: {score}"

    def test_adjusted_score_alpha_zero_equals_base(self):
        for base in [0.0, 0.3, 0.7, 1.0]:
            score = adjusted_score(base, confidence=0.9, retention=0.8, alpha=0.0)
            assert abs(score - base) < 1e-9, (
                f"alpha=0 should return base_score exactly, got {score} for base={base}"
            )

    def test_adjusted_score_alpha_one_equals_confidence_times_retention(self):
        confidence = 0.8
        retention = 0.7
        score = adjusted_score(0.5, confidence, retention, alpha=1.0)
        expected = confidence * retention
        assert abs(score - expected) < 1e-9, (
            f"alpha=1 should return confidence * retention = {expected}, got {score}"
        )


# ---------------------------------------------------------------------------
# Decay class mapping
# ---------------------------------------------------------------------------


class TestDecayClassMapping:
    def test_decay_class_mapping_from_type(self):
        lc = _make_lc()
        assert lc._decay_class_for_type("bugfix") == "bugfix"
        assert lc._decay_class_for_type("architecture") == "architecture"
        assert lc._decay_class_for_type("decision") == "decision"
        assert lc._decay_class_for_type("pattern") == "pattern"
        assert lc._decay_class_for_type("discovery") == "discovery"
        assert lc._decay_class_for_type("config") == "discovery"
        assert lc._decay_class_for_type("unknown_type") == "manual"
        assert lc._decay_class_for_type("preference") == "manual"
        assert lc._decay_class_for_type("") == "manual"


# ---------------------------------------------------------------------------
# save() integration (engram_client stubbed)
# ---------------------------------------------------------------------------


class TestSave:
    def test_save_appends_trailer(self):
        lc = _make_lc()
        saved_content: list[str] = []

        def fake_save(title=None, content=None, *, type_="manual", topic_key="", project="", timeout=10):
            saved_content.append(content)
            return {"id": 99, "title": title, "content": content}

        with patch("lib.engram_lifecycle.engram_client.save_observation", side_effect=fake_save):
            result = lc.save("My title", "Original body", type_="decision")

        assert result is not None
        assert len(saved_content) == 1
        assert "<engram-lifecycle>" in saved_content[0]
        assert "</engram-lifecycle>" in saved_content[0]

        trailer = lc._parse_trailer(saved_content[0])
        assert trailer is not None
        assert trailer["decay_class"] == "decision"
        assert trailer["confidence"] == 0.5
        assert trailer["reinforcement_count"] == 0

    def test_save_returns_none_when_engram_unavailable(self):
        lc = _make_lc()
        with patch("lib.engram_lifecycle.engram_client.save_observation", return_value=None):
            result = lc.save("title", "content", type_="manual")
        assert result is None


# ---------------------------------------------------------------------------
# search() integration (engram_client stubbed)
# ---------------------------------------------------------------------------


class TestSearch:
    def _make_obs_with_trailer(
        self,
        lc: EngramLifecycle,
        obs_id: int,
        decay_class: str,
        days_old: float,
        confidence: float,
    ) -> dict[str, Any]:
        """Build a mock observation whose trailer encodes a specific age."""
        last_reinforced_dt = _FIXED_NOW - timedelta(days=days_old)
        trailer = {
            "confidence": confidence,
            "last_reinforced": last_reinforced_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reinforcement_count": 3,
            "decay_class": decay_class,
        }
        content = f"Body text.\n<engram-lifecycle>\n{json.dumps(trailer)}\n</engram-lifecycle>"
        return _obs(content=content, obs_id=obs_id)

    def test_search_re_ranks_newer_over_older(self):
        lc = _make_lc()
        newer = self._make_obs_with_trailer(lc, 1, "decision", days_old=5, confidence=0.8)
        older = self._make_obs_with_trailer(lc, 2, "decision", days_old=120, confidence=0.8)

        with patch(
            "lib.engram_lifecycle.engram_client.search_observations",
            return_value=[older, newer],
        ):
            results = lc.search("test query", lifecycle_weight=True)

        assert len(results) == 2
        # Newer observation should sort first due to higher retention
        assert results[0]["id"] == 1, (
            f"Expected newer obs (id=1) first, got id={results[0]['id']}"
        )
        assert results[0]["adjusted_score"] > results[1]["adjusted_score"]

    def test_search_without_lifecycle_weight_returns_base_order(self):
        lc = _make_lc()
        obs_a = _obs(content="No trailer", obs_id=10)
        obs_b = _obs(content="No trailer", obs_id=20)

        with patch(
            "lib.engram_lifecycle.engram_client.search_observations",
            return_value=[obs_a, obs_b],
        ):
            results = lc.search("query", lifecycle_weight=False)

        assert results[0]["id"] == 10
        assert results[1]["id"] == 20
        # No lifecycle keys added when lifecycle_weight=False
        assert "adjusted_score" not in results[0]

    def test_search_results_without_trailer_not_penalized(self):
        lc = _make_lc()
        obs_no_trailer = _obs(content="Plain content, no trailer", obs_id=5)

        with patch(
            "lib.engram_lifecycle.engram_client.search_observations",
            return_value=[obs_no_trailer],
        ):
            results = lc.search("query", lifecycle_weight=True)

        assert len(results) == 1
        assert results[0]["confidence"] == 0.5
        assert results[0]["retention"] == 1.0


# ---------------------------------------------------------------------------
# reinforce() integration (engram_http_client stubbed)
# ---------------------------------------------------------------------------


class TestReinforce:
    def test_reinforce_updates_last_reinforced(self):
        lc = _make_lc(now=datetime(2026, 4, 27, 12, 0, 0))
        old_time = "2026-04-20T10:00:00Z"
        trailer = {
            "confidence": 0.6,
            "last_reinforced": old_time,
            "reinforcement_count": 2,
            "decay_class": "decision",
        }
        content = f"Body.\n<engram-lifecycle>\n{json.dumps(trailer)}\n</engram-lifecycle>"
        obs = _obs(content=content, obs_id=42, obs_type="decision")

        updated_calls: list[dict[str, Any]] = []

        def fake_update(obs_id, *, content=None, title=None, type_=None, topic_key=None,
                        base_url=None, timeout=5.0):
            updated_calls.append({"content": content})
            return {"id": obs_id, "content": content}

        with patch("lib.engram_lifecycle.engram_http_client.is_available", return_value=True):
            with patch("lib.engram_lifecycle.engram_http_client.get_observation", return_value=obs):
                with patch("lib.engram_lifecycle.engram_http_client.update_observation", side_effect=fake_update):
                    result = lc.reinforce(42)

        assert result is True
        assert len(updated_calls) == 1

        new_trailer = lc._parse_trailer(updated_calls[0]["content"])
        assert new_trailer is not None
        assert new_trailer["last_reinforced"] == "2026-04-27T12:00:00Z"
        assert new_trailer["reinforcement_count"] == 3
        assert new_trailer["confidence"] > 0.6

    def test_reinforce_nonexistent_id_returns_false(self):
        lc = _make_lc()
        with patch("lib.engram_lifecycle.engram_http_client.is_available", return_value=True):
            with patch("lib.engram_lifecycle.engram_http_client.get_observation", return_value=None):
                result = lc.reinforce("nonexistent-999")
        assert result is False

    def test_reinforce_observation_without_trailer_gets_default(self):
        lc = _make_lc()
        obs = _obs(content="Plain old content, no trailer", obs_id=77, obs_type="bugfix")

        updated_calls: list[dict[str, Any]] = []

        def fake_update(obs_id, *, content=None, title=None, type_=None, topic_key=None,
                        base_url=None, timeout=5.0):
            updated_calls.append({"content": content})
            return {"id": obs_id, "content": content}

        with patch("lib.engram_lifecycle.engram_http_client.is_available", return_value=True):
            with patch("lib.engram_lifecycle.engram_http_client.get_observation", return_value=obs):
                with patch("lib.engram_lifecycle.engram_http_client.update_observation", side_effect=fake_update):
                    result = lc.reinforce(77)

        assert result is True
        new_trailer = lc._parse_trailer(updated_calls[0]["content"])
        assert new_trailer is not None
        assert new_trailer["reinforcement_count"] == 1
        assert new_trailer["decay_class"] == "bugfix"
        assert new_trailer["confidence"] > 0.5

    def test_reinforce_returns_false_when_daemon_down(self):
        lc = _make_lc()
        with patch("lib.engram_lifecycle.engram_http_client.is_available", return_value=False):
            result = lc.reinforce(42)
        assert result is False

    def test_reinforce_confidence_increases_by_beta(self):
        """Single reinforce: confidence delta equals (1 - current) * BETA."""
        lc = _make_lc()
        initial_confidence = 0.7
        trailer = {
            "confidence": initial_confidence,
            "last_reinforced": "2026-04-20T10:00:00Z",
            "reinforcement_count": 1,
            "decay_class": "decision",
        }
        content = f"Body.\n<engram-lifecycle>\n{json.dumps(trailer)}\n</engram-lifecycle>"
        obs = _obs(content=content, obs_id=10, obs_type="decision")

        updated_calls: list[dict[str, Any]] = []

        def fake_update(obs_id, *, content=None, title=None, type_=None, topic_key=None,
                        base_url=None, timeout=5.0):
            updated_calls.append({"content": content})
            return {"id": obs_id, "content": content}

        with patch("lib.engram_lifecycle.engram_http_client.is_available", return_value=True):
            with patch("lib.engram_lifecycle.engram_http_client.get_observation", return_value=obs):
                with patch("lib.engram_lifecycle.engram_http_client.update_observation", side_effect=fake_update):
                    lc.reinforce(10)

        new_trailer = lc._parse_trailer(updated_calls[0]["content"])
        expected_confidence = initial_confidence + (1.0 - initial_confidence) * lc.BETA
        assert abs(new_trailer["confidence"] - expected_confidence) < 1e-9
