#!/usr/bin/env python3
"""cos-work-queue — CLI for the work-queue event log (.cognitive-os/work-queue.jsonl).

Commands:
  list          Print all entries (newest first by default)
  show <id>     Show full details for a specific entry by ID or index
  mark-done <id>  Mark an entry as done (adds done=true + done_at timestamp)

Usage:
  python3 scripts/cos_work_queue.py list [--limit N] [--event TYPE]
  python3 scripts/cos_work_queue.py show <id>
  python3 scripts/cos_work_queue.py mark-done <id>
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _queue_path(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "work-queue.jsonl"


def _load_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def _save_entries(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, separators=(",", ":")) for e in entries]
    path.write_text("\n".join(lines) + "\n" if lines else "")


def _find_project_dir() -> Path:
    cwd = Path.cwd()
    candidate = cwd
    while candidate != candidate.parent:
        if (candidate / ".git").exists():
            return candidate
        candidate = candidate.parent
    return cwd


def cmd_list(path: Path, limit: int | None, event_filter: str | None) -> None:
    entries = _load_entries(path)
    if event_filter:
        entries = [e for e in entries if e.get("event") == event_filter]
    # newest first
    entries = sorted(entries, key=lambda e: e.get("epoch", 0), reverse=True)
    if limit:
        entries = entries[:limit]
    if not entries:
        print("No entries found.")
        return
    print(f"{'#':<4} {'timestamp':<22} {'event':<20} {'done':<6} detail")
    print("-" * 80)
    for i, e in enumerate(entries):
        done_mark = "yes" if e.get("done") else ""
        detail = str(e.get("detail", ""))[:50]
        ts = e.get("timestamp", "")[:19]
        print(f"{i:<4} {ts:<22} {e.get('event',''):<20} {done_mark:<6} {detail}")


def cmd_show(path: Path, id_or_index: str) -> None:
    entries = _load_entries(path)
    # Try by index first
    try:
        idx = int(id_or_index)
        # newest-first order to match `list`
        entries_sorted = sorted(entries, key=lambda e: e.get("epoch", 0), reverse=True)
        if 0 <= idx < len(entries_sorted):
            print(json.dumps(entries_sorted[idx], indent=2))
            return
    except ValueError:
        pass
    # Try by id field
    for e in entries:
        if e.get("id") == id_or_index:
            print(json.dumps(e, indent=2))
            return
    print(f"Entry not found: {id_or_index}", file=sys.stderr)
    sys.exit(1)


def cmd_mark_done(path: Path, id_or_index: str) -> None:
    entries = _load_entries(path)
    entries_sorted = sorted(entries, key=lambda e: e.get("epoch", 0), reverse=True)

    target_entry = None
    try:
        idx = int(id_or_index)
        if 0 <= idx < len(entries_sorted):
            target_entry = entries_sorted[idx]
    except ValueError:
        for e in entries:
            if e.get("id") == id_or_index:
                target_entry = e
                break

    if target_entry is None:
        print(f"Entry not found: {id_or_index}", file=sys.stderr)
        sys.exit(1)

    # If no id field, assign one so we can key on it
    if "id" not in target_entry:
        target_entry["id"] = str(uuid.uuid4())

    target_id = target_entry["id"]

    # Update in original entries list
    updated = False
    for e in entries:
        if e.get("id") == target_id or (e is target_entry):
            e["done"] = True
            e["done_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            updated = True
            break

    if not updated:
        # Fallback: match by epoch + event
        for e in entries:
            if e.get("epoch") == target_entry.get("epoch") and e.get("event") == target_entry.get("event"):
                e["done"] = True
                e["done_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if "id" not in e:
                    e["id"] = target_id
                updated = True
                break

    if updated:
        _save_entries(path, entries)
        print(f"Marked done: {target_entry.get('event', '')} @ {target_entry.get('timestamp', '')}")
    else:
        print("Could not update entry.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI for .cognitive-os/work-queue.jsonl"
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Project root (default: git root or cwd)",
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List entries")
    p_list.add_argument("--limit", type=int, default=None, help="Max entries to show")
    p_list.add_argument("--event", default=None, help="Filter by event type")

    p_show = sub.add_parser("show", help="Show a single entry")
    p_show.add_argument("id", help="Entry ID or index (0-based, newest-first)")

    p_done = sub.add_parser("mark-done", help="Mark an entry as done")
    p_done.add_argument("id", help="Entry ID or index (0-based, newest-first)")

    args = parser.parse_args()

    if args.project_dir:
        project_dir = Path(args.project_dir).resolve()
    else:
        project_dir = _find_project_dir()

    path = _queue_path(project_dir)

    if args.command == "list":
        cmd_list(path, args.limit, args.event)
    elif args.command == "show":
        cmd_show(path, args.id)
    elif args.command == "mark-done":
        cmd_mark_done(path, args.id)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
