# SCOPE: both
"""Provider-agnostic outcome metrics.

These metrics intentionally focus on outcomes produced by dispatches rather
than on which provider happened to execute them.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable, Mapping


@dataclass(frozen=True)
class DispatchOutcomeSnapshot:
    total_dispatches: int
    successful_dispatches: int
    success_rate: float
    average_latency_ms: float
    p95_latency_ms: float
    average_cost_usd: float
    cost_per_successful_dispatch: float


def _percentile(values: list[float], percentile: float) -> float:
    """Return a simple nearest-rank percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, ceil(percentile * len(ordered))) - 1
    return float(ordered[min(rank, len(ordered) - 1)])


def compute_dispatch_outcomes(records: Iterable[Mapping[str, object]]) -> DispatchOutcomeSnapshot:
    """Compute provider-agnostic outcome metrics from dispatch-like records."""
    rows = list(records)
    total = len(rows)
    if total == 0:
        return DispatchOutcomeSnapshot(
            total_dispatches=0,
            successful_dispatches=0,
            success_rate=0.0,
            average_latency_ms=0.0,
            p95_latency_ms=0.0,
            average_cost_usd=0.0,
            cost_per_successful_dispatch=0.0,
        )

    successes = sum(1 for row in rows if bool(row.get("success", False)))
    latencies = [float(row.get("latency_ms", 0) or 0) for row in rows]
    costs = [float(row.get("cost_usd", 0) or 0) for row in rows]
    total_cost = sum(costs)

    return DispatchOutcomeSnapshot(
        total_dispatches=total,
        successful_dispatches=successes,
        success_rate=round(successes / total, 4),
        average_latency_ms=round(sum(latencies) / total, 2),
        p95_latency_ms=round(_percentile(latencies, 0.95), 2),
        average_cost_usd=round(total_cost / total, 6),
        cost_per_successful_dispatch=round(total_cost / successes, 6) if successes else 0.0,
    )
