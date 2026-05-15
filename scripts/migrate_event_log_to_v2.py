#!/usr/bin/env python3
# SCOPE: os-only
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.session_bus import append_session_event, read_session_events  # noqa: E402


def _legacy_path(project: Path) -> Path:
    return project / ".cognitive-os" / "sessions" / "events.jsonl"


def migrate(project: Path, *, execute: bool = False) -> dict[str, object]:
    path = _legacy_path(project)
    rows: list[dict] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                rows.append(event)

    migrated = 0
    skipped_existing = 0
    sessions = sorted({str(row.get("session_id") or "unknown") for row in rows if row.get("session_id")})
    if execute:
        for row in rows:
            sid = str(row.get("session_id") or "unknown")
            if sid in {"", "unknown"}:
                continue
            existing = read_session_events(sid, project_dir=project)
            # Idempotency: if a target stream already has at least as many events
            # as the legacy stream slice for this session, do not append again.
            legacy_count_for_session = sum(1 for item in rows if str(item.get("session_id") or "unknown") == sid)
            if len(existing) >= legacy_count_for_session:
                skipped_existing += 1
                continue
            append_session_event(
                str(row.get("event_type") or "legacy-event"),
                row.get("payload") if isinstance(row.get("payload"), dict) else {"legacy_event": row},
                project_dir=project,
                session_id=sid,
            )
            migrated += 1
    return {
        "schema_version": "event-log-v1-to-v2-migration/v1",
        "legacy_path": str(path),
        "legacy_events": len(rows),
        "sessions": sessions,
        "execute": execute,
        "migrated": migrated,
        "skipped_existing": skipped_existing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate ADR-205 legacy global event log into ADR-226 per-session streams.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = migrate(Path(args.project_dir).resolve(), execute=args.execute)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        sessions = payload.get("sessions", [])
        session_count = len(sessions) if isinstance(sessions, list) else 0
        print(f"legacy_events={payload['legacy_events']} migrated={payload['migrated']} sessions={session_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
