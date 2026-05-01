#!/usr/bin/env python3
"""
check_lazy_catalog_health.py — Lazy Catalog Telemetry Aggregator

Reads .cognitive-os/runtime/skill-discovery.jsonl, computes 24h rolling
rates of suspected_missed_skills with lazy ON vs OFF, and prints a
recommendation.

Usage:
    python3 scripts/check_lazy_catalog_health.py [--json] [--window-hours N]

Output:
    Human-readable summary (default) or JSON (--json).

Exit codes:
    0 — healthy (miss rate within 2× baseline)
    1 — degraded (miss rate exceeds 2× baseline, recommend COS_LAZY_CATALOG=0)
    2 — insufficient data (cannot determine)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(
    os.environ.get("CLAUDE_PROJECT_DIR",
                   os.environ.get("COGNITIVE_OS_PROJECT_DIR",
                                  str(Path(__file__).resolve().parents[1])))
)
TELEMETRY_PATH = PROJECT_ROOT / ".cognitive-os" / "runtime" / "skill-discovery.jsonl"
BASELINE_PATH = PROJECT_ROOT / "docs" / "measurements" / "lazy-catalog-baseline.json"


def load_records(window_hours: float) -> list[dict[str, Any]]:
    if not TELEMETRY_PATH.exists():
        return []
    cutoff = time.time() - window_hours * 3600
    records: list[dict[str, Any]] = []
    for line in TELEMETRY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if r.get("ts", 0) >= cutoff:
                records.append(r)
        except json.JSONDecodeError:
            pass
    return records


def compute_rate(records: list[dict[str, Any]], lazy_active: bool) -> dict[str, Any]:
    """Compute per-session miss rate for the given lazy_active state."""
    filtered = [r for r in records if r.get("event") == "agent_telemetry"
                and r.get("lazy_catalog_active") == lazy_active]
    if not filtered:
        return {"sessions": 0, "sessions_with_miss": 0, "rate": 0.0}

    sessions_with_miss: set[str] = set()
    all_sessions: set[str] = set()
    for r in filtered:
        sid = r.get("session_id", "")
        if sid:
            all_sessions.add(sid)
            if r.get("suspected_missed_skills"):
                sessions_with_miss.add(sid)

    rate = len(sessions_with_miss) / len(all_sessions) if all_sessions else 0.0
    return {
        "sessions": len(all_sessions),
        "sessions_with_miss": len(sessions_with_miss),
        "rate": round(rate, 4),
    }


def load_baseline() -> dict[str, Any]:
    if not BASELINE_PATH.exists():
        return {}
    try:
        return json.loads(BASELINE_PATH.read_text())
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--window-hours", type=float, default=24.0,
                        help="Rolling window in hours (default: 24)")
    args = parser.parse_args()

    records = load_records(args.window_hours)
    baseline = load_baseline()

    lazy_on = compute_rate(records, lazy_active=True)
    lazy_off = compute_rate(records, lazy_active=False)
    baseline_rate = float(baseline.get("missed_skills_rate_per_session", 0.0))

    # Injection events
    injections = sum(1 for r in records if r.get("event") == "catalog_injected")
    total_ups = sum(1 for r in records
                    if r.get("event") == "agent_telemetry" and r.get("lazy_catalog_active"))

    # Recommendation
    degraded = False
    recommendation = "OK"
    if lazy_on["sessions"] >= 3:
        threshold = baseline_rate * 2.0 if baseline_rate > 0 else 0.20
        if lazy_on["rate"] > threshold:
            degraded = True
            recommendation = (
                f"DEGRADE: lazy miss rate {lazy_on['rate']:.1%} > 2× baseline "
                f"{baseline_rate:.1%}. Set COS_LAZY_CATALOG=0."
            )
    elif lazy_on["sessions"] < 3:
        recommendation = "INSUFFICIENT_DATA"

    result = {
        "window_hours": args.window_hours,
        "total_records": len(records),
        "catalog_injections": injections,
        "agent_turns_lazy_on": total_ups,
        "lazy_on": lazy_on,
        "lazy_off": lazy_off,
        "baseline_rate": baseline_rate,
        "recommendation": recommendation,
        "degraded": degraded,
        "token_savings_per_session_k": 3.5,
        "sessions_observed_lazy": lazy_on["sessions"],
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Lazy Catalog Health ({args.window_hours}h window)")
        print(f"  Records in window : {len(records)}")
        print(f"  Catalog injections: {injections} / {total_ups} agent turns (lazy ON)")
        print(f"  Lazy ON  — sessions: {lazy_on['sessions']}, "
              f"miss rate: {lazy_on['rate']:.1%}")
        print(f"  Lazy OFF — sessions: {lazy_off['sessions']}, "
              f"miss rate: {lazy_off['rate']:.1%}")
        print(f"  Baseline rate     : {baseline_rate:.1%}")
        print(f"  Token savings     : ~3.5K per lazy session")
        print(f"  Recommendation    : {recommendation}")

    if recommendation == "INSUFFICIENT_DATA":
        return 2
    return 1 if degraded else 0


if __name__ == "__main__":
    sys.exit(main())
