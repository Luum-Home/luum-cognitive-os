# SCOPE: os-only
"""Error insights aggregation for Cognitive OS (ADR-080 Tier 2 #6).

Aggregates classified error records from error-learning.jsonl into actionable
insight reports: top categories, rolling error rate, cluster detection, and
recommendations.

Adapted from Hermes agent/insights.py (MIT) — aggregation and trend patterns.
Original Hermes InsightsEngine targets SQLite session data; this module targets
the flat error-learning.jsonl log directly, so the implementation is a clean
re-adaptation rather than a verbatim port.

License note: Hermes is MIT-licensed. See .cognitive-os/adoption-registry.yaml.

Usage:
    from lib.error_classifier import classify_jsonl, default_errors_path
    from lib.error_insights import summarize

    classified = classify_jsonl(default_errors_path())
    report = summarize(classified, window_hours=24)
    print(report.format_text())
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List

from lib.error_classifier import ClassifiedError, RecordCategory, Transience


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class CategorySummary:
    category: str
    count: int
    pct: float
    transient_count: int
    non_transient_count: int


@dataclass
class ClusterAlert:
    """5+ errors of the same category within 1 hour."""
    category: str
    count: int
    window_start: float  # epoch
    window_end: float    # epoch
    sample_fingerprints: List[str] = field(default_factory=list)


@dataclass
class InsightReport:
    """Aggregated error insights over a time window."""

    window_hours: int
    total_errors: int
    top_categories: List[CategorySummary]
    error_rate_trend: str          # "increasing" | "stable" | "decreasing" | "insufficient_data"
    rate_per_hour: float
    clusters: List[ClusterAlert]
    suspected_root_causes: List[str]
    recommendations: List[str]
    generated_at: float = field(default_factory=time.time)

    def format_text(self) -> str:
        """Return a human-readable text representation."""
        lines: List[str] = []
        ts = datetime.fromtimestamp(self.generated_at, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"Error Insights Report — last {self.window_hours}h (generated {ts})")
        lines.append("=" * 60)

        if self.total_errors == 0:
            lines.append("  No errors recorded in this window.")
            return "\n".join(lines)

        lines.append(f"  Total errors:  {self.total_errors}")
        lines.append(f"  Rate:          {self.rate_per_hour:.2f} errors/hour")
        lines.append(f"  Trend:         {self.error_rate_trend}")
        lines.append("")

        if self.top_categories:
            lines.append("Top Categories:")
            lines.append(f"  {'Category':<22} {'Count':>6} {'%':>6}  Transient")
            for c in self.top_categories:
                t_label = f"{c.transient_count}Y / {c.non_transient_count}N"
                lines.append(
                    f"  {c.category:<22} {c.count:>6} {c.pct:>5.1f}%  {t_label}"
                )
            lines.append("")

        if self.clusters:
            lines.append("Clusters (5+ errors within 1h):")
            for cl in self.clusters:
                start = datetime.fromtimestamp(cl.window_start, tz=timezone.utc).strftime("%H:%M")
                end   = datetime.fromtimestamp(cl.window_end,   tz=timezone.utc).strftime("%H:%M")
                lines.append(f"  [{cl.category}] {cl.count} errors between {start}–{end} UTC")
            lines.append("")

        if self.suspected_root_causes:
            lines.append("Suspected Root Causes:")
            for cause in self.suspected_root_causes:
                lines.append(f"  - {cause}")
            lines.append("")

        if self.recommendations:
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  * {rec}")
            lines.append("")

        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "window_hours": self.window_hours,
            "total_errors": self.total_errors,
            "rate_per_hour": self.rate_per_hour,
            "error_rate_trend": self.error_rate_trend,
            "top_categories": [
                {
                    "category": c.category,
                    "count": c.count,
                    "pct": c.pct,
                    "transient_count": c.transient_count,
                    "non_transient_count": c.non_transient_count,
                }
                for c in self.top_categories
            ],
            "clusters": [
                {
                    "category": cl.category,
                    "count": cl.count,
                    "window_start": cl.window_start,
                    "window_end": cl.window_end,
                    "sample_fingerprints": cl.sample_fingerprints,
                }
                for cl in self.clusters
            ],
            "suspected_root_causes": self.suspected_root_causes,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
        }


# ── Core aggregation ─────────────────────────────────────────────────────────

def _filter_window(
    classified: List[ClassifiedError],
    window_hours: int,
) -> List[ClassifiedError]:
    """Return only records within the last *window_hours* hours."""
    if window_hours <= 0:
        return list(classified)
    cutoff = time.time() - window_hours * 3600
    result = []
    for ce in classified:
        ts = ce.timestamp_epoch
        if ts is None or ts >= cutoff:
            result.append(ce)
    return result


def _top_categories(
    filtered: List[ClassifiedError],
    total: int,
) -> List[CategorySummary]:
    counts: Counter = Counter()
    transient_counts: Counter = Counter()
    non_transient_counts: Counter = Counter()

    for ce in filtered:
        cat = ce.category.value
        counts[cat] += 1
        t = ce.classification.transient
        if t is Transience.yes:
            transient_counts[cat] += 1
        elif t is Transience.no:
            non_transient_counts[cat] += 1

    summaries = []
    for cat, count in counts.most_common():
        summaries.append(CategorySummary(
            category=cat,
            count=count,
            pct=round(count / total * 100, 1) if total else 0.0,
            transient_count=transient_counts.get(cat, 0),
            non_transient_count=non_transient_counts.get(cat, 0),
        ))
    return summaries


def _detect_clusters(
    filtered: List[ClassifiedError],
    threshold: int = 5,
    cluster_window_secs: int = 3600,
) -> List[ClusterAlert]:
    """Detect categories with >= threshold errors within cluster_window_secs."""
    by_category: Dict[str, List[float]] = defaultdict(list)
    fingerprints: Dict[str, List[str]] = defaultdict(list)

    for ce in filtered:
        ts = ce.timestamp_epoch
        if ts is None:
            continue
        cat = ce.category.value
        by_category[cat].append(ts)
        fp = ce.fingerprint
        if fp:
            fingerprints[cat].append(fp)

    alerts: List[ClusterAlert] = []
    for cat, timestamps in by_category.items():
        if len(timestamps) < threshold:
            continue
        timestamps_sorted = sorted(timestamps)
        # Sliding window: find any window of cluster_window_secs with >= threshold entries
        i = 0
        while i < len(timestamps_sorted):
            window_start = timestamps_sorted[i]
            window_end = window_start + cluster_window_secs
            in_window = [t for t in timestamps_sorted[i:] if t <= window_end]
            if len(in_window) >= threshold:
                fps = list(dict.fromkeys(fingerprints.get(cat, [])))[:3]
                alerts.append(ClusterAlert(
                    category=cat,
                    count=len(in_window),
                    window_start=window_start,
                    window_end=in_window[-1],
                    sample_fingerprints=fps,
                ))
                # Skip past this window to avoid overlapping alerts for same category
                i += len(in_window)
            else:
                i += 1

    alerts.sort(key=lambda a: a.count, reverse=True)
    return alerts


def _error_rate_trend(
    classified: List[ClassifiedError],
    window_hours: int,
) -> str:
    """Compare first-half vs second-half of the window to determine trend."""
    if len(classified) < 4:
        return "insufficient_data"
    now = time.time()
    half = window_hours * 3600 / 2
    first_half_cutoff = now - window_hours * 3600
    mid_cutoff = now - half

    first_count = sum(
        1 for ce in classified
        if ce.timestamp_epoch is not None
        and first_half_cutoff <= ce.timestamp_epoch < mid_cutoff
    )
    second_count = sum(
        1 for ce in classified
        if ce.timestamp_epoch is not None
        and ce.timestamp_epoch >= mid_cutoff
    )

    if first_count == 0 and second_count == 0:
        return "insufficient_data"
    if first_count == 0:
        return "increasing"
    ratio = second_count / first_count
    if ratio > 1.25:
        return "increasing"
    if ratio < 0.75:
        return "decreasing"
    return "stable"


def _build_suspected_root_causes(
    clusters: List[ClusterAlert],
    top_categories: List[CategorySummary],
) -> List[str]:
    causes: List[str] = []
    for cl in clusters:
        start = datetime.fromtimestamp(cl.window_start, tz=timezone.utc).strftime("%H:%M UTC")
        causes.append(
            f"{cl.count} {cl.category} errors clustered around {start} — "
            "likely a systemic failure, not isolated incidents"
        )
    # Dominant category (>50%) without cluster
    cluster_cats = {cl.category for cl in clusters}
    for cs in top_categories[:2]:
        if cs.category not in cluster_cats and cs.pct > 50:
            causes.append(
                f"{cs.category} is {cs.pct:.0f}% of all errors — "
                "check for a persistent root cause"
            )
    return causes


def _build_recommendations(
    top_categories: List[CategorySummary],
    clusters: List[ClusterAlert],
    rate_per_hour: float,
    trend: str,
) -> List[str]:
    recs: List[str] = []
    cluster_cats = {cl.category for cl in clusters}

    for cs in top_categories[:5]:
        cat = cs.category
        if cat == RecordCategory.rate_limit.value:
            if cat in cluster_cats:
                recs.append(
                    "rate_limit cluster detected — consider lowering COS_RATE_THROTTLE_PCT "
                    "or adding provider-level backoff"
                )
            else:
                recs.append("rate_limit errors present — review COS_RATE_THROTTLE_PCT setting")
        elif cat == RecordCategory.test_failure.value:
            recs.append(
                f"{cs.count} test failure(s) — run `cos-test focused` to isolate "
                "failing scenarios before next sdd-apply"
            )
        elif cat == RecordCategory.auth.value:
            recs.append(
                "auth errors present — verify API keys and rotate if expired"
            )
        elif cat == RecordCategory.network.value:
            recs.append(
                "network errors present — check provider availability and retry config"
            )
        elif cat == RecordCategory.build_error.value:
            recs.append(
                "build errors present — resolve compilation issues; check Go/Python lint lanes"
            )
        elif cat == RecordCategory.lint_error.value:
            recs.append(
                "lint errors present — run `python3 -m pytest tests/audit/ -q` to surface naming violations"
            )

    if trend == "increasing" and rate_per_hour > 2:
        recs.append(
            f"Error rate is increasing ({rate_per_hour:.1f}/h) — "
            "consider pausing sdd-apply until root cause is identified"
        )

    if not recs:
        recs.append("No actionable recommendations — error rate is within normal bounds")

    return recs


# ── Public API ────────────────────────────────────────────────────────────────

def summarize(
    classified: List[ClassifiedError],
    window_hours: int = 24,
) -> InsightReport:
    """Aggregate classified errors into an InsightReport.

    Args:
        classified: Output of classify_jsonl().
        window_hours: How many hours back to analyze. 0 = all records.

    Returns:
        InsightReport with top categories, trends, clusters, and recommendations.
    """
    filtered = _filter_window(classified, window_hours)
    total = len(filtered)

    if total == 0:
        return InsightReport(
            window_hours=window_hours,
            total_errors=0,
            top_categories=[],
            error_rate_trend="insufficient_data",
            rate_per_hour=0.0,
            clusters=[],
            suspected_root_causes=[],
            recommendations=["No errors in the selected window"],
        )

    rate = total / window_hours if window_hours > 0 else 0.0
    trend = _error_rate_trend(classified, window_hours)
    top = _top_categories(filtered, total)
    clusters = _detect_clusters(filtered)
    causes = _build_suspected_root_causes(clusters, top)
    recs = _build_recommendations(top, clusters, rate, trend)

    return InsightReport(
        window_hours=window_hours,
        total_errors=total,
        top_categories=top,
        error_rate_trend=trend,
        rate_per_hour=round(rate, 3),
        clusters=clusters,
        suspected_root_causes=causes,
        recommendations=recs,
    )
