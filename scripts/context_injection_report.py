#!/usr/bin/env python3
# SCOPE: os-only
"""context_injection_report.py — Rank what actually injects text into context.

The context-diet machinery in this repo watches the fixed markdown tax (rules,
CLAUDE.md), which is a rounding error next to what accumulates per turn: hook
output and tool output. This report covers those two.

Section HOOKS reads .cognitive-os/metrics/hook-timing.jsonl and ranks hooks by
the bytes they wrote to stdout/stderr. stdout is the model-context channel
(PreToolUse additionalContext, SessionStart context); stderr is the
blocking-feedback channel that Claude reads on exit code 2. Both fields are
emitted by scripts/hook-timing-wrapper.sh. Rows written before that
instrumentation landed have no such fields and are reported separately as
uninstrumented, never silently counted as zero.

Section TOOLS reads truncation-events.jsonl, which result-truncator has been
writing since long before this report: every event carries original_chars and
truncated_chars, so realised savings are recoverable per event, per method and
per tool.

Usage:
  python3 scripts/context_injection_report.py                 # both sections
  python3 scripts/context_injection_report.py --section hooks
  python3 scripts/context_injection_report.py --section tools
  python3 scripts/context_injection_report.py --top 25
  python3 scripts/context_injection_report.py --since 24h
  python3 scripts/context_injection_report.py --by-event      # hook x event rows
  python3 scripts/context_injection_report.py --json

Exit codes: 0 report produced (with or without rows), 2 unreadable inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Rough conversion used everywhere in this repo's cost tooling: ~4 chars/token.
CHARS_PER_TOKEN = 4


# ── Locating inputs ─────────────────────────────────────────────────────────


def find_project_root(start: Path | None = None) -> Path:
    cwd = start or Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "cognitive-os.yaml").exists() or (candidate / ".claude").is_dir():
            return candidate
    return cwd


def parse_timestamp(value: str) -> float:
    if not value:
        return 0.0
    try:
        return (
            datetime.fromisoformat(value.rstrip("Z"))
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
    except Exception:
        return 0.0


def parse_since(spec: str) -> float:
    """'90m' / '24h' / '7d' -> seconds. Returns 0 for an empty or bad spec."""
    if not spec:
        return 0.0
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = spec[-1].lower()
    if unit not in units:
        return 0.0
    try:
        return float(spec[:-1]) * units[unit]
    except ValueError:
        return 0.0


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def tokens(chars: int) -> int:
    return chars // CHARS_PER_TOKEN


def human(n: float) -> str:
    for unit, size in (("M", 1_000_000), ("K", 1_000)):
        if abs(n) >= size:
            return f"{n / size:.1f}{unit}"
    return f"{n:.0f}"


# ── Section: hook output ────────────────────────────────────────────────────


def build_hook_report(
    rows: list[dict],
    since_epoch: float,
    by_event: bool,
    exclude: tuple[str, ...] = (),
) -> dict:
    total_rows = 0
    instrumented = 0
    excluded_rows = 0
    groups: dict[tuple[str, str], dict] = {}

    for row in rows:
        if since_epoch and parse_timestamp(row.get("timestamp", "")) < since_epoch:
            continue
        hook_name = str(row.get("hook") or "unknown")
        if any(pattern in hook_name for pattern in exclude):
            excluded_rows += 1
            continue
        total_rows += 1

        has_fields = "stdout_bytes" in row or "stderr_bytes" in row
        if not has_fields:
            continue
        instrumented += 1

        hook = str(row.get("hook") or "unknown")
        event = str(row.get("event") or "unknown") if by_event else "*"
        key = (hook, event)
        entry = groups.setdefault(
            key,
            {
                "hook": hook,
                "event": event,
                "invocations": 0,
                "stdout_bytes": 0,
                "stderr_bytes": 0,
                "silent_invocations": 0,
                "max_stdout_bytes": 0,
                "events": set(),
            },
        )
        out = int(row.get("stdout_bytes") or 0)
        err = int(row.get("stderr_bytes") or 0)
        entry["invocations"] += 1
        entry["stdout_bytes"] += out
        entry["stderr_bytes"] += err
        entry["max_stdout_bytes"] = max(entry["max_stdout_bytes"], out)
        if out == 0 and err == 0:
            entry["silent_invocations"] += 1
        entry["events"].add(str(row.get("event") or "unknown"))

    ranked = []
    for entry in groups.values():
        total_bytes = entry["stdout_bytes"] + entry["stderr_bytes"]
        invocations = entry["invocations"] or 1
        ranked.append(
            {
                "hook": entry["hook"],
                "event": entry["event"] if by_event else ",".join(sorted(entry["events"])),
                "invocations": entry["invocations"],
                "stdout_bytes": entry["stdout_bytes"],
                "stderr_bytes": entry["stderr_bytes"],
                "total_bytes": total_bytes,
                "bytes_per_invocation": round(total_bytes / invocations, 1),
                "max_stdout_bytes": entry["max_stdout_bytes"],
                "silent_pct": round(100.0 * entry["silent_invocations"] / invocations, 1),
                "est_tokens": tokens(total_bytes),
            }
        )
    ranked.sort(key=lambda item: (-item["total_bytes"], item["hook"]))

    grand_total = sum(item["total_bytes"] for item in ranked)
    for item in ranked:
        item["share_pct"] = (
            round(100.0 * item["total_bytes"] / grand_total, 1) if grand_total else 0.0
        )

    return {
        "rows_considered": total_rows,
        "rows_instrumented": instrumented,
        "rows_uninstrumented": total_rows - instrumented,
        "rows_excluded": excluded_rows,
        "excluded_patterns": list(exclude),
        "total_bytes": grand_total,
        "est_tokens": tokens(grand_total),
        "hooks": ranked,
    }


def print_hook_report(report: dict, top: int) -> None:
    print("=" * 96)
    print("HOOK OUTPUT — bytes each hook injects into context")
    print("=" * 96)
    considered = report["rows_considered"]
    instrumented = report["rows_instrumented"]
    coverage = 100.0 * instrumented / considered if considered else 0.0
    print(
        f"rows: {considered} considered | {instrumented} instrumented "
        f"({coverage:.1f}%) | {report['rows_uninstrumented']} predate the "
        f"stdout/stderr fields"
    )
    if report.get("rows_excluded"):
        print(
            f"excluded: {report['rows_excluded']} rows matching "
            f"{report['excluded_patterns']}"
        )
    if instrumented == 0:
        print()
        print("  No instrumented rows yet. scripts/hook-timing-wrapper.sh records")
        print("  stdout_bytes/stderr_bytes from the moment it landed; older rows in")
        print("  hook-timing.jsonl carry duration and exit code only. Re-run after a")
        print("  few tool calls.")
        print()
        return
    print(
        f"total: {human(report['total_bytes'])} bytes "
        f"(~{human(report['est_tokens'])} tokens at {CHARS_PER_TOKEN} chars/token)"
    )
    print()
    header = (
        f"{'#':>3}  {'hook':<34} {'inv':>6} {'stdout':>10} {'stderr':>9} "
        f"{'B/inv':>9} {'peak':>9} {'silent':>7} {'share':>7}"
    )
    print(header)
    print("-" * len(header))
    for index, item in enumerate(report["hooks"][:top], start=1):
        print(
            f"{index:>3}  {item['hook'][:34]:<34} {item['invocations']:>6} "
            f"{human(item['stdout_bytes']):>10} {human(item['stderr_bytes']):>9} "
            f"{item['bytes_per_invocation']:>9.1f} "
            f"{human(item['max_stdout_bytes']):>9} "
            f"{item['silent_pct']:>6.0f}% {item['share_pct']:>6.1f}%"
        )
    remaining = len(report["hooks"]) - top
    if remaining > 0:
        print(f"     ... {remaining} more hooks below the cut")
    print()
    print("  B/inv  = bytes injected per invocation (stdout + stderr)")
    print("  peak   = largest single stdout payload observed")
    print("  silent = share of invocations that injected nothing")
    print()
    print("  Read the ranking with one distinction in mind: PostToolUse hooks that")
    print("  rewrite the payload (result-truncator) re-emit the tool result itself,")
    print("  so their stdout is the tool output flowing through, not new text the")
    print("  hook invented. Advisory hooks emit only what they chose to say.")
    print()


# ── Section: tool output ────────────────────────────────────────────────────


def build_tool_report(rows: list[dict], since_epoch: float) -> dict:
    by_method: dict[str, dict] = {}
    by_tool: dict[str, dict] = {}
    biggest: list[dict] = []
    total_original = 0
    total_kept = 0
    count = 0

    for row in rows:
        if since_epoch and parse_timestamp(row.get("timestamp", "")) < since_epoch:
            continue
        original = int(row.get("original_chars") or 0)
        kept = int(row.get("truncated_chars") or 0)
        if original <= 0:
            continue
        count += 1
        total_original += original
        total_kept += kept
        saved = original - kept

        # Events written by the head+tail fallback carry no `method` key; they
        # are identifiable by the head_chars/tail_chars pair the branch logs.
        method = str(row.get("method") or ("head_tail" if "head_chars" in row else "unknown"))
        tool = str(row.get("tool") or ("Bash" if row.get("command") else "unknown"))

        for bucket, key in ((by_method, method), (by_tool, tool)):
            entry = bucket.setdefault(
                key, {"key": key, "events": 0, "original_chars": 0, "kept_chars": 0}
            )
            entry["events"] += 1
            entry["original_chars"] += original
            entry["kept_chars"] += kept

        biggest.append(
            {
                "timestamp": row.get("timestamp", ""),
                "method": method,
                "tool": tool,
                "original_chars": original,
                "kept_chars": kept,
                "saved_chars": saved,
                "command": (str(row.get("command") or "").strip().replace("\n", " ⏎ "))[:70],
            }
        )

    def finish(bucket: dict[str, dict]) -> list[dict]:
        out = []
        for entry in bucket.values():
            saved = entry["original_chars"] - entry["kept_chars"]
            out.append(
                {
                    **entry,
                    "saved_chars": saved,
                    "est_tokens_saved": tokens(saved),
                    "reduction_pct": (
                        round(100.0 * saved / entry["original_chars"], 1)
                        if entry["original_chars"]
                        else 0.0
                    ),
                }
            )
        out.sort(key=lambda item: -item["saved_chars"])
        return out

    biggest.sort(key=lambda item: -item["saved_chars"])
    saved_total = total_original - total_kept

    return {
        "events": count,
        "original_chars": total_original,
        "kept_chars": total_kept,
        "saved_chars": saved_total,
        "est_tokens_saved": tokens(saved_total),
        "reduction_pct": round(100.0 * saved_total / total_original, 1) if total_original else 0.0,
        "by_method": finish(by_method),
        "by_tool": finish(by_tool),
        "biggest_events": biggest[:20],
    }


def print_tool_report(report: dict, top: int) -> None:
    print("=" * 96)
    print("TOOL OUTPUT — what result-truncator kept out of context")
    print("=" * 96)
    if report["events"] == 0:
        print()
        print("  No truncation events in range. result-truncator only fires when a")
        print("  tool_response exceeds tokens.result_truncation.max_chars.")
        print()
        return
    print(
        f"events: {report['events']} | "
        f"raw {human(report['original_chars'])} chars -> "
        f"kept {human(report['kept_chars'])} chars | "
        f"saved {human(report['saved_chars'])} chars "
        f"(~{human(report['est_tokens_saved'])} tokens, {report['reduction_pct']}% reduction)"
    )
    print()

    for title, key in (("by method", "by_method"), ("by tool", "by_tool")):
        header = (
            f"{title:<18} {'events':>7} {'raw':>10} {'kept':>10} "
            f"{'saved':>10} {'tokens':>9} {'cut':>7}"
        )
        print(header)
        print("-" * len(header))
        for item in report[key]:
            print(
                f"{item['key'][:18]:<18} {item['events']:>7} "
                f"{human(item['original_chars']):>10} {human(item['kept_chars']):>10} "
                f"{human(item['saved_chars']):>10} "
                f"{human(item['est_tokens_saved']):>9} {item['reduction_pct']:>6.1f}%"
            )
        print()

    header = f"{'#':>3}  {'saved':>9} {'method':<12} {'command / target':<62}"
    print("biggest single events")
    print(header)
    print("-" * len(header))
    for index, item in enumerate(report["biggest_events"][:top], start=1):
        label = item["command"] or item["tool"]
        print(f"{index:>3}  {human(item['saved_chars']):>9} {item['method'][:12]:<12} {label:<62}")
    print()


# ── Entry point ─────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rank hook output and tool output by context cost."
    )
    parser.add_argument(
        "--section", choices=["hooks", "tools", "all"], default="all", help="which section to print"
    )
    parser.add_argument("--top", type=int, default=20, help="rows per ranking (default 20)")
    parser.add_argument("--since", default="", help="time window, e.g. 90m / 24h / 7d")
    parser.add_argument(
        "--by-event", action="store_true", help="split hook rows by harness event"
    )
    parser.add_argument(
        "--exclude-hook",
        action="append",
        default=[],
        metavar="SUBSTRING",
        help="drop hooks whose name contains SUBSTRING (repeatable); "
        "use for synthetic probes left behind by benchmarks",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--project-dir", default="", help="override project root")
    parser.add_argument(
        "--timing-log", default="", help="override path to hook-timing.jsonl"
    )
    parser.add_argument(
        "--truncation-log", default="", help="override path to truncation-events.jsonl"
    )
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve() if args.project_dir else find_project_root()
    metrics = root / ".cognitive-os" / "metrics"
    timing_log = Path(args.timing_log) if args.timing_log else metrics / "hook-timing.jsonl"
    truncation_log = (
        Path(args.truncation_log) if args.truncation_log else metrics / "truncation-events.jsonl"
    )

    window = parse_since(args.since)
    since_epoch = (datetime.now(timezone.utc).timestamp() - window) if window else 0.0

    payload: dict = {
        "project_dir": str(root),
        "since": args.since or "all",
        "chars_per_token": CHARS_PER_TOKEN,
    }

    try:
        if args.section in ("hooks", "all"):
            payload["hooks"] = build_hook_report(
                load_jsonl(timing_log),
                since_epoch,
                args.by_event,
                tuple(args.exclude_hook),
            )
            payload["hooks"]["source"] = str(timing_log)
        if args.section in ("tools", "all"):
            payload["tools"] = build_tool_report(load_jsonl(truncation_log), since_epoch)
            payload["tools"]["source"] = str(truncation_log)
    except OSError as exc:
        print(f"context_injection_report: cannot read metrics: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print()
    print(f"project: {root}")
    print(f"window:  {args.since or 'all recorded history'}")
    print()
    if "hooks" in payload:
        print_hook_report(payload["hooks"], args.top)
    if "tools" in payload:
        print_tool_report(payload["tools"], args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
