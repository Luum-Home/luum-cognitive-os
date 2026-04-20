#!/usr/bin/env python3
"""Cognitive OS Orchestrator — dogfood entry point.

Launches sub-Claude agents via `lib.claude_executor.ClaudeExecutor`, which
publishes heartbeats on the agent_bus and is monitored by
`lib.agent_bus_metrics.AgentBusMetrics`. Every launch from this script:

  - registers on agent_bus (heartbeats visible to so-vitals, so-agent-status)
  - emits agent_launched / agent_completed MetricEvents to
    .cognitive-os/metrics/agent-heartbeat.jsonl
  - runs under ORCHESTRATOR_MODE=executor (auto-activated via AutoExecutor)
  - degrades to FallbackBus files when Valkey is not reachable

Usage:
    python3 scripts/orchestrator.py --task "Write a one-line summary of docs/adrs/ADR-028.md"
    echo "Write a greeting." | python3 scripts/orchestrator.py
    python3 scripts/orchestrator.py --task "..." --model sonnet --timeout 120
    python3 scripts/orchestrator.py --list-live   # show agents currently running
    python3 scripts/orchestrator.py --scan-stale  # show hung agents

Exit codes:
    0  task succeeded
    1  task failed or timed out
    2  misconfigured (bad args, executor unavailable)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# --- Helpers ----------------------------------------------------------------


def _short_id() -> str:
    """Short, unique agent id — first 8 hex chars of a uuid4."""
    return uuid.uuid4().hex[:8]


def _activate_executor_mode() -> dict:
    """Attempt to activate executor mode; return mode descriptor."""
    try:
        from lib.auto_executor import AutoExecutor

        return AutoExecutor.check_and_activate()
    except Exception as e:
        return {"mode": "degraded", "error": str(e), "valkey_available": False}


def _read_prompt_from_args_or_stdin(args: argparse.Namespace) -> str:
    if args.task:
        return args.task.strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


# --- Subcommands ------------------------------------------------------------


def cmd_list_live(args: argparse.Namespace) -> int:
    from lib.agent_bus_metrics import AgentBusMetrics

    abm = AgentBusMetrics()
    live = abm.list_live(max_age_seconds=args.max_age)
    if not live:
        print("No live agents.")
        return 0
    print(f"{'AGENT ID':<24} {'PHASE':<16} {'AGE(s)':>8}")
    for rec in live:
        print(f"{rec['agent_id']:<24} {(rec.get('last_phase') or '-'):<16} {int(rec['age_seconds']):>8}")
    return 0


def cmd_scan_stale(args: argparse.Namespace) -> int:
    from lib.agent_bus_metrics import AgentBusMetrics

    abm = AgentBusMetrics()
    stale = abm.scan_stale(max_age_seconds=args.max_age)
    if not stale:
        print("No stale agents.")
        return 0
    print(f"{'AGENT ID':<24} {'PHASE':<16} {'AGE(s)':>8}  STATE")
    for rec in stale:
        print(f"{rec['agent_id']:<24} {(rec.get('last_phase') or '-'):<16} {int(rec['age_seconds']):>8}  STALE")
    return 0


def cmd_kill_hung(args: argparse.Namespace) -> int:
    from lib.agent_bus_metrics import AgentBusMetrics

    abm = AgentBusMetrics()
    result = abm.mark_hung_and_publish(args.agent_id)
    print(f"marked hung: {result}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    prompt = _read_prompt_from_args_or_stdin(args)
    if not prompt:
        print("ERROR: no task provided. Pass --task or pipe via stdin.", file=sys.stderr)
        return 2

    # Activate executor mode (Valkey if available, fallback otherwise)
    mode = _activate_executor_mode()
    mode_label = mode.get("mode", "unknown")
    valkey = bool(mode.get("valkey_available"))
    if args.verbose:
        print(f"[orchestrator] executor mode={mode_label} valkey={valkey}", file=sys.stderr)

    # Build the agent id and wire up metrics bridge
    agent_id = args.agent_id or f"orch-{_short_id()}"
    os.environ.setdefault("COGNITIVE_OS_SESSION_ID", f"orchestrator-{agent_id}")

    try:
        from lib.agent_bus_metrics import AgentBusMetrics
        from lib.claude_executor import ClaudeExecutor
    except ImportError as e:
        print(f"ERROR: executor/adapter import failed: {e}", file=sys.stderr)
        return 2

    # Subscribe the adapter so heartbeats from the sub-claude flow into
    # .cognitive-os/metrics/agent-heartbeat.jsonl as MetricEvents.
    abm = AgentBusMetrics()
    if valkey:
        try:
            abm.subscribe()
            # subscribe() registers the callback; the underlying subscriber
            # must be told to listen in a background thread.
            if abm._subscriber and hasattr(abm._subscriber, "start"):
                abm._subscriber.start()
        except Exception as e:
            if args.verbose:
                print(f"[orchestrator] subscriber start failed: {e}", file=sys.stderr)

    # Launch the sub-claude. ClaudeExecutor's __init__ spawns an
    # AgentPublisher heartbeat thread when agent_id is provided.
    executor = ClaudeExecutor(
        agent_id=agent_id,
        default_model=args.model,
        default_timeout=args.timeout,
        verbose=args.verbose,
    )

    if args.verbose:
        print(f"[orchestrator] launching agent_id={agent_id} model={args.model or 'default'}", file=sys.stderr)

    t0 = time.monotonic()
    result = executor.run(prompt, model=args.model, timeout=args.timeout)
    elapsed = time.monotonic() - t0

    # Stop subscriber if we started one
    if abm._subscriber and hasattr(abm._subscriber, "stop"):
        try:
            abm._subscriber.stop()
        except Exception:
            pass

    # Report
    print(f"agent_id:    {agent_id}")
    print(f"success:     {result.success}")
    print(f"elapsed:     {elapsed:.2f}s")
    print(f"input_tok:   {getattr(result, 'input_tokens', 0)}")
    print(f"output_tok:  {getattr(result, 'output_tokens', 0)}")
    print(f"cost_usd:    {getattr(result, 'cost_usd', 0.0):.4f}")
    if getattr(result, "error", None):
        print(f"error:       {result.error}", file=sys.stderr)
    if args.show_text:
        print("---")
        print(getattr(result, "text", "") or "")

    return 0 if result.success else 1


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="orchestrator",
        description="Cognitive OS dogfood orchestrator: launch agents via ClaudeExecutor, "
                    "observe through agent_bus_metrics.",
    )
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("run", help="Launch a sub-claude agent (default)")
    r.add_argument("--task", "-t", help="Prompt text (or pipe via stdin).")
    r.add_argument("--model", "-m", default=None, help="Model shortname (opus/sonnet/haiku).")
    r.add_argument("--timeout", type=int, default=600, help="Timeout in seconds.")
    r.add_argument("--agent-id", default=None, help="Override agent id.")
    r.add_argument("--show-text", action="store_true", help="Print the agent's text output.")
    r.add_argument("--verbose", action="store_true")
    r.set_defaults(func=cmd_run)

    ll = sub.add_parser("list-live", help="List live agents (from agent_bus_metrics).")
    ll.add_argument("--max-age", type=int, default=300, help="Liveness threshold in seconds.")
    ll.set_defaults(func=cmd_list_live)

    ss = sub.add_parser("scan-stale", help="List stale agents.")
    ss.add_argument("--max-age", type=int, default=300, help="Staleness threshold in seconds.")
    ss.set_defaults(func=cmd_scan_stale)

    kh = sub.add_parser("kill-hung", help="Mark an agent as hung and publish stop signal.")
    kh.add_argument("agent_id")
    kh.set_defaults(func=cmd_kill_hung)

    # Top-level shortcuts: if no subcommand, default to `run` with remaining args.
    args, remaining = p.parse_known_args(argv)
    if not args.cmd:
        # Parse as `run`
        ns = r.parse_args(remaining)
        return cmd_run(ns)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
