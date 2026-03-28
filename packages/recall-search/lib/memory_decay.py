"""Memory decay for Engram observations.

Calculates time-based relevance scores so older memories naturally
lose priority in search results. Different memory types decay at
different rates — architecture decisions stay relevant much longer
than bugfix notes.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Decay rates per memory type (fraction of relevance lost per day).
# Lower rate = slower decay = stays relevant longer.
DECAY_RATES: Dict[str, float] = {
    "bugfix": 0.02,        # Bugs found lose relevance faster
    "decision": 0.005,     # Decisions stay relevant longest
    "architecture": 0.003,  # Architecture decisions are very stable
    "discovery": 0.01,     # Discoveries decay moderately
    "pattern": 0.005,      # Patterns are stable
    "config": 0.015,       # Config changes decay moderately fast
    "preference": 0.001,   # User preferences barely decay
}

DEFAULT_DECAY_RATE: float = 0.01  # 1% per day for unknown types


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string to a timezone-aware datetime.

    Handles both offset-aware (``2026-01-15T10:00:00+00:00``) and
    offset-naive (``2026-01-15T10:00:00``) formats.  Naive timestamps
    are assumed to be UTC.
    """
    # Try standard fromisoformat first (Python 3.11+ handles 'Z')
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # Fallback: strip microseconds / extra chars and retry
        cleaned = ts.rstrip("Z").split(".")[0]
        dt = datetime.fromisoformat(cleaned)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _get_age_days(observation: Dict, now: Optional[datetime] = None) -> float:
    """Return the age of *observation* in fractional days.

    Looks for ``timestamp`` (ISO string) or ``timestamp_epoch`` (unix
    seconds) in the observation dict.  Returns 0.0 when neither is
    present or the observation is in the future relative to *now*.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    ts_str = observation.get("timestamp")
    ts_epoch = observation.get("timestamp_epoch")

    if ts_str:
        created = _parse_timestamp(ts_str)
    elif ts_epoch is not None:
        created = datetime.fromtimestamp(float(ts_epoch), tz=timezone.utc)
    else:
        return 0.0

    delta = (now - created).total_seconds()
    if delta < 0:
        return 0.0
    return delta / 86400.0  # seconds -> days


def calculate_relevance(
    observation: Dict,
    now: Optional[datetime] = None,
) -> float:
    """Calculate current relevance score (0.0 -- 1.0) for *observation*.

    Uses exponential decay: ``relevance = e^(-rate * age_days)``.
    """
    obs_type = observation.get("type", "")
    rate = DECAY_RATES.get(obs_type, DEFAULT_DECAY_RATE)
    age = _get_age_days(observation, now)
    relevance = math.exp(-rate * age)
    return max(0.0, min(1.0, relevance))


def apply_decay_to_search_results(
    results: List[Dict],
    now: Optional[datetime] = None,
) -> List[Dict]:
    """Re-rank *results* by ``relevance * decay``.

    Each dict in *results* is augmented with a ``decay_score`` key and
    the list is returned sorted descending by that score.  The original
    list is **not** mutated.
    """
    scored: List[Dict] = []
    for r in results:
        copy = dict(r)
        copy["decay_score"] = calculate_relevance(r, now)
        scored.append(copy)
    scored.sort(key=lambda x: x["decay_score"], reverse=True)
    return scored


def should_prune(
    observation: Dict,
    threshold: float = 0.1,
    now: Optional[datetime] = None,
) -> bool:
    """Return ``True`` if *observation* has decayed below *threshold*."""
    return calculate_relevance(observation, now) < threshold


def get_decay_stats(observations: List[Dict]) -> Dict:
    """Return aggregate decay statistics for a list of observations.

    Returns a dict with keys:
    - ``total``: number of observations
    - ``active``: relevance > 0.5
    - ``fading``: 0.1 <= relevance <= 0.5
    - ``stale``: relevance < 0.1
    """
    total = len(observations)
    active = 0
    fading = 0
    stale = 0
    for obs in observations:
        score = calculate_relevance(obs)
        if score > 0.5:
            active += 1
        elif score >= 0.1:
            fading += 1
        else:
            stale += 1
    return {
        "total": total,
        "active": active,
        "fading": fading,
        "stale": stale,
    }
