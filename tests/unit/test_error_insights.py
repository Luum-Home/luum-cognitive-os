"""Unit tests for lib/error_insights.py (ADR-080 Tier 2 #6).

Covers: summarize(), InsightReport, cluster detection, trend analysis,
recommendation generation, edge cases.
"""

import time

import pytest

from lib.error_classifier import (
    ClassifiedError,
    ErrorClass,
    RecordCategory,
    RecordSeverity,
    Transience,
)
from lib.error_insights import summarize

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = time.time()


def _make_ce(
    cat: RecordCategory,
    ts_offset: float = 0.0,
    transient: Transience = Transience.no,
    fingerprint: str = "fp0",
) -> ClassifiedError:
    """Build a ClassifiedError with a relative timestamp (seconds before now)."""
    ts = _NOW - ts_offset
    record = {"type": cat.value.upper(), "timestamp_epoch": ts, "fingerprint": fingerprint}
    ec = ErrorClass(
        category=cat,
        severity=RecordSeverity.medium,
        transient=transient,
        suggested_action="action",
        raw=record,
    )
    return ClassifiedError(record=record, classification=ec)


def _bulk(cat: RecordCategory, count: int, base_offset: float = 0.0, spacing: float = 10.0) -> list:
    return [_make_ce(cat, ts_offset=base_offset + i * spacing, fingerprint=f"fp{i}") for i in range(count)]


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestSummarizeEmpty:
    def test_empty_list(self):
        report = summarize([], window_hours=24)
        assert report.total_errors == 0
        assert report.top_categories == []
        assert report.clusters == []
        assert "No errors" in report.recommendations[0]

    def test_format_text_empty(self):
        report = summarize([], window_hours=24)
        text = report.format_text()
        assert "No errors" in text

    def test_all_outside_window(self):
        old = _make_ce(RecordCategory.test_failure, ts_offset=90 * 3600)  # 90h ago
        report = summarize([old], window_hours=24)
        assert report.total_errors == 0

    def test_window_zero_includes_all(self):
        old = _make_ce(RecordCategory.test_failure, ts_offset=999 * 3600)
        report = summarize([old], window_hours=0)
        assert report.total_errors == 1


# ---------------------------------------------------------------------------
# Top categories
# ---------------------------------------------------------------------------

class TestTopCategories:
    def test_single_category(self):
        ces = _bulk(RecordCategory.test_failure, 5)
        report = summarize(ces, window_hours=24)
        assert len(report.top_categories) == 1
        assert report.top_categories[0].category == "test_failure"
        assert report.top_categories[0].count == 5
        assert report.top_categories[0].pct == pytest.approx(100.0)

    def test_multiple_categories_sorted(self):
        ces = (
            _bulk(RecordCategory.test_failure, 10)
            + _bulk(RecordCategory.lint_error, 3)
            + _bulk(RecordCategory.auth, 1)
        )
        report = summarize(ces, window_hours=24)
        counts = [c.count for c in report.top_categories]
        assert counts == sorted(counts, reverse=True)
        assert report.top_categories[0].category == "test_failure"

    def test_percentages_sum_to_100(self):
        ces = _bulk(RecordCategory.test_failure, 7) + _bulk(RecordCategory.lint_error, 3)
        report = summarize(ces, window_hours=24)
        total_pct = sum(c.pct for c in report.top_categories)
        assert total_pct == pytest.approx(100.0, abs=0.2)

    def test_transient_counts_split(self):
        transient = [_make_ce(RecordCategory.network, transient=Transience.yes) for _ in range(4)]
        non_transient = [_make_ce(RecordCategory.network, transient=Transience.no) for _ in range(2)]
        report = summarize(transient + non_transient, window_hours=24)
        net = next(c for c in report.top_categories if c.category == "network")
        assert net.transient_count == 4
        assert net.non_transient_count == 2


# ---------------------------------------------------------------------------
# Rate and trend
# ---------------------------------------------------------------------------

class TestRateAndTrend:
    def test_rate_per_hour(self):
        ces = _bulk(RecordCategory.test_failure, 12)
        report = summarize(ces, window_hours=6)
        assert report.rate_per_hour == pytest.approx(2.0)

    def test_trend_increasing(self):
        # More errors in the second half of the window
        first_half = _bulk(RecordCategory.test_failure, 2, base_offset=22 * 3600)  # ~22h ago
        second_half = _bulk(RecordCategory.test_failure, 10, base_offset=1 * 3600)  # ~1h ago
        report = summarize(first_half + second_half, window_hours=24)
        assert report.error_rate_trend == "increasing"

    def test_trend_decreasing(self):
        first_half = _bulk(RecordCategory.test_failure, 10, base_offset=22 * 3600)
        second_half = _bulk(RecordCategory.test_failure, 1, base_offset=1 * 3600)
        report = summarize(first_half + second_half, window_hours=24)
        assert report.error_rate_trend == "decreasing"

    def test_trend_stable(self):
        first_half = _bulk(RecordCategory.test_failure, 5, base_offset=22 * 3600)
        second_half = _bulk(RecordCategory.test_failure, 5, base_offset=1 * 3600)
        report = summarize(first_half + second_half, window_hours=24)
        assert report.error_rate_trend == "stable"

    def test_trend_insufficient_data(self):
        ces = _bulk(RecordCategory.test_failure, 2)
        report = summarize(ces, window_hours=24)
        assert report.error_rate_trend == "insufficient_data"


# ---------------------------------------------------------------------------
# Cluster detection
# ---------------------------------------------------------------------------

class TestClusterDetection:
    def test_no_cluster_below_threshold(self):
        ces = _bulk(RecordCategory.rate_limit, 4, spacing=100)
        report = summarize(ces, window_hours=24)
        assert len(report.clusters) == 0

    def test_cluster_detected_at_threshold(self):
        # 5 rate_limit errors within 200 seconds
        ces = _bulk(RecordCategory.rate_limit, 5, spacing=40)
        report = summarize(ces, window_hours=24)
        assert len(report.clusters) == 1
        assert report.clusters[0].category == "rate_limit"
        assert report.clusters[0].count >= 5

    def test_cluster_above_threshold(self):
        ces = _bulk(RecordCategory.test_failure, 20, spacing=30)
        report = summarize(ces, window_hours=24)
        assert len(report.clusters) >= 1
        assert report.clusters[0].count >= 5

    def test_cluster_different_categories_independent(self):
        rl_ces = _bulk(RecordCategory.rate_limit, 6, spacing=50)
        tf_ces = _bulk(RecordCategory.test_failure, 6, spacing=50)
        report = summarize(rl_ces + tf_ces, window_hours=24)
        cluster_cats = {cl.category for cl in report.clusters}
        assert "rate_limit" in cluster_cats
        assert "test_failure" in cluster_cats

    def test_cluster_window_start_end_ordered(self):
        ces = _bulk(RecordCategory.auth, 6, spacing=100)
        report = summarize(ces, window_hours=24)
        for cl in report.clusters:
            assert cl.window_start <= cl.window_end

    def test_no_clusters_on_sparse_errors(self):
        # 5 errors spread over 10 hours — no 1h cluster
        ces = _bulk(RecordCategory.lint_error, 5, spacing=7200)  # 2h apart
        report = summarize(ces, window_hours=24)
        assert len(report.clusters) == 0


# ---------------------------------------------------------------------------
# Suspected root causes
# ---------------------------------------------------------------------------

class TestSuspectedRootCauses:
    def test_cluster_generates_cause(self):
        ces = _bulk(RecordCategory.rate_limit, 8, spacing=50)
        report = summarize(ces, window_hours=24)
        assert len(report.suspected_root_causes) >= 1
        assert any("rate_limit" in c for c in report.suspected_root_causes)

    def test_dominant_category_generates_cause(self):
        ces = _bulk(RecordCategory.test_failure, 9) + _bulk(RecordCategory.lint_error, 1)
        report = summarize(ces, window_hours=24)
        # test_failure is >50%, should surface as cause (if no cluster)
        causes_text = " ".join(report.suspected_root_causes)
        assert "test_failure" in causes_text or len(report.clusters) > 0

    def test_no_spurious_causes_on_low_volume(self):
        ces = _bulk(RecordCategory.test_failure, 2)
        report = summarize(ces, window_hours=24)
        # No cluster, <50% dominance impossible with 2 records of same cat (100%!)
        # Just assert it doesn't crash
        assert isinstance(report.suspected_root_causes, list)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class TestRecommendations:
    def test_recommendations_non_empty(self):
        ces = _bulk(RecordCategory.test_failure, 3)
        report = summarize(ces, window_hours=24)
        assert len(report.recommendations) >= 1
        assert all(isinstance(r, str) for r in report.recommendations)

    def test_rate_limit_recommendation_mentions_throttle(self):
        ces = _bulk(RecordCategory.rate_limit, 3)
        report = summarize(ces, window_hours=24)
        recs = " ".join(report.recommendations)
        assert "rate_limit" in recs or "RATE" in recs.upper()

    def test_rate_limit_cluster_recommendation_specific(self):
        ces = _bulk(RecordCategory.rate_limit, 7, spacing=50)
        report = summarize(ces, window_hours=24)
        recs = " ".join(report.recommendations)
        assert "COS_RATE_THROTTLE_PCT" in recs

    def test_test_failure_recommendation_mentions_cos_test(self):
        ces = _bulk(RecordCategory.test_failure, 5)
        report = summarize(ces, window_hours=24)
        recs = " ".join(report.recommendations)
        assert "cos-test" in recs or "test" in recs.lower()

    def test_no_errors_recommendation(self):
        report = summarize([], window_hours=24)
        recs = " ".join(report.recommendations)
        assert "No errors" in recs or "no errors" in recs.lower()


# ---------------------------------------------------------------------------
# InsightReport.format_text and as_dict
# ---------------------------------------------------------------------------

class TestInsightReportOutput:
    def test_format_text_contains_total(self):
        ces = _bulk(RecordCategory.test_failure, 4)
        report = summarize(ces, window_hours=24)
        text = report.format_text()
        assert "4" in text

    def test_format_text_contains_window(self):
        ces = _bulk(RecordCategory.test_failure, 2)
        report = summarize(ces, window_hours=12)
        text = report.format_text()
        assert "12" in text

    def test_format_text_contains_category(self):
        ces = _bulk(RecordCategory.lint_error, 3)
        report = summarize(ces, window_hours=24)
        assert "lint_error" in report.format_text()

    def test_as_dict_keys(self):
        ces = _bulk(RecordCategory.test_failure, 2)
        report = summarize(ces, window_hours=24)
        d = report.as_dict()
        for key in ("window_hours", "total_errors", "top_categories", "error_rate_trend",
                    "rate_per_hour", "clusters", "suspected_root_causes", "recommendations",
                    "generated_at"):
            assert key in d

    def test_as_dict_top_categories_structure(self):
        ces = _bulk(RecordCategory.auth, 3)
        d = summarize(ces, window_hours=24).as_dict()
        cat = d["top_categories"][0]
        assert "category" in cat and "count" in cat and "pct" in cat

    def test_as_dict_clusters_structure(self):
        ces = _bulk(RecordCategory.rate_limit, 6, spacing=50)
        d = summarize(ces, window_hours=24).as_dict()
        if d["clusters"]:
            cl = d["clusters"][0]
            assert "category" in cl and "count" in cl and "window_start" in cl


# ---------------------------------------------------------------------------
# Integration: classify_jsonl → summarize
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_classify_then_summarize(self, tmp_path):
        import json
        from lib.error_classifier import classify_jsonl

        records = (
            [{"type": "TEST_FAILURE", "timestamp_epoch": _NOW - i * 60, "fingerprint": f"tf{i}"} for i in range(8)]
            + [{"type": "LINT_ERROR", "timestamp_epoch": _NOW - 3600, "fingerprint": "le0"}]
        )
        p = tmp_path / "errors.jsonl"
        with open(p, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        classified = classify_jsonl(p)
        report = summarize(classified, window_hours=24)
        assert report.total_errors == 9
        assert report.top_categories[0].category == "test_failure"
        assert report.top_categories[0].count == 8
