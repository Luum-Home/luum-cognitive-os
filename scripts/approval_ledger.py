#!/usr/bin/env python3
# SCOPE: both
"""Append-only approval ledger for high-risk concurrent-agent actions."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.concurrency_safety import project_runtime_dir

def project_dir(args: argparse.Namespace) -> Path:
    value = args.project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).resolve()

def ledger_path(project: Path) -> Path:
    path = project_runtime_dir(project) / "approval-ledger.jsonl"; path.parent.mkdir(parents=True, exist_ok=True); return path

def read_events(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def record(args: argparse.Namespace) -> int:
    timestamp = time.time(); base = f"{args.category}|{args.scope}|{args.approved_by}|{timestamp}".encode()
    event = {"event": "approval", "approval_id": hashlib.sha256(base).hexdigest()[:16], "category": args.category, "scope": args.scope, "reason": args.reason, "approved_by": args.approved_by, "verification_command": args.verification_command, "rollback_plan": args.rollback_plan, "timestamp": timestamp}
    with ledger_path(project_dir(args)).open("a", encoding="utf-8") as fh: fh.write(json.dumps(event, sort_keys=True) + "\n")
    print(json.dumps({"status": "recorded", "approval": event}, sort_keys=True)); return 0

def list_events(args: argparse.Namespace) -> int:
    print(json.dumps({"approvals": read_events(ledger_path(project_dir(args)))}, sort_keys=True)); return 0

def require(args: argparse.Namespace) -> int:
    approvals = read_events(ledger_path(project_dir(args)))
    matches = [event for event in approvals if event.get("category") == args.category and event.get("scope") == args.scope]
    if matches:
        print(json.dumps({"status": "approved", "approval": matches[-1]}, sort_keys=True)); return 0
    print(json.dumps({"status": "missing", "category": args.category, "scope": args.scope}, sort_keys=True)); return 2

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--project-dir"); sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record"); rec.add_argument("--category", required=True); rec.add_argument("--scope", required=True); rec.add_argument("--reason", required=True); rec.add_argument("--approved-by", required=True); rec.add_argument("--verification-command", required=True); rec.add_argument("--rollback-plan", required=True); rec.set_defaults(func=record)
    ls = sub.add_parser("list"); ls.set_defaults(func=list_events)
    req = sub.add_parser("require"); req.add_argument("--category", required=True); req.add_argument("--scope", required=True); req.set_defaults(func=require)
    return parser

def main() -> int:
    args = build_parser().parse_args(); return int(args.func(args))
if __name__ == "__main__": raise SystemExit(main())
