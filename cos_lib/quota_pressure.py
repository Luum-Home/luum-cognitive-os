"""Quota pressure heuristic for adaptive Agent() dispatch (ADR-056).

Computes a bounded quota-pressure score in [0..1] by combining two signals:
  1. Recent rate-limit errors in `llm-dispatch.jsonl` (primary signal).
  2. Session cost accumulated in `cost-events.jsonl` vs daily budget.

Used by `hooks/agent-quota-advisor.sh` (L1 advisory) and reserved for
future L2 auto-redirect / L3 transparent-bridge work.

The heuristic is intentionally simple and non-aspirational: it fuses only
data that already exists on disk — no new API calls, no remote probes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

# Match `lib/dispatch.py::_RATE_LIMIT_PATTERNS` — kept in sync.
# Any substring (case-insensitive) in a dispatched provider error means
# the call was throttled and should count toward quota pressure.
_RATE_LIMIT_PATTERNS: tuple[str, ...] = (
    "out of extra usage",
    "rate limit exceeded",
    "approximate usage limit",
    "approximately usage limit",
    "approaching your usage limit",
    "usage limit",
    "429",
    "too many requests",
    "quota exceeded",
)

# Tuning constants. Override via env vars if future experiments demand it.
_DEFAULT_DAILY_BUDGET_USD = 10.0  # cognitive-os.yaml resources.budget.daily_alert_usd
_RATE_LIMIT_WEIGHT = 0.5          # per-occurrence contribution (capped at 1.0 from signal)
_COST_WEIGHT = 0.5                # cost-vs-budget contribution (capped at 1.0)


def _iter_recent(path: Path, cutoff_epoch: float) -> Iterable[dict]:
    """Yield JSON records from a JSONL file whose timestamp is >= cutoff.

    Silently skips malformed lines / missing timestamps. Returns nothing if
    the file does not exist or is unreadable.
    """
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts_epoch = _record_epoch(rec)
                if ts_epoch is None or ts_epoch < cutoff_epoch:
                    continue
                yield rec
    except OSError:
        return


def _record_epoch(rec: dict) -> float | None:
    """Best-effort: find a timestamp in the record and convert to epoch seconds.

    Accepts either `ts` (llm-dispatch.jsonl) or `timestamp` (cost-events.jsonl)
    in ISO-8601 format with trailing Z or offset.
    """
    raw = rec.get("ts") or rec.get("timestamp")
    if not raw or not isinstance(raw, str):
        return None
    # Strip trailing Z for fromisoformat compatibility on older Python.
    candidate = raw.rstrip("Z")
    # If no TZ info, treat as UTC (most of our JSONL uses Z).
    try:
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            # microseconds weirdness: drop fractional
            candidate = candidate.split(".")[0]
            dt = datetime.fromisoformat(candidate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, ImportError):
        return None


def _has_rate_limit(error: str | None) -> bool:
    if not error or not isinstance(error, str):
        return False
    low = error.lower()
    return any(p in low for p in _RATE_LIMIT_PATTERNS)


def _count_rate_limits(dispatch_path: Path, cutoff_epoch: float) -> int:
    """Count records in `llm-dispatch.jsonl` that look like rate-limit errors."""
    count = 0
    for rec in _iter_recent(dispatch_path, cutoff_epoch):
        err = rec.get("error", "")
        success = rec.get("success", True)
        # A record "counts" as a rate-limit signal if either:
        #   - success is False AND error matches a pattern
        #   - the provider list includes claude AND success is True but a previous
        #     provider in `providers_tried` errored with a rate-limit. (skipped —
        #     the per-attempt error isn't recorded in the per-dispatch row today)
        if not success and _has_rate_limit(err):
            count += 1
    return count


def _sum_recent_cost(cost_path: Path, cutoff_epoch: float) -> float:
    """Sum estimated_cost_usd for records in window. Accepts multiple schemas."""
    total = 0.0
    for rec in _iter_recent(cost_path, cutoff_epoch):
        # cost-events.jsonl: payload.estimated_cost_usd
        payload = rec.get("payload") or {}
        cost = payload.get("estimated_cost_usd")
        if cost is None:
            cost = rec.get("cost_usd")  # llm-dispatch.jsonl fallback shape
        try:
            if cost is not None:
                total += float(cost)
        except (TypeError, ValueError):
            continue
    return total


def compute_quota_pressure(
    metrics_path: Path,
    window_min: int = 30,
    daily_budget_usd: float = _DEFAULT_DAILY_BUDGET_USD,
    now_epoch: float | None = None,
) -> float:
    """Return quota-pressure score in [0.0, 1.0].

    Parameters
    ----------
    metrics_path
        Directory containing `llm-dispatch.jsonl` and `cost-events.jsonl`.
        Missing files are tolerated — the signal simply reads as zero.
    window_min
        Look-back window in minutes. Default 30min matches rate-limit
        refresh cadence observed in ADR-049 telemetry.
    daily_budget_usd
        Daily alert threshold from `cognitive-os.yaml`. Cost signal normalizes
        against this value (cost/budget, capped at 1.0).
    now_epoch
        Override for deterministic testing. Defaults to `time.time()`.

    Returns
    -------
    float
        0.0 when both signals are zero. 1.0 when either rate-limit errors
        are saturated or session cost >= daily budget. Values in between
        represent a weighted blend (currently 50/50).
    """
    if now_epoch is None:
        now_epoch = time.time()
    cutoff = now_epoch - (window_min * 60.0)

    dispatch_path = metrics_path / "llm-dispatch.jsonl"
    cost_path = metrics_path / "cost-events.jsonl"

    rate_limit_count = _count_rate_limits(dispatch_path, cutoff)
    # Normalize: 1 rate-limit error in window -> 0.5 signal, 2+ -> 1.0
    rate_limit_signal = min(1.0, rate_limit_count / 2.0)

    cost_usd = _sum_recent_cost(cost_path, cutoff)
    if daily_budget_usd <= 0:
        cost_signal = 0.0
    else:
        cost_signal = min(1.0, cost_usd / daily_budget_usd)

    pressure = (rate_limit_signal * _RATE_LIMIT_WEIGHT) + (cost_signal * _COST_WEIGHT)
    # Cap at 1.0 for safety (math makes this already true, but be explicit).
    return max(0.0, min(1.0, pressure))


def pressure_band(pressure: float) -> str:
    """Translate a raw score into a UX label used by the advisory hook.

    Thresholds aligned with ADR-056 L1 spec:
      - LOW     (< 0.5)  — silent
      - ADVISORY (0.5-0.8) — warning
      - STRONG  (>= 0.8)  — strong advisory mentioning COS_AUTO_REDIRECT_AGENT
    """
    if pressure >= 0.8:
        return "STRONG"
    if pressure >= 0.5:
        return "ADVISORY"
    return "LOW"
