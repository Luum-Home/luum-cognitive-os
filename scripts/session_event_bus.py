#!/usr/bin/env python3
# SCOPE: both
"""Emit and inspect Cognitive OS inter-session coordination events."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from lib.session_bus import append_event, peers, read_events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    emit = sub.add_parser("emit")
    emit.add_argument("event_type")
    emit.add_argument("--session-id", default=None)
    emit.add_argument("--payload-json", default="{}")
    tail = sub.add_parser("tail")
    tail.add_argument("--limit", type=int, default=20)
    tail.add_argument("--event-type", default=None)
    peer_cmd = sub.add_parser("peers")
    peer_cmd.add_argument("--within-seconds", type=int, default=1800)
    peer_cmd.add_argument("--current-session-id", default=None)
    peer_cmd.add_argument("--include-dead", action="store_true")
    args = parser.parse_args()
    if args.cmd == "emit":
        payload = json.loads(args.payload_json)
        event = append_event(args.event_type, payload, project_dir=args.project_dir, session_id=args.session_id)
        print(json.dumps(event, sort_keys=True))
        return 0
    if args.cmd == "peers":
        for peer in peers(project_dir=args.project_dir, within_seconds=args.within_seconds, alive_only=not args.include_dead, current_session_id=args.current_session_id):
            print(json.dumps(peer.to_dict(), sort_keys=True))
        return 0
    events = read_events(project_dir=args.project_dir, limit=args.limit, event_type=args.event_type)
    for event in events:
        print(json.dumps(event, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
