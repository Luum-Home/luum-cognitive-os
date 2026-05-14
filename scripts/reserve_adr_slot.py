#!/usr/bin/env python3
# SCOPE: os-only
"""ADR-089 Layer 3 — ADR slot reservation entry point.

Thin CLI wrapper around the core adr_reserve module (scripts/adr_reserve.py).
Provides the interface specified by ADR-089:

    # Reserve next slot (prints slot number to stdout)
    python3 scripts/reserve_adr_slot.py

    # Reserve with a title
    python3 scripts/reserve_adr_slot.py --title "My Feature"

    # Release a slot
    python3 scripts/reserve_adr_slot.py --release 090

    # List in-flight reservations
    python3 scripts/reserve_adr_slot.py --list

    # Clean up expired reservations
    python3 scripts/reserve_adr_slot.py --cleanup

Reservation state lives in .cognitive-os/runtime/adr-reservations/ (gitignored
via the parent .cognitive-os/ exclusion in .gitignore).

TTL: 30 minutes (1800 seconds) by default.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

# ── Locate and import adr_reserve ─────────────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_ADR_RESERVE_PATH = _SCRIPTS_DIR / "adr_reserve.py"

if not _ADR_RESERVE_PATH.exists():
    print(f"ERROR: {_ADR_RESERVE_PATH} not found", file=sys.stderr)
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("adr_reserve", _ADR_RESERVE_PATH)
assert _spec and _spec.loader, f"Could not load {_ADR_RESERVE_PATH}"
_adr_reserve = importlib.util.module_from_spec(_spec)
sys.modules["adr_reserve"] = _adr_reserve
_spec.loader.exec_module(_adr_reserve)  # type: ignore[union-attr]

# ── Helpers ────────────────────────────────────────────────────────────────────

DEFAULT_TTL = 1800  # 30 minutes


def _project_dir(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "project_dir", ".")).resolve()


def _session_id() -> str:
    return (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or f"shell-{os.getppid()}"
    )


def _reservations_path(project_dir: Path) -> Path:
    """ADR-089 stores reservations under .cognitive-os/runtime/adr-reservations/."""
    return project_dir / ".cognitive-os" / "runtime" / "adr-reservations" / "reservations.json"


# ── Commands ───────────────────────────────────────────────────────────────────


def cmd_reserve(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args)
    title = args.title or "untitled"
    session_id = _session_id()
    ttl = getattr(args, "ttl", DEFAULT_TTL)

    reservation = _adr_reserve.reserve(
        project_dir=project_dir,
        title=title,
        session_id=session_id,
        owner=os.environ.get("USER", "unknown"),
        ttl_seconds=ttl,
        reservations_path=_reservations_path(project_dir),
    )

    if getattr(args, "json", False):
        payload = _adr_reserve.reservation_payload(reservation)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        # ADR-089: default output is the slot number (integer, one line)
        print(reservation.number)
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    """Free a reserved slot by number."""
    project_dir = _project_dir(args)
    slot = int(args.release)
    rpath = _reservations_path(project_dir)

    data = _adr_reserve.load_json(rpath)
    now = _adr_reserve.utc_now()
    active = _adr_reserve.active_reservations(data, now)

    removed = [r for r in active if r.get("number") == slot]
    kept = [r for r in active if r.get("number") != slot]

    if not removed:
        print(f"[reserve_adr_slot] slot {slot} not found in active reservations", file=sys.stderr)
        return 1

    data["reservations"] = kept

    import fcntl

    rpath.parent.mkdir(parents=True, exist_ok=True)
    lock_path = rpath.with_suffix(rpath.suffix + ".lock")
    with lock_path.open("w") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        tmp = rpath.with_suffix(rpath.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, rpath)
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    print(f"[reserve_adr_slot] released slot {slot} (ADR-{slot:03d})", file=sys.stderr)
    print(slot)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args)
    rpath = _reservations_path(project_dir)

    rows = _adr_reserve.list_reservations(
        project_dir=project_dir,
        reservations_path=rpath,
        include_expired=True,
    )

    if getattr(args, "json", False):
        print(json.dumps({"reservations": rows}, indent=2, sort_keys=True))
    else:
        if not rows:
            print("[reserve_adr_slot] no reservations")
        for row in rows:
            status = row.get("status", "?")
            adr_id = row.get("adr_id", "ADR-???")
            session = row.get("session_id", "?")
            expires = row.get("expires_at", "?")
            path = row.get("path", "?")
            print(f"  {adr_id}  [{status:8s}]  session={session}  expires={expires}  path={path}")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args)
    rpath = _reservations_path(project_dir)

    result = _adr_reserve.cleanup_expired(
        project_dir=project_dir,
        reservations_path=rpath,
    )

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"[reserve_adr_slot] removed {result['removed_count']} expired reservation(s)")
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reserve, release, or list ADR slot numbers atomically (ADR-089 Layer 3)"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project root (default: cwd)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="ADR title for the reservation (used to generate the slug)",
    )
    parser.add_argument(
        "--release",
        metavar="NNN",
        default=None,
        help="Release (free) a previously reserved slot number",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_reservations",
        help="List all in-flight reservations",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove expired reservations",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=DEFAULT_TTL,
        help=f"Reservation TTL in seconds (default: {DEFAULT_TTL} = 30 min)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of plain text",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_reservations:
        return cmd_list(args)

    if args.cleanup:
        return cmd_cleanup(args)

    if args.release is not None:
        return cmd_release(args)

    # Default: reserve next slot
    return cmd_reserve(args)


if __name__ == "__main__":
    sys.exit(main())
