# SCOPE: os-only
"""Memory Governance v2 — Typed memory policies with verification, staleness, and recall boost.

Implements the static rule table defined in ADR-261.  Each governed memory type
carries a verification policy, a staleness policy, a staleness threshold in
seconds, and a recall score multiplier.  Unknown types receive a no-op default
so existing observations are never affected.

ADR reference: docs/adrs/ADR-261-memory-governance-v2.md
Pattern source: .private/external-pattern-research/annex-a-memory.md §Feature 1 (clean-room rewrite)

Public interface
----------------
    get_policy(type_name)               -> MemoryTypePolicy
    is_stale(age_seconds, type_name)    -> bool
    assess_freshness(age_seconds, type_name) -> FreshnessResult
    boosted_score(raw_score, type_name) -> float
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryTypePolicy:
    """Governance rule for a single memory type.

    Fields
    ------
    type_name           : canonical type string (e.g. "preference")
    verification        : verification tier at recall time
    staleness           : staleness policy tier
    stale_after_seconds : seconds after which the observation is considered stale;
                          None means staleness="never" and threshold is not applied
    recall_boost        : multiplier applied to the raw retrieval score; 1.0 = neutral
    """

    type_name: str
    verification: Literal["none", "corroborate", "verify_before_use"]
    staleness: Literal["never", "soft", "hard"]
    stale_after_seconds: int | None
    recall_boost: float


@dataclass(frozen=True)
class FreshnessResult:
    """Result of a freshness assessment for a single observation.

    Fields
    ------
    state : freshness state
        - "stable" : staleness="never" or below soft-threshold; no action needed
        - "fresh"  : age is below the staleness threshold (soft/hard policy)
        - "aging"  : age is approaching the threshold (>= 75% of threshold)
        - "stale"  : age >= stale_after_seconds for soft or hard policy
    note  : human-readable cue for the assistant surface; None when state=="stable"
            and verification=="none".  Always emitted for verify_before_use types.
    """

    state: Literal["stable", "fresh", "aging", "stale"]
    note: str | None


# ---------------------------------------------------------------------------
# Static policy table — six governed types (ADR-261 §Decision 1)
# ---------------------------------------------------------------------------

_POLICY_TABLE: dict[str, MemoryTypePolicy] = {
    "preference": MemoryTypePolicy(
        type_name="preference",
        verification="corroborate",
        staleness="soft",
        stale_after_seconds=7_776_000,   # 90 days
        recall_boost=1.4,
    ),
    "identity": MemoryTypePolicy(
        type_name="identity",
        verification="verify_before_use",
        staleness="soft",
        stale_after_seconds=15_552_000,  # 180 days
        recall_boost=1.2,
    ),
    "fact": MemoryTypePolicy(
        type_name="fact",
        verification="corroborate",
        staleness="hard",
        stale_after_seconds=2_592_000,   # 30 days
        recall_boost=1.0,
    ),
    "procedure": MemoryTypePolicy(
        type_name="procedure",
        verification="verify_before_use",
        staleness="soft",
        stale_after_seconds=5_184_000,   # 60 days
        recall_boost=1.6,
    ),
    "blocker": MemoryTypePolicy(
        type_name="blocker",
        verification="verify_before_use",
        staleness="hard",
        stale_after_seconds=864_000,     # 10 days
        recall_boost=1.8,
    ),
    "decision": MemoryTypePolicy(
        type_name="decision",
        verification="none",
        staleness="never",
        stale_after_seconds=None,
        recall_boost=1.1,
    ),
}

# Fraction of stale_after_seconds at which an observation is considered "aging"
_AGING_RATIO: float = 0.75

# No-op default for unknown types (ADR-261 §Decision 5)
_NO_OP_POLICY = MemoryTypePolicy(
    type_name="",         # filled at call time by get_policy()
    verification="none",
    staleness="never",
    stale_after_seconds=None,
    recall_boost=1.0,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_policy(type_name: str) -> MemoryTypePolicy:
    """Return the governance policy for *type_name*.

    Returns a no-op default (verification=none, staleness=never, boost=1.0)
    for any type not listed in the static rule table so that existing luum
    types (bugfix, discovery, architecture, config, …) are completely unaffected.

    Args:
        type_name: Engram observation type string.

    Returns:
        :class:`MemoryTypePolicy` for the type; no-op default for unknown types.
    """
    policy = _POLICY_TABLE.get(type_name)
    if policy is not None:
        return policy
    # Return a no-op default with the caller's type_name preserved for traceability
    return MemoryTypePolicy(
        type_name=type_name,
        verification="none",
        staleness="never",
        stale_after_seconds=None,
        recall_boost=1.0,
    )


def is_stale(observation_age_seconds: int | float, type_name: str) -> bool:
    """Return True if the observation exceeds the policy staleness threshold.

    Always returns False for:
    - Types with staleness="never" (e.g. "decision")
    - Unknown types (no-op default has staleness="never")
    - Types whose stale_after_seconds is None

    Args:
        observation_age_seconds: Age of the observation in seconds (>= 0).
        type_name:               Engram observation type string.

    Returns:
        True if the observation is stale; False otherwise.
    """
    policy = get_policy(type_name)
    if policy.staleness == "never" or policy.stale_after_seconds is None:
        return False
    return observation_age_seconds >= policy.stale_after_seconds


def assess_freshness(
    observation_age_seconds: int | float,
    type_name: str,
) -> FreshnessResult:
    """Return a :class:`FreshnessResult` describing the observation's freshness state.

    States (in priority order):
    - "stable" : staleness="never" (no note unless verify_before_use)
    - "stale"  : age >= threshold (soft or hard staleness)
    - "aging"  : age >= 75% of threshold
    - "fresh"  : age < 75% of threshold

    Notes:
    - verify_before_use types always emit a non-None note regardless of state.
    - corroborate types emit a note when stale or aging.
    - none types emit a note only when stale and staleness="soft" (warn, not suppress).

    Args:
        observation_age_seconds: Age of the observation in seconds (>= 0).
        type_name:               Engram observation type string.

    Returns:
        :class:`FreshnessResult` with state and optional human-readable note.
    """
    policy = get_policy(type_name)

    # --- staleness="never" branch ---
    if policy.staleness == "never" or policy.stale_after_seconds is None:
        note = None
        if policy.verification == "verify_before_use":
            note = f"verify before use: '{type_name}' memories require confirmation"
        return FreshnessResult(state="stable", note=note)

    threshold = policy.stale_after_seconds
    age = observation_age_seconds

    # --- determine state ---
    if age >= threshold:
        state: Literal["stable", "fresh", "aging", "stale"] = "stale"
    elif age >= threshold * _AGING_RATIO:
        state = "aging"
    else:
        state = "fresh"

    # --- build note ---
    note = _build_note(state, policy, type_name)

    return FreshnessResult(state=state, note=note)


def boosted_score(raw_score: float, type_name: str) -> float:
    """Apply the type's recall_boost multiplier to *raw_score*.

    Unknown types receive a 1.0 multiplier (no change).
    NOTE: This function is NOT idempotent for governed types — applying it
    twice multiplies the boost twice (e.g. 0.5 * 1.8 * 1.8 = 1.62).
    Callers must apply it exactly once per retrieval cycle.

    Args:
        raw_score: Base retrieval score (any non-negative float).
        type_name: Engram observation type string.

    Returns:
        raw_score * recall_boost for the type; raw_score unchanged for unknown types.
    """
    policy = get_policy(type_name)
    return raw_score * policy.recall_boost


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_note(
    state: Literal["stable", "fresh", "aging", "stale"],
    policy: MemoryTypePolicy,
    type_name: str,
) -> str | None:
    """Construct the human-readable cue for a FreshnessResult."""
    if policy.verification == "verify_before_use":
        if state == "stale":
            return (
                f"stale — verify before use: '{type_name}' exceeded its "
                f"{policy.stale_after_seconds}s threshold; reconfirm with user or live source"
            )
        if state == "aging":
            return (
                f"aging — verify before use: '{type_name}' is approaching its "
                f"staleness threshold; confirm before consequential use"
            )
        # fresh state still warrants the note for verify_before_use types
        return f"verify before use: '{type_name}' memories require confirmation before acting"

    if policy.verification == "corroborate":
        if state == "stale":
            return (
                f"stale — corroborate: '{type_name}' exceeded its "
                f"{policy.stale_after_seconds}s threshold; seek a second source for consequential actions"
            )
        if state == "aging":
            return (
                f"aging: '{type_name}' is approaching its staleness threshold; "
                "consider corroborating before use"
            )
        return None  # fresh + corroborate → no noise

    # verification="none"
    if state == "stale" and policy.staleness == "soft":
        return f"stale: '{type_name}' exceeded its {policy.stale_after_seconds}s threshold"
    return None
