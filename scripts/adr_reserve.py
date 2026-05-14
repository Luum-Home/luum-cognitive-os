#!/usr/bin/env python3
# SCOPE: os-only
"""Reserve ADR numbers atomically across concurrent COS sessions."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ADR_RE = re.compile(r"^ADR-(\d{3})")


@dataclass(frozen=True)
class Reservation:
    number: int
    adr_id: str
    title: str
    slug: str
    session_id: str
    owner: str
    expires_at: str
    path: str


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"reservations": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"reservations": []}
    if not isinstance(data, dict):
        return {"reservations": []}
    if not isinstance(data.get("reservations"), list):
        data["reservations"] = []
    return data


def existing_adr_numbers(adrs_dir: Path) -> set[int]:
    numbers: set[int] = set()
    if not adrs_dir.exists():
        return numbers
    for path in adrs_dir.iterdir():
        match = ADR_RE.match(path.name)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def active_reservations(data: dict[str, object], now: datetime) -> list[dict[str, object]]:
    active: list[dict[str, object]] = []
    for item in data.get("reservations", []):
        if not isinstance(item, dict):
            continue
        expires = parse_iso(str(item.get("expires_at", "")))
        if expires and expires > now:
            active.append(item)
    return active


def next_number(used: set[int]) -> int:
    return max(used, default=0) + 1


def reserve(
    *,
    project_dir: Path,
    title: str,
    session_id: str,
    owner: str,
    ttl_seconds: int,
    adrs_dir: Path | None = None,
    reservations_path: Path | None = None,
) -> Reservation:
    adrs_dir = adrs_dir or project_dir / "docs" / "02-Decisions" / "adrs"
    reservations_path = reservations_path or project_dir / ".cognitive-os" / "locks" / "adr-reservations.json"
    reservations_path.parent.mkdir(parents=True, exist_ok=True)
    adrs_dir.mkdir(parents=True, exist_ok=True)
    lock_path = reservations_path.with_suffix(reservations_path.suffix + ".lock")

    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        now = utc_now()
        data = load_json(reservations_path)
        active = active_reservations(data, now)
        used = existing_adr_numbers(adrs_dir)
        for item in active:
            number = item.get("number")
            try:
                used.add(int(number))
            except Exception:
                continue
        number = next_number(used)
        slug = slugify(title)
        adr_id = f"ADR-{number:03d}"
        expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc).isoformat()
        rel_path = f"docs/02-Decisions/adrs/{adr_id}-{slug}.md"
        record = {
            "number": number,
            "adr_id": adr_id,
            "title": title,
            "slug": slug,
            "session_id": session_id,
            "owner": owner,
            "reserved_at": now.isoformat(),
            "expires_at": expires_at,
            "path": rel_path,
        }
        data["reservations"] = [*active, record]
        tmp = reservations_path.with_suffix(reservations_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, reservations_path)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return Reservation(
        number=number,
        adr_id=adr_id,
        title=title,
        slug=slug,
        session_id=session_id,
        owner=owner,
        expires_at=expires_at,
        path=rel_path,
    )



def reservation_payload(reservation: Reservation) -> dict[str, object]:
    return {
        "number": reservation.number,
        "adr_id": reservation.adr_id,
        "title": reservation.title,
        "slug": reservation.slug,
        "session_id": reservation.session_id,
        "owner": reservation.owner,
        "expires_at": reservation.expires_at,
        "path": reservation.path,
    }


def reservation_status(item: dict[str, object], *, project_dir: Path, now: datetime | None = None) -> str:
    now = now or utc_now()
    expires = parse_iso(str(item.get("expires_at", "")))
    path = project_dir / str(item.get("path", ""))
    if path.exists():
        return "fulfilled"
    if expires and expires <= now:
        return "expired"
    return "active"


def list_reservations(*, project_dir: Path, reservations_path: Path | None = None, include_expired: bool = True) -> list[dict[str, object]]:
    reservations_path = reservations_path or project_dir / ".cognitive-os" / "locks" / "adr-reservations.json"
    data = load_json(reservations_path)
    now = utc_now()
    rows: list[dict[str, object]] = []
    for item in data.get("reservations", []):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        status = reservation_status(row, project_dir=project_dir, now=now)
        if not include_expired and status == "expired":
            continue
        row["status"] = status
        rows.append(row)
    return rows


def cleanup_expired(*, project_dir: Path, reservations_path: Path | None = None) -> dict[str, object]:
    reservations_path = reservations_path or project_dir / ".cognitive-os" / "locks" / "adr-reservations.json"
    reservations_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = reservations_path.with_suffix(reservations_path.suffix + ".lock")
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        data = load_json(reservations_path)
        kept: list[dict[str, object]] = []
        removed: list[dict[str, object]] = []
        now = utc_now()
        for item in data.get("reservations", []):
            if not isinstance(item, dict):
                continue
            status = reservation_status(item, project_dir=project_dir, now=now)
            item = dict(item)
            item["status"] = status
            if status == "expired":
                removed.append(item)
            else:
                kept.append(item)
        data["reservations"] = kept
        tmp = reservations_path.with_suffix(reservations_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, reservations_path)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return {"kept": kept, "removed": removed, "removed_count": len(removed)}


def current_session() -> str:
    return (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or "unknown"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reserve, list, or clean ADR number reservations atomically")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--title", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--owner", default=None)
    parser.add_argument("--ttl-seconds", type=int, default=86400)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_reservations")
    parser.add_argument("--cleanup-expired", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()
    if args.cleanup_expired:
        payload = cleanup_expired(project_dir=project_dir)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"removed {payload['removed_count']} expired ADR reservations")
        return 0
    if args.list_reservations:
        payload = {"reservations": list_reservations(project_dir=project_dir)}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for item in payload["reservations"]:
                print(f"{item.get('adr_id')} {item.get('status')} {item.get('path')} session={item.get('session_id')}")
        return 0
    if not args.title:
        raise SystemExit("--title is required unless --list or --cleanup-expired is used")
    reservation = reserve(
        project_dir=project_dir,
        title=args.title,
        session_id=args.session_id or current_session(),
        owner=args.owner or os.environ.get("USER", "unknown"),
        ttl_seconds=args.ttl_seconds,
    )
    payload = reservation_payload(reservation)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{reservation.adr_id} reserved for {reservation.title}: {reservation.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
