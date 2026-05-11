"""Unit tests for lib/memory_governance.py — ADR-261 Memory Governance v2.

Test coverage:
- get_policy returns correct MemoryTypePolicy for each of the six governed types
- get_policy returns the no-op default for an unrecognized type string
- is_stale returns False for age < stale_after_seconds; True for age >= threshold
- is_stale always returns False for types with staleness="never" (e.g., "decision")
- boosted_score is a pass-through for unknown types (raw_score unchanged)
- assess_freshness returns state="stable" and note=None for staleness="never" + verification="none" types
- assess_freshness returns state="stale" for hard-staleness types past threshold
- assess_freshness returns note != None for verify_before_use types regardless of age
- boosted_score is NOT idempotent for governed types (documents multiplicative behaviour)
- assess_freshness returns correct state at fresh/aging/stale boundaries
"""

from __future__ import annotations

import pytest

from lib.memory_governance import (
    MemoryTypePolicy,
    assess_freshness,
    boosted_score,
    get_policy,
    is_stale,
)

# ---------------------------------------------------------------------------
# Constants for readability
# ---------------------------------------------------------------------------

_DAY = 86_400  # seconds in a day


# ===========================================================================
# get_policy — correct policy for governed types
# ===========================================================================


class TestGetPolicyGoverned:
    def test_preference_policy(self) -> None:
        p = get_policy("preference")
        assert p.type_name == "preference"
        assert p.verification == "corroborate"
        assert p.staleness == "soft"
        assert p.stale_after_seconds == 7_776_000
        assert p.recall_boost == pytest.approx(1.4)

    def test_identity_policy(self) -> None:
        p = get_policy("identity")
        assert p.type_name == "identity"
        assert p.verification == "verify_before_use"
        assert p.staleness == "soft"
        assert p.stale_after_seconds == 15_552_000
        assert p.recall_boost == pytest.approx(1.2)

    def test_fact_policy(self) -> None:
        p = get_policy("fact")
        assert p.type_name == "fact"
        assert p.verification == "corroborate"
        assert p.staleness == "hard"
        assert p.stale_after_seconds == 2_592_000
        assert p.recall_boost == pytest.approx(1.0)

    def test_procedure_policy(self) -> None:
        p = get_policy("procedure")
        assert p.type_name == "procedure"
        assert p.verification == "verify_before_use"
        assert p.staleness == "soft"
        assert p.stale_after_seconds == 5_184_000
        assert p.recall_boost == pytest.approx(1.6)

    def test_blocker_policy(self) -> None:
        p = get_policy("blocker")
        assert p.type_name == "blocker"
        assert p.verification == "verify_before_use"
        assert p.staleness == "hard"
        assert p.stale_after_seconds == 864_000
        assert p.recall_boost == pytest.approx(1.8)

    def test_decision_policy(self) -> None:
        p = get_policy("decision")
        assert p.type_name == "decision"
        assert p.verification == "none"
        assert p.staleness == "never"
        assert p.stale_after_seconds is None
        assert p.recall_boost == pytest.approx(1.1)

    def test_returns_frozen_dataclass(self) -> None:
        p = get_policy("preference")
        assert isinstance(p, MemoryTypePolicy)
        with pytest.raises((AttributeError, TypeError)):
            p.recall_boost = 99.0  # type: ignore[misc]  # frozen dataclass


class TestGetPolicyUnknown:
    def test_unknown_type_returns_noop(self) -> None:
        p = get_policy("unknown_type")
        assert p.type_name == "unknown_type"
        assert p.verification == "none"
        assert p.staleness == "never"
        assert p.stale_after_seconds is None
        assert p.recall_boost == pytest.approx(1.0)

    def test_empty_string_returns_noop(self) -> None:
        p = get_policy("")
        assert p.verification == "none"
        assert p.staleness == "never"
        assert p.recall_boost == pytest.approx(1.0)

    def test_bugfix_returns_noop(self) -> None:
        """Existing luum type not in table — must be a no-op."""
        p = get_policy("bugfix")
        assert p.staleness == "never"
        assert p.recall_boost == pytest.approx(1.0)

    def test_discovery_returns_noop(self) -> None:
        p = get_policy("discovery")
        assert p.staleness == "never"
        assert p.recall_boost == pytest.approx(1.0)


# ===========================================================================
# is_stale
# ===========================================================================


class TestIsStale:
    # --- preference (soft, 90 days = 7_776_000 s) ---

    def test_preference_stale_above_threshold(self) -> None:
        assert is_stale(100 * _DAY, "preference") is True

    def test_preference_stale_at_exact_threshold(self) -> None:
        assert is_stale(90 * _DAY, "preference") is True

    def test_preference_not_stale_below_threshold(self) -> None:
        assert is_stale(50 * _DAY, "preference") is False

    def test_preference_not_stale_zero_age(self) -> None:
        assert is_stale(0, "preference") is False

    # --- blocker (hard, 10 days = 864_000 s) ---

    def test_blocker_stale_above_threshold(self) -> None:
        assert is_stale(11 * _DAY, "blocker") is True

    def test_blocker_not_stale_below_threshold(self) -> None:
        assert is_stale(9 * _DAY, "blocker") is False

    # --- fact (hard, 30 days) ---

    def test_fact_stale_above_threshold(self) -> None:
        assert is_stale(31 * _DAY, "fact") is True

    def test_fact_not_stale_below_threshold(self) -> None:
        assert is_stale(29 * _DAY, "fact") is False

    # --- decision (never) ---

    def test_decision_never_stale_large_age(self) -> None:
        assert is_stale(1000 * _DAY, "decision") is False

    def test_decision_never_stale_zero_age(self) -> None:
        assert is_stale(0, "decision") is False

    # --- unknown type (no-op, staleness=never) ---

    def test_unknown_never_stale(self) -> None:
        assert is_stale(9999 * _DAY, "unknown_xyz") is False


# ===========================================================================
# boosted_score
# ===========================================================================


class TestBoostedScore:
    def test_blocker_boost(self) -> None:
        result = boosted_score(0.5, "blocker")
        assert result == pytest.approx(0.9)  # 0.5 * 1.8

    def test_preference_boost(self) -> None:
        result = boosted_score(0.5, "preference")
        assert result == pytest.approx(0.7)  # 0.5 * 1.4

    def test_unknown_type_passthrough(self) -> None:
        """Unknown type -> recall_boost=1.0 -> no change."""
        assert boosted_score(0.5, "unknown") == pytest.approx(0.5)

    def test_empty_type_passthrough(self) -> None:
        assert boosted_score(0.75, "") == pytest.approx(0.75)

    def test_bugfix_passthrough(self) -> None:
        """Existing unmanaged type must be a pass-through."""
        assert boosted_score(0.6, "bugfix") == pytest.approx(0.6)

    def test_fact_neutral_boost(self) -> None:
        """fact has boost=1.0 — result must be unchanged."""
        assert boosted_score(0.42, "fact") == pytest.approx(0.42)

    def test_decision_slight_boost(self) -> None:
        assert boosted_score(0.5, "decision") == pytest.approx(0.55)  # 0.5 * 1.1

    # --- Idempotency note (documents multiplicative behaviour) ---
    def test_boost_is_multiplicative_not_idempotent(self) -> None:
        """boosted_score is NOT idempotent for governed types.

        Applying it twice multiplies the boost twice.  Callers must apply
        the boost exactly once per retrieval cycle.

        This test documents and asserts the multiplicative behaviour:
            boosted_score(boosted_score(0.5, "blocker"), "blocker")
            == 0.5 * 1.8 * 1.8
            == 1.62
        rather than 0.9 (idempotent would return 0.9 twice).
        """
        once = boosted_score(0.5, "blocker")       # 0.9
        twice = boosted_score(once, "blocker")      # 1.62
        assert once == pytest.approx(0.9)
        assert twice == pytest.approx(0.5 * 1.8 * 1.8)
        # Confirm they differ (i.e., NOT idempotent)
        assert once != pytest.approx(twice)


# ===========================================================================
# assess_freshness — state boundaries
# ===========================================================================


class TestAssessFreshness:
    # --- staleness="never" + verification="none" (decision) ---

    def test_decision_returns_stable_no_note(self) -> None:
        result = assess_freshness(1000 * _DAY, "decision")
        assert result.state == "stable"
        assert result.note is None

    def test_decision_zero_age_stable(self) -> None:
        result = assess_freshness(0, "decision")
        assert result.state == "stable"
        assert result.note is None

    # --- unknown type (no-op default: staleness=never, verification=none) ---

    def test_unknown_stable_no_note(self) -> None:
        result = assess_freshness(9999 * _DAY, "unknown_xyz")
        assert result.state == "stable"
        assert result.note is None

    # --- hard-stale (fact, 30 days) ---

    def test_fact_stale_state(self) -> None:
        result = assess_freshness(31 * _DAY, "fact")
        assert result.state == "stale"
        assert result.note is not None

    def test_fact_aging_state(self) -> None:
        # 75% of 30 days = 22.5 days -> 23 days is aging
        result = assess_freshness(23 * _DAY, "fact")
        assert result.state == "aging"

    def test_fact_fresh_state(self) -> None:
        result = assess_freshness(10 * _DAY, "fact")
        assert result.state == "fresh"
        assert result.note is None  # corroborate + fresh -> no note

    # --- hard-stale (blocker, 10 days) ---

    def test_blocker_stale_state(self) -> None:
        result = assess_freshness(11 * _DAY, "blocker")
        assert result.state == "stale"
        assert result.note is not None

    # --- soft-stale (preference, 90 days) ---

    def test_preference_stale_has_note(self) -> None:
        result = assess_freshness(100 * _DAY, "preference")
        assert result.state == "stale"
        assert result.note is not None

    def test_preference_aging_has_note(self) -> None:
        # 75% of 90 days = 67.5 days -> 70 days is aging
        result = assess_freshness(70 * _DAY, "preference")
        assert result.state == "aging"
        assert result.note is not None

    def test_preference_fresh_no_note(self) -> None:
        result = assess_freshness(30 * _DAY, "preference")
        assert result.state == "fresh"
        assert result.note is None  # corroborate + fresh -> no note

    # --- verify_before_use always emits note regardless of age ---

    def test_blocker_fresh_still_has_note(self) -> None:
        result = assess_freshness(1 * _DAY, "blocker")
        assert result.state == "fresh"
        assert result.note is not None  # verify_before_use always notes

    def test_procedure_fresh_has_note(self) -> None:
        result = assess_freshness(1 * _DAY, "procedure")
        assert result.state == "fresh"
        assert result.note is not None

    def test_identity_fresh_has_note(self) -> None:
        result = assess_freshness(1 * _DAY, "identity")
        assert result.state == "fresh"
        assert result.note is not None

    # --- staleness="never" + verify_before_use (identity — wait, identity is soft!) ---
    # identity is soft/180d + verify_before_use. Test stable is NOT returned for it.

    def test_identity_large_age_is_stale_not_stable(self) -> None:
        result = assess_freshness(200 * _DAY, "identity")
        assert result.state == "stale"
        # note must be non-None (verify_before_use)
        assert result.note is not None

    # --- FreshnessResult is a frozen dataclass ---

    def test_freshness_result_frozen(self) -> None:
        result = assess_freshness(0, "decision")
        with pytest.raises((AttributeError, TypeError)):
            result.state = "stale"  # type: ignore[misc]

    # --- Boundary: exact threshold ---

    def test_exact_threshold_is_stale(self) -> None:
        """Observations at exactly stale_after_seconds are considered stale."""
        # blocker: 864_000 s = 10 days
        result = assess_freshness(864_000, "blocker")
        assert result.state == "stale"

    def test_one_second_before_threshold_is_not_stale(self) -> None:
        result = assess_freshness(863_999, "blocker")
        assert result.state != "stale"
