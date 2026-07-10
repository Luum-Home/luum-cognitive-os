#!/usr/bin/env python3
# SCOPE: os-only
"""Read-path report: portable token/cost telemetry from cost-events.jsonl.

Reads ``.cognitive-os/metrics/cost-events.jsonl`` and prints a summary table
with per-session and per-day totals, cache-hit ratio, provider/harness coverage,
and cost breakdown. Real rows (``is_estimate: false`` and
``source: "transcript"`` or ``telemetry_schema: token-usage-normalized.v1``) are
distinguished from estimate rows.

Usage::

    python3 scripts/token_report.py [--by session|day] [--json] [--project-dir DIR]

Flags:
    --by session   Per-session detail (default when no flag given: both)
    --by day       Per-day rollup
    --json         Emit JSON instead of a plain table
    --project-dir  Project root (default: runtime_project_root_or_cwd())
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from cos_lib.paths import runtime_project_root_or_cwd


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_event_date(row: dict) -> str:
    """Return YYYY-MM-DD for a cost event row, or 'unknown'."""
    ts = row.get("timestamp") or row.get("ts")
    if ts:
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    return "unknown"


def load_cost_events(cost_file: str) -> list[dict]:
    """Return all parsed rows from cost-events.jsonl; silently skip bad lines."""
    rows = []
    p = Path(cost_file)
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                rows.append(json.loads(raw_line))
            except json.JSONDecodeError:
                continue
    return rows


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _is_real_usage_payload(payload: dict) -> bool:
    return (
        payload.get("is_estimate") is False
        and (
            payload.get("source") == "transcript"
            or payload.get("telemetry_schema") == "token-usage-normalized.v1"
        )
    )


def _aggregate_session(rows: list[dict]) -> list[dict]:
    """Return one summary dict per session_id from normalized real-usage rows."""
    by_session: dict[str, dict] = {}
    for row in rows:
        payload = row.get("payload", {})
        if not _is_real_usage_payload(payload):
            continue
        sid = payload.get("session_id", "unknown")
        if sid not in by_session:
            by_session[sid] = {
                "session_id": sid,
                "date": _parse_event_date(row),
                "model": payload.get("model", "unknown"),
                "providers_seen": set(payload.get("providers_seen") or []),
                "harnesses_seen": set(payload.get("harnesses_seen") or []),
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read": 0,
                "cache_write": 0,
                "actual_cost_usd": 0.0,
                "has_null_cost": False,
                "pricing_known": payload.get("pricing_known", True),
            }
        s = by_session[sid]
        s["providers_seen"].update(payload.get("providers_seen") or [])
        s["harnesses_seen"].update(payload.get("harnesses_seen") or [])
        s["input_tokens"] += payload.get("input_tokens", 0)
        s["output_tokens"] += payload.get("output_tokens", 0)
        s["cache_read"] += payload.get("cache_read_input_tokens", 0)
        s["cache_write"] += payload.get("cache_creation_input_tokens", 0)
        cost = payload.get("actual_cost_usd")
        if cost is None:
            s["has_null_cost"] = True
        else:
            s["actual_cost_usd"] = (s["actual_cost_usd"] or 0.0) + float(cost)
        if not payload.get("pricing_known", True):
            s["pricing_known"] = False
    out = []
    for row in by_session.values():
        row["providers_seen"] = sorted(row["providers_seen"])
        row["harnesses_seen"] = sorted(row["harnesses_seen"])
        out.append(row)
    return sorted(out, key=lambda r: r["date"])


def _aggregate_day(rows: list[dict]) -> list[dict]:
    """Return one summary dict per calendar day from normalized real-usage rows."""
    by_day: dict[str, dict] = {}
    for row in rows:
        payload = row.get("payload", {})
        if not _is_real_usage_payload(payload):
            continue
        day = _parse_event_date(row)
        if day not in by_day:
            by_day[day] = {
                "date": day,
                "sessions": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read": 0,
                "cache_write": 0,
                "actual_cost_usd": 0.0,
                "has_null_cost": False,
                "providers_seen": set(payload.get("providers_seen") or []),
                "harnesses_seen": set(payload.get("harnesses_seen") or []),
            }
        d = by_day[day]
        d["providers_seen"].update(payload.get("providers_seen") or [])
        d["harnesses_seen"].update(payload.get("harnesses_seen") or [])
        d["sessions"] += 1
        d["input_tokens"] += payload.get("input_tokens", 0)
        d["output_tokens"] += payload.get("output_tokens", 0)
        d["cache_read"] += payload.get("cache_read_input_tokens", 0)
        d["cache_write"] += payload.get("cache_creation_input_tokens", 0)
        cost = payload.get("actual_cost_usd")
        if cost is None:
            d["has_null_cost"] = True
        else:
            d["actual_cost_usd"] = (d["actual_cost_usd"] or 0.0) + float(cost)
    out = []
    for row in by_day.values():
        row["providers_seen"] = sorted(row["providers_seen"])
        row["harnesses_seen"] = sorted(row["harnesses_seen"])
        out.append(row)
    return sorted(out, key=lambda r: r["date"])


def _cache_hit_ratio(input_tokens: int, cache_read: int, cache_write: int) -> float:
    """Cache-hit ratio: cache_read / (input + cache_read + cache_write)."""
    total = input_tokens + cache_read + cache_write
    if total == 0:
        return 0.0
    return round(cache_read / total, 4)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _fmt_cost(cost: float, has_null: bool) -> str:
    if has_null:
        return f"${cost:.4f}*"  # asterisk = partial (some turns had unknown pricing)
    return f"${cost:.4f}"


def print_session_table(sessions: list[dict]) -> None:
    if not sessions:
        print("No real token usage events found.")
        return
    header = f"{'SESSION':<30} {'DATE':<12} {'MODEL':<16} {'PROVIDER':<12} {'HARNESS':<12} {'INPUT':>8} {'OUTPUT':>8} {'CACHE_R':>8} {'CACHE_W':>8} {'RATIO':>6} {'COST':>10}"
    print(header)
    print("-" * len(header))
    for s in sessions:
        ratio = _cache_hit_ratio(s["input_tokens"], s["cache_read"], s["cache_write"])
        cost_str = _fmt_cost(s["actual_cost_usd"] or 0.0, s["has_null_cost"])
        row = (
            f"{s['session_id'][:28]:<30} "
            f"{s['date']:<12} "
            f"{s['model'][:14]:<16} "
            f"{','.join(s.get('providers_seen') or ['unknown'])[:10]:<12} "
            f"{','.join(s.get('harnesses_seen') or ['unknown'])[:10]:<12} "
            f"{s['input_tokens']:>8} "
            f"{s['output_tokens']:>8} "
            f"{s['cache_read']:>8} "
            f"{s['cache_write']:>8} "
            f"{ratio:>6.2%} "
            f"{cost_str:>10}"
        )
        print(row)
    print()
    print("* = one or more turns had unknown model pricing; cost is partial.")


def print_day_table(days: list[dict]) -> None:
    if not days:
        print("No real token usage events found.")
        return
    header = f"{'DATE':<12} {'SESSIONS':>8} {'PROVIDERS':<16} {'HARNESSES':<16} {'INPUT':>10} {'OUTPUT':>8} {'CACHE_R':>8} {'CACHE_W':>8} {'RATIO':>6} {'COST':>10}"
    print(header)
    print("-" * len(header))
    for d in days:
        ratio = _cache_hit_ratio(d["input_tokens"], d["cache_read"], d["cache_write"])
        cost_str = _fmt_cost(d["actual_cost_usd"] or 0.0, d["has_null_cost"])
        row = (
            f"{d['date']:<12} "
            f"{d['sessions']:>8} "
            f"{','.join(d.get('providers_seen') or ['unknown'])[:14]:<16} "
            f"{','.join(d.get('harnesses_seen') or ['unknown'])[:14]:<16} "
            f"{d['input_tokens']:>10} "
            f"{d['output_tokens']:>8} "
            f"{d['cache_read']:>8} "
            f"{d['cache_write']:>8} "
            f"{ratio:>6.2%} "
            f"{cost_str:>10}"
        )
        print(row)
    print()
    print("* = one or more sessions had unknown model pricing; cost is partial.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report portable real token usage and cost from cost-events.jsonl.",
    )
    parser.add_argument(
        "--by",
        choices=["session", "day"],
        default=None,
        help="Grouping: 'session' for per-session detail, 'day' for daily rollup. "
             "Default: both.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit JSON instead of a plain table.",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Project root. Defaults to runtime_project_root_or_cwd().",
    )
    args = parser.parse_args(argv)

    project_dir = args.project_dir or str(runtime_project_root_or_cwd())
    cost_file = os.path.join(project_dir, ".cognitive-os", "metrics", "cost-events.jsonl")

    rows = load_cost_events(cost_file)

    if args.emit_json:
        sessions = _aggregate_session(rows)
        days = _aggregate_day(rows)
        out: dict = {}
        if args.by in (None, "session"):
            out["sessions"] = sessions
        if args.by in (None, "day"):
            out["days"] = days
        print(json.dumps(out, indent=2))
        return 0

    if args.by == "session" or args.by is None:
        sessions = _aggregate_session(rows)
        print("\n=== Per-Session Token Report (real transcript rows) ===\n")
        print_session_table(sessions)

    if args.by == "day" or args.by is None:
        days = _aggregate_day(rows)
        print("\n=== Per-Day Token Report (real transcript rows) ===\n")
        print_day_table(days)

    return 0


if __name__ == "__main__":
    sys.exit(main())
