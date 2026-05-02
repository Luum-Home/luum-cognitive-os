#!/usr/bin/env bash
# SCOPE: both
# scope: both
# cos-events.sh — CLI wrapper for the inter-session event bus (P1.3 / ADR-116).
#
# Usage:
#   bash scripts/cos-events.sh emit <event_type> --payload '<json>'
#   bash scripts/cos-events.sh tail [--follow] [--since <iso-ts>]
#   bash scripts/cos-events.sh stats [--window <seconds>]
#
# All heavy lifting is delegated to packages/agent-coordination/lib/event_bus.py
# (symlinked as lib/event_bus.py).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python3}"

_usage() {
  cat <<'EOF'
Usage: cos-events.sh <subcommand> [options]

Subcommands:
  emit <event_type> --payload '<json>'
        Append one event to the bus.
        event_type must be one of:
          claim_acquired  claim_released  task_completed
          commit_landed   session_started  session_ended  conflict_detected

  tail [--follow] [--since <iso-ts>] [--since-line <n>]
        Stream events from the bus.
        --follow     Keep watching for new events (like tail -f).
        --since      ISO-8601 timestamp; skip older events.
        --since-line Skip the first N lines.

  stats [--window <seconds>]
        Print per-event-type counts for the last <window> seconds (default 3600).

Options:
  --bus-path <path>   Override the default bus file path.
  --help, -h          Show this message.
EOF
}

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------

SUBCOMMAND="${1:-}"
shift || true

case "${SUBCOMMAND}" in
  emit|tail|stats) ;;
  --help|-h) _usage; exit 0 ;;
  "")
    echo "cos-events: subcommand required" >&2
    _usage >&2
    exit 2
    ;;
  *)
    echo "cos-events: unknown subcommand '${SUBCOMMAND}'" >&2
    _usage >&2
    exit 2
    ;;
esac

# --------------------------------------------------------------------------
# Delegate to Python
# --------------------------------------------------------------------------

exec "${PYTHON}" - "${SUBCOMMAND}" "$@" <<'PYEOF'
"""Inline Python driver invoked by cos-events.sh.

sys.argv[1] is the subcommand; the rest are forwarded arguments.
"""
import sys
import os
import argparse
import json

# Ensure the project lib is importable regardless of cwd.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
sys.path.insert(0, _repo_root)

from lib.event_bus import emit, tail, stats, EVENT_TYPES  # noqa: E402

subcommand = sys.argv[1]
args_raw = sys.argv[2:]

# ------------------------------------------------------------------
# emit
# ------------------------------------------------------------------
if subcommand == "emit":
    p = argparse.ArgumentParser(prog="cos-events emit")
    p.add_argument("event_type", help="Event type (see EVENT_TYPES)")
    p.add_argument("--payload", required=True, help="JSON payload string")
    p.add_argument("--session-id", default=None)
    p.add_argument("--bus-path", default=None)
    ns = p.parse_args(args_raw)

    try:
        payload_dict = json.loads(ns.payload)
    except json.JSONDecodeError as exc:
        print(f"cos-events: invalid JSON payload: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        emit(
            ns.event_type,
            payload_dict,
            session_id=ns.session_id,
            bus_path=ns.bus_path,
        )
    except ValueError as exc:
        print(f"cos-events: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"emitted: {ns.event_type}")
    sys.exit(0)

# ------------------------------------------------------------------
# tail
# ------------------------------------------------------------------
elif subcommand == "tail":
    p = argparse.ArgumentParser(prog="cos-events tail")
    p.add_argument("--follow", action="store_true")
    p.add_argument("--since", default=None, help="ISO-8601 timestamp")
    p.add_argument("--since-line", type=int, default=0)
    p.add_argument("--bus-path", default=None)
    ns = p.parse_args(args_raw)

    try:
        for event in tail(
            since_ts=ns.since,
            since_line=ns.since_line,
            follow=ns.follow,
            bus_path=ns.bus_path,
        ):
            print(json.dumps(event, ensure_ascii=False))
    except KeyboardInterrupt:
        pass
    sys.exit(0)

# ------------------------------------------------------------------
# stats
# ------------------------------------------------------------------
elif subcommand == "stats":
    p = argparse.ArgumentParser(prog="cos-events stats")
    p.add_argument("--window", type=float, default=3600.0,
                   help="Look-back window in seconds (default: 3600)")
    p.add_argument("--bus-path", default=None)
    ns = p.parse_args(args_raw)

    counts = stats(window_seconds=ns.window, bus_path=ns.bus_path)
    if not counts:
        print("(no events in window)")
    else:
        # Print sorted by count descending
        for event_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"{event_type:<22} {count}")
    sys.exit(0)

else:
    print(f"cos-events: unhandled subcommand '{subcommand}'", file=sys.stderr)
    sys.exit(2)
PYEOF
