#!/usr/bin/env python3
"""so_session_watchdog.py — Phase A (log-only) session lifecycle daemon.

ADR-047 Phase A implementation.  Observes Claude Code sessions and logs
classification results to .cognitive-os/metrics/session-watchdog.jsonl.
NEVER sends signals.  Phase B (enforce) is a follow-up PR.

Usage:
    python3 scripts/so_session_watchdog.py --once
    python3 scripts/so_session_watchdog.py --daemon [--interval 60]
    python3 scripts/so_session_watchdog.py --help

Opt-out:
    COS_SESSION_WATCHDOG_DISABLE=1  → exit 0 silently, write nothing.

Feature flags (cognitive-os.yaml  runtime.session_watchdog):
    enabled: true|false         default true
    mode: "log-only"|"enforce"|"off"   default "log-only"
    ttl_hours: 6                default 6.0
    idle_cpu_threshold: 1.0     default 1.0  (percent)
    idle_samples_required: 3    default 3
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional

# ---------------------------------------------------------------------------
# Path wiring — ensure lib/ is importable regardless of CWD
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent


def _find_project_root() -> Path:
    """Prefer env var, fall back to parent of scripts/."""
    env = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return _PROJECT_ROOT


PROJECT_ROOT = _find_project_root()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.session_watchdog_lib import (  # noqa: E402
    WatchdogRecord,
    append_jsonl,
    classify_session,
    compute_gate_metric,
    enrich_session,
    load_watchdog_config,
    load_watchdog_jsonl,
    should_kill,
    _enumerate_via_ps,
    _enumerate_via_psutil,
    _try_import_psutil,
)

# Re-export so callers can do: from scripts.so_session_watchdog import should_kill
__all__ = ["should_kill", "run_once", "run_daemon", "run_scan", "evaluate_gate"]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

METRICS_DIR = PROJECT_ROOT / ".cognitive-os" / "metrics"
WATCHDOG_JSONL = METRICS_DIR / "session-watchdog.jsonl"

# ---------------------------------------------------------------------------
# Core scan logic
# ---------------------------------------------------------------------------


def run_scan(config: dict) -> List[WatchdogRecord]:
    """Enumerate sessions, classify each, return records (do NOT write JSONL)."""
    psutil = _try_import_psutil()
    if psutil is not None:
        sessions_raw, engram_procs = _enumerate_via_psutil(psutil)
    else:
        sessions_raw, engram_procs = _enumerate_via_ps()

    ttl_sec = int(float(config.get("ttl_hours", 6.0)) * 3600)
    idle_cpu = float(config.get("idle_cpu_threshold", 1.0))
    ttl_hours_cfg = float(config.get("ttl_hours", 6.0))

    scan_id = str(uuid.uuid4())
    now_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    records: List[WatchdogRecord] = []
    for raw in sessions_raw:
        session = enrich_session(raw, engram_procs)
        classification, reason, would_kill = classify_session(
            session, ttl_sec, idle_cpu
        )
        records.append(
            WatchdogRecord(
                timestamp=now_str,
                scan_id=scan_id,
                session_pid=session.pid,
                session_etime_sec=session.etime_sec,
                classification=classification,
                would_kill=would_kill,
                reason=reason,
                resume_id=session.resume_id,
                engram_mcp_children=session.engram_mcp_children,
                cpu_percent=session.cpu_percent,
                ttl_hours_configured=ttl_hours_cfg,
            )
        )

    return records


def write_records(records: List[WatchdogRecord]) -> None:
    """Append all records to the JSONL metrics file."""
    for rec in records:
        append_jsonl(WATCHDOG_JSONL, rec.to_dict())


# ---------------------------------------------------------------------------
# One-shot and daemon entry points
# ---------------------------------------------------------------------------


def evaluate_gate(jsonl_path: Optional[Path] = None) -> "Any":
    """Compute the Phase B gate metric from the current JSONL record stream.

    Resolves the JSONL path AT CALL TIME (reads module global WATCHDOG_JSONL)
    so that tests monkey-patching `WATCHDOG_JSONL` via `patch.object` are
    honored. Callers may pass an explicit path to override.

    Returns a GateMetric dataclass. Callers use `.gate_passes` to decide
    whether Phase B enforcement may be enabled.
    """
    if jsonl_path is None:
        jsonl_path = WATCHDOG_JSONL
    records = load_watchdog_jsonl(jsonl_path)
    return compute_gate_metric(records)


def run_once(config: dict, verbose: bool = False, kill_mode: bool = False) -> int:
    """Single scan pass.  Returns exit code.

    Parameters
    ----------
    kill_mode:
        If True, caller requested Phase B enforcement. The function evaluates
        the gate metric first. If the gate FAILS, the request is refused,
        an explanation is printed to stderr, and the function falls back to
        log-only behavior. This is the primary Phase B safety rail: even if
        someone edits `cognitive-os.yaml` to set `mode: enforce`, enforcement
        will NOT activate until the gate passes.
    """
    mode = config.get("mode", "log-only")

    if mode == "off":
        if verbose:
            print("[watchdog] mode=off — skipping scan.", file=sys.stderr)
        return 0

    # Phase B gate: evaluate before any kill authority is granted
    enforce_requested = kill_mode or mode == "enforce"
    if enforce_requested:
        gate = evaluate_gate()
        if not gate.gate_passes:
            print(
                f"[watchdog] Phase B REFUSED: gate metric fails — {gate.evidence_summary}",
                file=sys.stderr,
            )
            print(
                f"[watchdog]   total_records={gate.total_records} "
                f"flagged_records={gate.flagged_records} "
                f"fp_rate={gate.fp_rate*100:.2f}% "
                f"span={gate.observation_span_hours:.1f}h",
                file=sys.stderr,
            )
            print(
                "[watchdog]   falling back to log-only mode (no kills performed).",
                file=sys.stderr,
            )
            # Fall through to log-only — DO NOT kill
        else:
            # Gate passed — but kill logic is not yet implemented. Fail safe.
            print(
                f"[watchdog] Phase B gate PASSED ({gate.evidence_summary}) but kill implementation "
                "is not yet wired. Staying in log-only mode. See ADR-047 §'Phase B'.",
                file=sys.stderr,
            )

    records = run_scan(config)
    write_records(records)

    if verbose:
        psutil_avail = _try_import_psutil() is not None
        print(
            f"[watchdog] scan complete: {len(records)} session(s) found "
            f"(psutil={'yes' if psutil_avail else 'no, using ps fallback'}).",
            file=sys.stderr,
        )
        for r in records:
            wk = "would_kill=YES" if r.would_kill else "would_kill=no"
            print(
                f"  pid={r.session_pid} etime={r.session_etime_sec}s "
                f"class={r.classification} {wk} reason={r.reason}",
                file=sys.stderr,
            )

    return 0


def run_daemon(config: dict, interval_sec: int, verbose: bool = False) -> int:
    """Loop every interval_sec seconds.  Handles KeyboardInterrupt gracefully."""
    if verbose:
        print(f"[watchdog] starting daemon mode (interval={interval_sec}s).", file=sys.stderr)

    while True:
        try:
            # Reload config on every pass so flag changes take effect live.
            config = load_watchdog_config(PROJECT_ROOT)
            if config.get("enabled", True) is False:
                if verbose:
                    print("[watchdog] enabled=false — sleeping.", file=sys.stderr)
                time.sleep(interval_sec)
                continue
            run_once(config, verbose=verbose)
        except KeyboardInterrupt:
            if verbose:
                print("[watchdog] interrupted — exiting.", file=sys.stderr)
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"[watchdog] scan error: {exc}", file=sys.stderr)

        time.sleep(interval_sec)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="so_session_watchdog.py",
        description=(
            "ADR-047 Phase A session lifecycle watchdog.\n"
            "Observes Claude Code sessions, logs classifications to\n"
            "  .cognitive-os/metrics/session-watchdog.jsonl\n"
            "NEVER kills processes in Phase A (log-only mode).\n\n"
            "Opt-out: set COS_SESSION_WATCHDOG_DISABLE=1"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode_group = p.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Single scan pass, write records, exit.",
    )
    mode_group.add_argument(
        "--daemon",
        action="store_true",
        help="Loop every --interval seconds (default 60).",
    )
    mode_group.add_argument(
        "--gate-report",
        action="store_true",
        help="Compute Phase B gate metric from JSONL and print report; do NOT scan.",
    )
    p.add_argument(
        "--kill-mode",
        action="store_true",
        help=(
            "Request Phase B enforcement. Requires gate metric to pass "
            "(fp_rate<1%%, sample>=50, 2-week span). If gate fails, the "
            "request is refused and watchdog falls back to log-only."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run: never actually send signals, even if kill_mode is set.",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Poll interval for daemon mode (default: 60).",
    )
    p.add_argument(
        "--project-root",
        type=Path,
        default=None,
        metavar="PATH",
        help="Override project root (default: auto-detect from script location).",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print scan summary to stderr.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    # Opt-out env var: exit 0 silently, write NOTHING.
    if os.environ.get("COS_SESSION_WATCHDOG_DISABLE", "").strip() == "1":
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    global PROJECT_ROOT, WATCHDOG_JSONL, METRICS_DIR
    if args.project_root is not None:
        PROJECT_ROOT = args.project_root.resolve()
        METRICS_DIR = PROJECT_ROOT / ".cognitive-os" / "metrics"
        WATCHDOG_JSONL = METRICS_DIR / "session-watchdog.jsonl"

    config = load_watchdog_config(PROJECT_ROOT)

    if config.get("enabled", True) is False and not args.daemon:
        if args.verbose:
            print("[watchdog] enabled=false in config — exiting.", file=sys.stderr)
        return 0

    if args.gate_report:
        gate = evaluate_gate()
        print(f"ADR-047 Phase B gate report")
        print(f"  JSONL: {WATCHDOG_JSONL}")
        print(f"  total_records: {gate.total_records}")
        print(f"  distinct_flagged_pids: {gate.distinct_flagged_pids}")
        print(f"  flagged_records (would_kill=true): {gate.flagged_records}")
        print(f"  resumed_within_24h (false positives): {gate.resumed_within_24h}")
        print(f"  stayed_idle (true positives): {gate.stayed_idle}")
        print(f"  fp_rate: {gate.fp_rate*100:.2f}% (threshold <1.00%)")
        print(f"  observation_span_hours: {gate.observation_span_hours:.2f} (threshold >=336h)")
        print(f"  sample_size_ok: {gate.sample_size_ok}")
        print(f"  fp_rate_ok: {gate.fp_rate_ok}")
        print(f"  observation_span_ok: {gate.observation_span_ok}")
        print(f"  GATE: {'PASS' if gate.gate_passes else 'FAIL'}")
        print(f"  summary: {gate.evidence_summary}")
        return 0 if gate.gate_passes else 2

    kill_mode = bool(args.kill_mode)
    if args.dry_run:
        # Dry-run forces no enforcement even if kill-mode was requested
        os.environ["SO_WATCHDOG_DRY_RUN"] = "1"

    if args.once:
        return run_once(config, verbose=args.verbose, kill_mode=kill_mode)
    else:
        return run_daemon(config, interval_sec=args.interval, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
