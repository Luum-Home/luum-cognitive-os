# SCOPE: both
# scope: both
"""Engagement-weighted scoring engine for research results.

Adapted from the Sprut Agent Kit last30days scoring pattern.
Pure Python, no external dependencies. Python 3.9+ compatible.

Author: luum
"""

import math
import re
import string
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHTS = {
    "relevance": 0.45,
    "recency": 0.25,
    "engagement": 0.30,
}

# Engagement signal keys and their relative importance.
# Higher weight = more important signal.
_ENGAGEMENT_SIGNALS: Dict[str, float] = {
    "stars": 0.30,
    "forks": 0.15,
    "upvotes": 0.25,
    "comments": 0.15,
    "views": 0.15,
}

# Logarithmic scaling thresholds for engagement signals.
# Values at or above this threshold score 1.0 for that signal.
_ENGAGEMENT_CAPS: Dict[str, int] = {
    "stars": 10000,
    "forks": 2000,
    "upvotes": 500,
    "comments": 200,
    "views": 100000,
}

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, normalize whitespace for comparison."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> Set[str]:
    """Split normalized text into a set of unique tokens."""
    return set(normalize_text(text).split())


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------


def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard similarity between two sets. Returns 0.0 if both empty."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------


def calculate_relevance(result: Dict, query: str) -> float:
    """Keyword overlap between result content and query.

    Uses Jaccard similarity on word sets extracted from:
    - result["title"] (weight 0.6)
    - result["content"] or result["snippet"] (weight 0.4)
    compared against the query.

    Returns a float in [0.0, 1.0].
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    title = result.get("title", "")
    content = result.get("content", result.get("snippet", ""))

    title_tokens = _tokenize(title)
    content_tokens = _tokenize(content)

    title_sim = _jaccard(query_tokens, title_tokens)
    content_sim = _jaccard(query_tokens, content_tokens)

    return min(1.0, title_sim * 0.6 + content_sim * 0.4)


def calculate_recency(
    result: Dict, now: Optional[datetime] = None
) -> float:
    """Score based on how recent the result is.

    Expects ``result["date"]`` or ``result["published"]`` as an ISO-8601
    string (``YYYY-MM-DD`` or full datetime).

    Returns:
        1.0  if published today
        0.0  if published >= 365 days ago (or date missing/unparseable)

    The decay is linear over 365 days.
    """
    date_str = result.get("date", result.get("published", ""))
    if not date_str:
        return 0.0

    if now is None:
        now = datetime.now(timezone.utc)

    try:
        parsed = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0

    days_ago = (now - parsed).total_seconds() / 86400.0
    if days_ago < 0:
        # Future dates treated as today.
        return 1.0
    if days_ago >= 365:
        return 0.0
    return max(0.0, 1.0 - days_ago / 365.0)


def calculate_engagement(result: Dict) -> float:
    """Score based on engagement signals (stars, forks, upvotes, comments, views).

    Each signal is log-scaled against its cap, then weighted.
    Missing signals contribute 0.

    Returns a float in [0.0, 1.0].
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for signal, weight in _ENGAGEMENT_SIGNALS.items():
        raw = result.get(signal, 0)
        try:
            raw = int(raw)
        except (TypeError, ValueError):
            raw = 0

        if raw <= 0:
            # Signal absent — skip entirely so it doesn't drag down score
            # when the result simply doesn't have that metric.
            continue

        cap = _ENGAGEMENT_CAPS.get(signal, 1000)
        # log1p scales smoothly: log1p(0)=0, log1p(cap)=max
        score = min(1.0, math.log1p(raw) / math.log1p(cap))

        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0.0:
        return 0.0
    return min(1.0, weighted_sum / total_weight)


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------


def score_result(
    result: Dict, query: str, now: Optional[datetime] = None
) -> float:
    """Score a research result (0.0-1.0) based on weighted relevance + recency + engagement."""
    relevance = calculate_relevance(result, query)
    recency = calculate_recency(result, now=now)
    engagement = calculate_engagement(result)

    return min(
        1.0,
        relevance * WEIGHTS["relevance"]
        + recency * WEIGHTS["recency"]
        + engagement * WEIGHTS["engagement"],
    )


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate_results(
    results: List[Dict], threshold: float = 0.7
) -> List[Dict]:
    """Remove duplicate results using Jaccard similarity on titles + content snippets.

    Two results are considered duplicates when the Jaccard similarity of their
    combined title + content token sets meets or exceeds *threshold*.

    The first occurrence in list order is kept; later duplicates are dropped.
    """
    if not results:
        return []

    kept: List[Dict] = []
    kept_token_sets: List[Set[str]] = []

    for result in results:
        title = result.get("title", "")
        content = result.get("content", result.get("snippet", ""))
        tokens = _tokenize(f"{title} {content}")

        is_dup = False
        for existing_tokens in kept_token_sets:
            if _jaccard(tokens, existing_tokens) >= threshold:
                is_dup = True
                break

        if not is_dup:
            kept.append(result)
            kept_token_sets.append(tokens)

    return kept


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_results(
    results: List[Dict], query: str, now: Optional[datetime] = None
) -> List[Dict]:
    """Score, deduplicate, and sort results by weighted score descending.

    Each result dict gets a ``_score`` key added with the computed score.
    """
    if not results:
        return []

    deduped = deduplicate_results(results)

    for r in deduped:
        r["_score"] = score_result(r, query, now=now)

    deduped.sort(key=lambda r: r["_score"], reverse=True)
    return deduped
