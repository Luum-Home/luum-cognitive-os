#!/usr/bin/env python3
# SCOPE: both
"""Summarize the cross-session task event bus.

JSONL contract (one object per line):
  {
    "ts": "2026-05-20T12:00:00Z",      # ISO timestamp, optional for old rows
    "session": "worker-a",              # emitting session id
    "event": "claim|complete|conflict", # required canonical event name
    "payload": {                         # event-specific body
      "task_id": "task-123",
      "fingerprint": "...",
      "held_by": "other-session",
      "expected_files": ["scripts/foo.py"]
    }
  }

The watcher is intentionally read-only: corrupt JSONL rows are ignored, evidence
is preserved in the source log, and the output is a current projection of claims,
completions, and conflicts for recovery/status surfaces.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cos_task_claims import events_path, project_dir

WATCHED_EVENTS = {"claim", "complete", "conflict"}


@dataclass
class EventProjection:
    current_claims: dict[str, dict[str, Any]] = field(default_factory=dict)
    completions: dict[str, dict[str, Any]] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    event_counts: dict[str, int] = field(default_factory=lambda: {name: 0 for name in WATCHED_EVENTS})
    skipped_lines: int = 0

    def ingest(self, row: dict[str, Any]) -> None:
        event = str(row.get("event") or row.get("event_type") or "")
        if event not in WATCHED_EVENTS:
            return
        self.event_counts[event] = self.event_counts.get(event, 0) + 1
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        session = str(row.get("session") or row.get("session_id") or payload.get("session_id") or "")
        task_id = str(payload.get("task_id") or payload.get("id") or "")
        fingerprint = str(payload.get("fingerprint") or "")
        key = task_id or fingerprint or f"line-{sum(self.event_counts.values())}"
        envelope = {"ts": row.get("ts"), "session": session, "payload": payload}
        if event == "claim":
            self.current_claims[key] = envelope
        elif event == "complete":
            self.completions[key] = envelope
            self.current_claims.pop(key, None)
        elif event == "conflict":
            self.conflicts.append(envelope)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any] | None]:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            yield None
            continue
        yield row if isinstance(row, dict) else None


def summarize_events(path: Path) -> EventProjection:
    projection = EventProjection()
    for row in iter_jsonl(path):
        if row is None:
            projection.skipped_lines += 1
            continue
        projection.ingest(row)
    return projection


def format_text(projection: EventProjection) -> str:
    lines = [
        "task-event-watcher:",
        f"- current_claims: {len(projection.current_claims)}",
        f"- completions: {len(projection.completions)}",
        f"- conflicts: {len(projection.conflicts)}",
        f"- skipped_lines: {projection.skipped_lines}",
    ]
    for task_id, claim in sorted(projection.current_claims.items()):
        payload = claim.get("payload", {})
        lines.append(f"  claim {task_id}: session={claim.get('session') or '-'} files={','.join(payload.get('expected_files') or []) or '-'}")
    for task_id, complete in sorted(projection.completions.items()):
        lines.append(f"  complete {task_id}: session={complete.get('session') or '-'}")
    for conflict in projection.conflicts:
        payload = conflict.get("payload", {})
        lines.append(f"  conflict {payload.get('task_id') or payload.get('fingerprint') or '-'}: held_by={payload.get('held_by') or '-'} session={conflict.get('session') or '-'}")
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--events-file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--schema", action="store_true", help="Print the JSONL contract and exit.")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.schema:
        print(__doc__.strip())
        return 0
    project = project_dir(args)
    path = Path(args.events_file).resolve() if args.events_file else events_path(project)
    projection = summarize_events(path)
    if args.json:
        print(json.dumps(asdict(projection), indent=2, sort_keys=True))
    else:
        print(format_text(projection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
