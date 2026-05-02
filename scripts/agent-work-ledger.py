#!/usr/bin/env python3
# SCOPE: both
"""Append-only ledger for concurrent agent work claims."""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.concurrency_safety import project_runtime_dir

def project_dir(args: argparse.Namespace) -> Path:
    value = args.project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).resolve()

def ledger_path(project: Path) -> Path:
    path = project_runtime_dir(project) / "agent-work-ledger.jsonl"; path.parent.mkdir(parents=True, exist_ok=True); return path

def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        try: events.append(json.loads(line))
        except json.JSONDecodeError: events.append({"event": "corrupt-line", "raw": line})
    return events

def record(args: argparse.Namespace) -> int:
    project = project_dir(args)
    event = {"event": "agent-work", "agent_id": args.agent_id, "session_id": args.session_id, "task": args.task, "status": args.status, "scopes": args.scope, "timestamp": time.time()}
    with ledger_path(project).open("a", encoding="utf-8") as fh: fh.write(json.dumps(event, sort_keys=True) + "\n")
    print(json.dumps({"status": "recorded", "event": event}, sort_keys=True)); return 0

def list_events(args: argparse.Namespace) -> int:
    print(json.dumps({"events": read_events(ledger_path(project_dir(args)))}, sort_keys=True)); return 0

def summary(args: argparse.Namespace) -> int:
    events = read_events(ledger_path(project_dir(args))); active: dict[str, dict[str, Any]] = {}
    for event in events:
        key = f"{event.get('agent_id')}::{event.get('session_id')}::{event.get('task')}"
        if event.get("status") == "started": active[key] = event
        elif event.get("status") in {"completed", "aborted"}: active.pop(key, None)
    print(json.dumps({"total_events": len(events), "active_work": list(active.values())}, sort_keys=True)); return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--project-dir"); sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record"); rec.add_argument("--agent-id", required=True); rec.add_argument("--session-id", required=True); rec.add_argument("--task", required=True); rec.add_argument("--status", choices=("started", "completed", "aborted"), required=True); rec.add_argument("--scope", action="append", required=True); rec.set_defaults(func=record)
    ls = sub.add_parser("list"); ls.set_defaults(func=list_events)
    sm = sub.add_parser("summary"); sm.set_defaults(func=summary)
    return parser

def main() -> int:
    args = build_parser().parse_args(); return int(args.func(args))
if __name__ == "__main__": raise SystemExit(main())
