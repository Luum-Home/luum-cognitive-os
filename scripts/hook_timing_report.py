#!/usr/bin/env python3
"""hook_timing_report.py — Aggregate and display hook execution timing.

Reads .cognitive-os/metrics/hook-timing.jsonl and prints per-hook statistics
(invocations, p50/p95/p99 duration, failure count) plus a top-10 slowest
individual invocations list.

Usage:
  python3 scripts/hook_timing_report.py              # full report
  python3 scripts/hook_timing_report.py --live       # tail -f the JSONL, human-readable
  python3 scripts/hook_timing_report.py --event Stop # filter by harness event
  python3 scripts/hook_timing_report.py --top 20     # show top 20 slowest (default 10)
  python3 scripts/hook_timing_report.py --since 1h   # only records from last hour
  python3 scripts/hook_timing_report.py --json       # machine-readable JSON output
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Locate the metrics file ─────────────────────────────────────────────────

def _find_project_root() -> Path:
    """Walk up from cwd until we find cognitive-os.yaml or .claude/."""
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "cognitive-os.yaml").exists() or (candidate / ".claude").is_dir():
            return candidate
    return cwd


def _timing_log_path() -> Path:
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
    if env_dir:
        return Path(env_dir) / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
    return _find_project_root() / ".cognitive-os" / "metrics" / "hook-timing.jsonl"


# ── Parsing ─────────────────────────────────────────────────────────────────

def _parse_timestamp(ts_str: str) -> float:
    """Parse ISO-8601 UTC timestamp to epoch float. Returns 0 on failure."""
    try:
        dt = datetime.fromisoformat(ts_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def _load_records(path: Path, since_epoch: float = 0.0, event_filter: str = "", session_filter: str = "") -> list[dict]:
    """Load and filter JSONL records. Skips malformed lines silently."""
    records = []
    if not path.exists():
        return records
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_timestamp(rec.get("timestamp", ""))
            if since_epoch and ts < since_epoch:
                continue
            if event_filter and rec.get("event", "") != event_filter:
                continue
            if session_filter and rec.get("session_id", "") != session_filter:
                continue
            records.append(rec)
    return records


# ── Statistics ──────────────────────────────────────────────────────────────

def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct / 100)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


def _compute_stats(records: list[dict]) -> dict:
    """
    Returns:
      {
        "by_hook": {
          hook_name: {
            "count": int,
            "failures": int,
            "p50": float,
            "p95": float,
            "p99": float,
            "max": float,
            "total_ms": float,
            "events": set[str],
          }
        },
        "slowest": [{"hook", "event", "duration_ms", "timestamp", "exit_code"}, ...],
      }
    """
    by_hook: dict[str, dict] = defaultdict(lambda: {
        "count": 0,
        "failures": 0,
        "durations": [],
        "events": set(),
        "total_ms": 0.0,
    })

    for rec in records:
        hook = rec.get("hook", "unknown")
        dur = float(rec.get("duration_ms", 0))
        exit_code = int(rec.get("exit_code", 0))
        event = rec.get("event", "")

        h = by_hook[hook]
        h["count"] += 1
        h["durations"].append(dur)
        h["total_ms"] += dur
        h["events"].add(event)
        if exit_code != 0:
            h["failures"] += 1

    stats_by_hook = {}
    for hook, h in by_hook.items():
        sorted_d = sorted(h["durations"])
        stats_by_hook[hook] = {
            "count": h["count"],
            "failures": h["failures"],
            "p50": _percentile(sorted_d, 50),
            "p95": _percentile(sorted_d, 95),
            "p99": _percentile(sorted_d, 99),
            "max": sorted_d[-1] if sorted_d else 0.0,
            "total_ms": h["total_ms"],
            "events": sorted(h["events"]),
        }

    # Top slowest individual invocations
    slowest = sorted(
        records,
        key=lambda r: float(r.get("duration_ms", 0)),
        reverse=True,
    )

    return {"by_hook": stats_by_hook, "slowest": slowest}


# ── Formatting ───────────────────────────────────────────────────────────────

def _bar(value: float, max_val: float, width: int = 20) -> str:
    if max_val == 0:
        return " " * width
    filled = int(round(value / max_val * width))
    return "█" * filled + "░" * (width - filled)


def _format_ms(ms: float) -> str:
    if ms >= 60_000:
        return f"{ms/60_000:.1f}m"
    if ms >= 1_000:
        return f"{ms/1_000:.1f}s"
    return f"{ms:.0f}ms"


def _print_report(stats: dict, top_n: int = 10, event_filter: str = "", total_records: int = 0):
    by_hook = stats["by_hook"]
    slowest = stats["slowest"]

    # Sort hooks by p95 descending
    ranked = sorted(by_hook.items(), key=lambda kv: kv[1]["p95"], reverse=True)
    max_p95 = max((v["p95"] for v in by_hook.values()), default=1.0)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filter_note = f"  event={event_filter}" if event_filter else ""
    print(f"\n{'═'*80}")
    print(f"  Hook Timing Report — {now_str}{filter_note}")
    print(f"  Total records: {total_records:,}  |  Unique hooks: {len(by_hook)}")
    print(f"{'═'*80}\n")

    print(f"  {'HOOK':<35} {'COUNT':>6} {'FAIL':>5} {'p50':>8} {'p95':>8} {'p99':>8} {'MAX':>8}  {'p95 bar'}")
    print(f"  {'─'*35} {'─'*6} {'─'*5} {'─'*8} {'─'*8} {'─'*8} {'─'*8}  {'─'*20}")

    for hook, s in ranked:
        bar = _bar(s["p95"], max_p95)
        fail_str = f"{s['failures']}" if s["failures"] > 0 else "  ."
        print(
            f"  {hook:<35} {s['count']:>6} {fail_str:>5} "
            f"{_format_ms(s['p50']):>8} {_format_ms(s['p95']):>8} "
            f"{_format_ms(s['p99']):>8} {_format_ms(s['max']):>8}  {bar}"
        )

    # Top slowest
    print(f"\n{'─'*80}")
    print(f"  Top {top_n} slowest individual invocations:")
    print(f"{'─'*80}\n")
    print(f"  {'DURATION':>10}  {'EVENT':<20}  {'HOOK':<35}  {'EXIT':>4}  TIMESTAMP")
    print(f"  {'─'*10}  {'─'*20}  {'─'*35}  {'─'*4}  {'─'*20}")
    for rec in slowest[:top_n]:
        dur = float(rec.get("duration_ms", 0))
        hook = rec.get("hook", "unknown")
        event = rec.get("event", "")
        ts = rec.get("timestamp", "")
        exit_code = rec.get("exit_code", 0)
        print(f"  {_format_ms(dur):>10}  {event:<20}  {hook:<35}  {exit_code:>4}  {ts}")

    # Failed hooks summary
    failed_hooks = [(h, s) for h, s in ranked if s["failures"] > 0]
    if failed_hooks:
        print(f"\n{'─'*80}")
        print(f"  Failed hooks (non-zero exit):")
        print(f"{'─'*80}\n")
        for hook, s in failed_hooks:
            print(f"  {hook:<35}  {s['failures']:>4} failures out of {s['count']:>4} calls")
    else:
        print(f"\n  All hooks exited 0. No failures.\n")

    print(f"{'═'*80}\n")


# ── Live mode ────────────────────────────────────────────────────────────────

def _live_mode(path: Path):
    """Tail the JSONL file and print each new line in human-readable form."""
    print(f"Watching {path}  (Ctrl+C to stop)\n")
    print(f"  {'TIMESTAMP':<22}  {'EVENT':<20}  {'HOOK':<35}  {'DUR':>8}  EXIT")
    print(f"  {'─'*22}  {'─'*20}  {'─'*35}  {'─'*8}  {'─'*4}")
    sys.stdout.flush()

    if not path.exists():
        print(f"  (waiting for {path} to be created...)")
        sys.stdout.flush()
        while not path.exists():
            time.sleep(0.5)

    try:
        proc = subprocess.Popen(
            ["tail", "-f", "-n", "0", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            dur = float(rec.get("duration_ms", 0))
            hook = rec.get("hook", "unknown")
            event = rec.get("event", "")
            ts = rec.get("timestamp", "")[:19].replace("T", " ")
            exit_code = rec.get("exit_code", 0)
            exit_str = str(exit_code) if exit_code != 0 else "  0"
            slow_flag = "  ⚠ SLOW" if dur > 5000 else ""
            print(
                f"  {ts:<22}  {event:<20}  {hook:<35}  {_format_ms(dur):>8}  {exit_str}{slow_flag}"
            )
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\nStopped.")


# ── Parse --since ───────────────────────────────────────────────────────────

def _parse_since(since_str: str) -> float:
    """Convert '1h', '30m', '2d' to an epoch cutoff."""
    now = time.time()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if since_str[-1] in units:
        try:
            return now - int(since_str[:-1]) * units[since_str[-1]]
        except ValueError:
            pass
    try:
        return now - int(since_str)
    except ValueError:
        print(f"ERROR: Cannot parse --since '{since_str}'. Use e.g. '1h', '30m', '2d'.", file=sys.stderr)
        sys.exit(1)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Report on hook execution timing from hook-timing.jsonl"
    )
    parser.add_argument("--live", action="store_true", help="Stream new entries in real-time")
    parser.add_argument("--event", default="", help="Filter by harness event (e.g. Stop, PreToolUse)")
    parser.add_argument("--top", type=int, default=10, help="Number of slowest invocations to show (default: 10)")
    parser.add_argument("--since", default="", help="Only include records from last N (e.g. 1h, 30m, 2d)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--path", default="", help="Override path to hook-timing.jsonl")
    parser.add_argument("--session", default="", help="Filter by COS session ID (e.g. COGNITIVE_OS_SESSION_ID value)")
    args = parser.parse_args()

    log_path = Path(args.path) if args.path else _timing_log_path()

    if args.live:
        _live_mode(log_path)
        return

    since_epoch = _parse_since(args.since) if args.since else 0.0
    records = _load_records(log_path, since_epoch=since_epoch, event_filter=args.event, session_filter=args.session)

    if not records:
        if not log_path.exists():
            print(f"No hook-timing.jsonl found at {log_path}")
            print("Start a session to generate data, or run a hook through the wrapper.")
        else:
            print(f"No records match filters (event={args.event!r}, since={args.since!r}, session={args.session!r})")
        return

    stats = _compute_stats(records)

    if args.json:
        # Serialize — convert sets to sorted lists
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(records),
            "filters": {"event": args.event, "since": args.since, "session": args.session},
            "by_hook": {
                h: {**s, "events": list(s["events"])}
                for h, s in stats["by_hook"].items()
            },
            "slowest": stats["slowest"][: args.top],
        }
        print(json.dumps(output, indent=2))
        return

    _print_report(stats, top_n=args.top, event_filter=args.event, total_records=len(records))


if __name__ == "__main__":
    main()
