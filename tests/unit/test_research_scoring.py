"""Unit tests for lib/research_scoring.py.

Tests cover all public functions: scoring, relevance, recency, engagement,
deduplication, ranking, and text normalization.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest

from lib.research_scoring import (
    calculate_engagement,
    calculate_recency,
    calculate_relevance,
    deduplicate_results,
    normalize_text,
    rank_results,
    score_result,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    title: str = "",
    content: str = "",
    date: str = "",
    stars: int = 0,
    forks: int = 0,
    upvotes: int = 0,
    comments: int = 0,
    views: int = 0,
) -> Dict:
    """Build a result dict with optional engagement signals."""
    result: Dict = {"title": title, "content": content}
    if date:
        result["date"] = date
    if stars:
        result["stars"] = stars
    if forks:
        result["forks"] = forks
    if upvotes:
        result["upvotes"] = upvotes
    if comments:
        result["comments"] = comments
    if views:
        result["views"] = views
    return result


# ---------------------------------------------------------------------------
# score_result
# ---------------------------------------------------------------------------


class TestScoreResult:
    def test_returns_float_0_to_1(self) -> None:
        result = _make_result(
            title="Python tutorial",
            content="Learn Python basics",
            date=datetime.now(timezone.utc).isoformat(),
            stars=100,
        )
        score = score_result(result, "Python tutorial")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_higher_score_for_more_relevant(self) -> None:
        relevant = _make_result(title="Python web scraping guide")
        irrelevant = _make_result(title="Cooking Italian pasta")
        s1 = score_result(relevant, "Python web scraping")
        s2 = score_result(irrelevant, "Python web scraping")
        assert s1 > s2


# ---------------------------------------------------------------------------
# calculate_relevance
# ---------------------------------------------------------------------------


class TestCalculateRelevance:
    def test_identical_query(self) -> None:
        result = _make_result(title="machine learning tutorial")
        score = calculate_relevance(result, "machine learning tutorial")
        assert score > 0.3  # high overlap expected

    def test_no_overlap(self) -> None:
        result = _make_result(title="underwater basket weaving")
        score = calculate_relevance(result, "quantum physics equations")
        assert score < 0.1  # near zero

    def test_empty_query(self) -> None:
        result = _make_result(title="something")
        score = calculate_relevance(result, "")
        assert score == 0.0

    def test_content_contributes(self) -> None:
        result = _make_result(
            title="unrelated title",
            content="Python web framework comparison",
        )
        score = calculate_relevance(result, "Python web framework")
        assert score > 0.0


# ---------------------------------------------------------------------------
# calculate_recency
# ---------------------------------------------------------------------------


class TestCalculateRecency:
    def test_today(self) -> None:
        now = datetime.now(timezone.utc)
        result = _make_result(date=now.isoformat())
        score = calculate_recency(result, now=now)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_one_year_ago(self) -> None:
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=365)
        result = _make_result(date=old.isoformat())
        score = calculate_recency(result, now=now)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_six_months_ago(self) -> None:
        now = datetime.now(timezone.utc)
        mid = now - timedelta(days=182)
        result = _make_result(date=mid.isoformat())
        score = calculate_recency(result, now=now)
        assert 0.4 < score < 0.6

    def test_missing_date(self) -> None:
        result = _make_result(title="no date")
        score = calculate_recency(result)
        assert score == 0.0

    def test_invalid_date(self) -> None:
        result = _make_result(date="not-a-date")
        score = calculate_recency(result)
        assert score == 0.0

    def test_future_date(self) -> None:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=10)
        result = _make_result(date=future.isoformat())
        score = calculate_recency(result, now=now)
        assert score == 1.0


# ---------------------------------------------------------------------------
# calculate_engagement
# ---------------------------------------------------------------------------


class TestCalculateEngagement:
    def test_high_stars(self) -> None:
        result = _make_result(stars=5000)
        score = calculate_engagement(result)
        assert score > 0.7

    def test_no_signals(self) -> None:
        result = _make_result(title="nothing")
        score = calculate_engagement(result)
        assert score == 0.0

    def test_mixed_signals(self) -> None:
        result = _make_result(stars=100, forks=20, comments=10)
        score = calculate_engagement(result)
        assert 0.0 < score < 1.0

    def test_max_all_signals(self) -> None:
        result = _make_result(
            stars=10000,
            forks=2000,
            upvotes=500,
            comments=200,
            views=100000,
        )
        score = calculate_engagement(result)
        assert score == pytest.approx(1.0, abs=0.05)


# ---------------------------------------------------------------------------
# deduplicate_results
# ---------------------------------------------------------------------------


class TestDeduplicateResults:
    def test_identical_titles(self) -> None:
        r1 = _make_result(title="Python tutorial for beginners")
        r2 = _make_result(title="Python tutorial for beginners")
        deduped = deduplicate_results([r1, r2])
        assert len(deduped) == 1

    def test_different_titles_kept(self) -> None:
        r1 = _make_result(title="Python web scraping")
        r2 = _make_result(title="Java enterprise architecture")
        deduped = deduplicate_results([r1, r2])
        assert len(deduped) == 2

    def test_empty_list(self) -> None:
        assert deduplicate_results([]) == []

    def test_preserves_order(self) -> None:
        r1 = _make_result(title="first unique item")
        r2 = _make_result(title="second unique item")
        r3 = _make_result(title="third unique item")
        deduped = deduplicate_results([r1, r2, r3])
        assert len(deduped) == 3
        assert deduped[0]["title"] == "first unique item"


# ---------------------------------------------------------------------------
# rank_results
# ---------------------------------------------------------------------------


class TestRankResults:
    def test_sorted_descending(self) -> None:
        now = datetime.now(timezone.utc)
        r1 = _make_result(
            title="exact query match",
            date=now.isoformat(),
            stars=1000,
        )
        r2 = _make_result(
            title="unrelated topic",
            date=(now - timedelta(days=300)).isoformat(),
        )
        ranked = rank_results([r2, r1], "exact query match", now=now)
        assert len(ranked) >= 1
        # First result should have a higher score
        assert ranked[0]["_score"] >= ranked[-1]["_score"]

    def test_adds_score_key(self) -> None:
        r = _make_result(title="test")
        ranked = rank_results([r], "test")
        assert "_score" in ranked[0]
        assert isinstance(ranked[0]["_score"], float)

    def test_empty_results(self) -> None:
        assert rank_results([], "query") == []


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------


class TestNormalizeText:
    def test_strips_punctuation(self) -> None:
        assert normalize_text("Hello, World!") == "hello world"

    def test_lowercases(self) -> None:
        assert normalize_text("UPPER CASE") == "upper case"

    def test_normalizes_whitespace(self) -> None:
        assert normalize_text("  multiple   spaces  ") == "multiple spaces"

    def test_empty_string(self) -> None:
        assert normalize_text("") == ""
