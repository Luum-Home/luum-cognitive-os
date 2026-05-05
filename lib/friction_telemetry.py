"""Friction telemetry aggregation for ADR-123-S1."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

OUTCOMES = {"observe", "warn", "block", "auto_repair", "bypass"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * pct))
    return float(ordered[index])


def hook_name(row: dict[str, Any]) -> str:
    for key in ("hook", "hook_id", "source", "name"):
        value = row.get(key)
        if value:
            return str(value)
    return "unknown"


def reason(row: dict[str, Any]) -> str:
    for key in ("reason", "skip_reason", "error", "message", "execution_status"):
        value = row.get(key)
        if value:
            return str(value)
    exit_code = row.get("exit_code")
    if exit_code not in (None, ""):
        return f"exit_code={exit_code}"
    return "unspecified"


def latency_ms(row: dict[str, Any]) -> float:
    for key in ("body_duration_ms", "latency_ms", "duration_ms"):
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def normalize_outcome(row: dict[str, Any]) -> str:
    explicit = str(row.get("outcome") or row.get("normalized_outcome") or "").strip()
    if explicit in OUTCOMES:
        return explicit
    event_type = str(row.get("event_type") or row.get("event") or "").lower()
    if row.get("bypass") is True or "bypass" in event_type:
        return "bypass"
    if row.get("auto_repair") is True or "repair" in event_type:
        return "auto_repair"
    try:
        exit_code = int(row.get("exit_code", 0) or 0)
    except (TypeError, ValueError):
        exit_code = 0
    status = str(row.get("execution_status") or "ok").lower()
    if exit_code == 2:
        return "block"
    if exit_code != 0 or status in {"error", "failed", "timeout", "killed", "safe_mode"}:
        return "warn"
    return "observe"


def top(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"hook": hook, "count": count} for hook, count in counter.most_common(limit)]


def summarize(rows: Iterable[dict[str, Any]], *, limit: int = 10, false_positive_threshold: int = 2) -> dict[str, Any]:
    outcome_counts: Counter[str] = Counter()
    blockers: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    bypasses: Counter[str] = Counter()
    repairs: Counter[str] = Counter()
    latencies: dict[str, list[float]] = defaultdict(list)
    reason_counts: Counter[tuple[str, str, str]] = Counter()

    total = 0
    for row in rows:
        total += 1
        hook = hook_name(row)
        outcome = normalize_outcome(row)
        outcome_counts[outcome] += 1
        latencies[hook].append(latency_ms(row))
        if outcome == "block":
            blockers[hook] += 1
        elif outcome == "warn":
            warnings[hook] += 1
        elif outcome == "bypass":
            bypasses[hook] += 1
        elif outcome == "auto_repair":
            repairs[hook] += 1
        if outcome in {"block", "warn"}:
            reason_counts[(hook, outcome, reason(row))] += 1

    p95 = [
        {"hook": hook, "p95_latency_ms": round(percentile(values, 0.95), 2), "samples": len(values)}
        for hook, values in latencies.items()
    ]
    p95.sort(key=lambda item: (-item["p95_latency_ms"], item["hook"]))

    candidates = [
        {"hook": hook, "outcome": outcome, "reason": why, "count": count}
        for (hook, outcome, why), count in reason_counts.items()
        if count >= false_positive_threshold
    ]
    candidates.sort(key=lambda item: (-item["count"], item["hook"], item["reason"]))

    return {
        "schema_version": "friction-telemetry.v1",
        "total_events": total,
        "outcome_counts": {outcome: outcome_counts.get(outcome, 0) for outcome in sorted(OUTCOMES)},
        "top_blocking_hooks": top(blockers, limit),
        "top_warning_hooks": top(warnings, limit),
        "top_bypass_hooks": top(bypasses, limit),
        "top_auto_repair_hooks": top(repairs, limit),
        "top_latency_hooks": p95[:limit],
        "false_positive_candidates": candidates[:limit],
    }
