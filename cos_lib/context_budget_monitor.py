# SCOPE: both
"""Calibration report for ADR-186 context-budget runtime metrics."""
from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SLO_PASS_RATE = 0.90
SLO_WARN_RATE_MAX = 0.08
SLO_BLOCK_RATE_MAX = 0.02
SLO_OVERRIDE_RATE_MAX = 0.05
SLO_METER_P99_MS = 30.0


@dataclass(frozen=True)
class ContextBudgetReport:
    status: str
    total_entries: int
    window_days: int
    pass_rate: float
    warn_rate: float
    block_rate: float
    override_rate: float
    meter_p99_ms: float | None
    verdict_counts: dict[str, int]
    by_source: dict[str, dict[str, Any]]
    findings: list[str]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def metrics_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / ".cognitive-os" / "metrics" / "context-budget.jsonl"


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[index]


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _source_summary(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("source") or "unknown")].append(row)
    out: dict[str, dict[str, Any]] = {}
    for source, items in grouped.items():
        counts = Counter(str(item.get("verdict") or "UNKNOWN") for item in items)
        ratios = [float(item.get("ratio_used") or 0) for item in items]
        out[source] = {
            "count": len(items),
            "verdict_counts": dict(counts),
            "max_ratio_used": round(max(ratios), 4) if ratios else 0.0,
            "avg_ratio_used": round(sum(ratios) / len(ratios), 4) if ratios else 0.0,
        }
    return dict(sorted(out.items()))


def build_report(
    project_dir: str | Path,
    *,
    window_days: int = 30,
    now_epoch: float | None = None,
) -> ContextBudgetReport:
    """Build a falsifiable ADR-186 calibration report from context-budget JSONL."""
    now = time.time() if now_epoch is None else now_epoch
    cutoff = now - (window_days * 24 * 3600)
    rows = [row for row in read_rows(metrics_path(project_dir)) if float(row.get("timestamp_epoch") or 0) >= cutoff]
    total = len(rows)
    verdict_counts = Counter(str(row.get("verdict") or "UNKNOWN") for row in rows)
    overrides = sum(1 for row in rows if row.get("reason") == "override" or (row.get("verdict") == "BLOCK" and row.get("allowed") is True))
    meter_latencies = [float(row.get("latency_ms")) for row in rows if row.get("source") == "context-budget-meter" and row.get("latency_ms") is not None]
    meter_p99 = _percentile(meter_latencies, 99)

    pass_rate = _rate(verdict_counts.get("PASS", 0), total)
    warn_rate = _rate(verdict_counts.get("WARN", 0), total)
    block_rate = _rate(verdict_counts.get("BLOCK", 0), total)
    override_rate = _rate(overrides, total)

    findings: list[str] = []
    if total == 0:
        findings.append("no context-budget metrics found; calibration cannot start")
    if total and pass_rate < SLO_PASS_RATE:
        findings.append(f"PASS rate {pass_rate:.1%} below target {SLO_PASS_RATE:.0%}")
    if warn_rate > SLO_WARN_RATE_MAX:
        findings.append(f"WARN rate {warn_rate:.1%} above target {SLO_WARN_RATE_MAX:.0%}")
    if block_rate > SLO_BLOCK_RATE_MAX:
        findings.append(f"BLOCK rate {block_rate:.1%} above target {SLO_BLOCK_RATE_MAX:.0%}")
    if override_rate > SLO_OVERRIDE_RATE_MAX:
        findings.append(f"override rate {override_rate:.1%} above target {SLO_OVERRIDE_RATE_MAX:.0%}")
    if meter_p99 is not None and meter_p99 > SLO_METER_P99_MS:
        findings.append(f"context-budget-meter p99 {meter_p99:.1f}ms above target {SLO_METER_P99_MS:.0f}ms")

    status = "pass" if total > 0 and not findings else "warn"
    recommendation = "keep current budgets" if status == "pass" else "collect more data or recalibrate context_budget thresholds"
    return ContextBudgetReport(
        status=status,
        total_entries=total,
        window_days=window_days,
        pass_rate=pass_rate,
        warn_rate=warn_rate,
        block_rate=block_rate,
        override_rate=override_rate,
        meter_p99_ms=round(meter_p99, 3) if meter_p99 is not None else None,
        verdict_counts=dict(verdict_counts),
        by_source=_source_summary(rows),
        findings=findings,
        recommendation=recommendation,
    )
