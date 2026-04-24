"""ADR-028 Phase B D2 contract: p95 hook latency.

Reads `.cognitive-os/metrics/hook-health.jsonl`, computes per-hook p50/p95
durations, and asserts the p95 stays below a ceiling. Hooks that show up
with fewer than N samples are ignored (percentiles on tiny samples are
noise).

Thresholds:
  COS_HOOK_P95_CEILING_MS   default 1500 ms  (overall p95 across all hooks)
  COS_HOOK_MIN_SAMPLES      default 10       (per-hook minimum to include)
"""
from __future__ import annotations

import json
import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pytest


_ROOT = Path(__file__).resolve().parent.parent.parent
_P95_CEILING_MS = int(os.environ.get("COS_HOOK_P95_CEILING_MS", "1500"))
_MIN_SAMPLES = int(os.environ.get("COS_HOOK_MIN_SAMPLES", "10"))
_MAX_SAMPLE_AGE_HOURS = int(os.environ.get("COS_HOOK_MAX_SAMPLE_AGE_HOURS", "6"))
_HOOK_HEALTH = _ROOT / ".cognitive-os" / "metrics" / "hook-health.jsonl"


def _load_samples() -> List[dict]:
    if not _HOOK_HEALTH.is_file():
        pytest.skip(f"no hook-health data at {_HOOK_HEALTH}")
    rows: List[dict] = []
    for line in _HOOK_HEALTH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        # MetricEvent rows wrap fields in `payload`; legacy rows are flat.
        if "schema_version" in row and "payload" in row:
            payload = row["payload"] or {}
            hook = payload.get("hook") or payload.get("hook_name") or payload.get("script")
            dur = payload.get("duration_ms") or payload.get("elapsed_ms")
        else:
            hook = row.get("hook") or row.get("hook_name") or row.get("script")
            dur = row.get("duration_ms") or row.get("elapsed_ms")
        if hook is None or dur is None:
            continue
        try:
            rows.append({
                "hook": str(hook),
                "duration_ms": float(dur),
                "timestamp": row.get("timestamp") or payload.get("timestamp"),
            })
        except (TypeError, ValueError):
            continue
    return _fresh_rows(rows)


def _fresh_rows(rows: List[dict]) -> List[dict]:
    """Keep recent telemetry so stale local history does not fail current runs."""
    parsed = []
    for row in rows:
        ts = row.get("timestamp")
        if not ts:
            continue
        try:
            parsed_ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed_ts.tzinfo is None:
            parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
        parsed.append((parsed_ts, row))
    if not parsed:
        return rows
    latest = max(ts for ts, _ in parsed)
    cutoff = latest - timedelta(hours=_MAX_SAMPLE_AGE_HOURS)
    fresh = [row for ts, row in parsed if ts >= cutoff]
    return fresh


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def _by_hook(rows: List[dict]) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for r in rows:
        out.setdefault(r["hook"], []).append(r["duration_ms"])
    return out


# ---------------------------------------------------------------------------


def test_hook_health_has_parsable_rows():
    rows = _load_samples()
    assert len(rows) >= 1, "hook-health.jsonl exists but no rows are parsable"


def test_no_hook_p95_exceeds_ceiling():
    """For every hook with >= _MIN_SAMPLES datapoints, p95 must stay under ceiling."""
    rows = _load_samples()
    groups = _by_hook(rows)
    offenders = []
    evaluated = 0
    for hook, durations in groups.items():
        if len(durations) < _MIN_SAMPLES:
            continue
        evaluated += 1
        p95 = _percentile(durations, 0.95)
        if p95 > _P95_CEILING_MS:
            offenders.append((hook, len(durations), p95))
    if evaluated == 0:
        pytest.skip(f"no hooks with >= {_MIN_SAMPLES} samples; cannot compute p95")
    assert not offenders, (
        f"{len(offenders)} hook(s) exceed p95 ceiling {_P95_CEILING_MS} ms: "
        + ", ".join(f"{h} (n={n}, p95={p:.0f})" for h, n, p in offenders)
    )


def test_overall_p95_under_ceiling():
    """Aggregate p95 across all samples should be under ceiling."""
    rows = _load_samples()
    durations = [r["duration_ms"] for r in rows]
    if len(durations) < _MIN_SAMPLES:
        pytest.skip(f"only {len(durations)} samples; need >= {_MIN_SAMPLES}")
    p95 = _percentile(durations, 0.95)
    p50 = _percentile(durations, 0.50)
    assert p95 <= _P95_CEILING_MS, (
        f"overall p95 hook latency {p95:.0f} ms exceeds {_P95_CEILING_MS} ms ceiling "
        f"(p50={p50:.0f} ms, n={len(durations)})"
    )


def test_percentile_helper_handles_edges():
    """Behavioral sanity on the percentile implementation."""
    assert _percentile([], 0.5) == 0.0
    assert _percentile([10], 0.95) == 10
    assert _percentile([1, 2, 3, 4, 5], 0.0) == 1
    assert _percentile([1, 2, 3, 4, 5], 1.0) == 5
    # p50 of evenly spaced values = the middle value
    assert _percentile([1, 2, 3, 4, 5], 0.5) == 3
