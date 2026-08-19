#!/usr/bin/env python3
"""Every seat in the hook registration allowlist must name a hook that exists.

WHY. `hooks/_lib/registration-allowlist.txt` is a RATCHET: each line suppresses
one hook from `scripts/check_hook_registration.py`. A line naming a file that no
longer exists suppresses nothing — it is a seat in a ledger with no occupant, and
it makes the ledger's size lie about how much is being excused.

The occupancy set is a CENSUS, not a written list: it is globbed from the tree at
assert time, over both hook roots (`hooks/` and `packages/*/hooks/`), so a hook
that moves between the two roots does not become a false ghost.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = REPO_ROOT / "hooks" / "_lib" / "registration-allowlist.txt"


def _seats() -> list[str]:
    return [
        line.strip()
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _hooks_on_disk() -> set[str]:
    """Census of live hook filenames, resolved over every hook root."""
    names: set[str] = set()
    for pattern in ("hooks/*.sh", "packages/*/hooks/*.sh"):
        for path in REPO_ROOT.glob(pattern):
            if path.is_file() and not path.name.startswith("_"):
                names.add(path.name)
    return names


def test_allowlist_has_no_seat_without_a_hook() -> None:
    on_disk = _hooks_on_disk()
    assert on_disk, "hook census came back empty — the glob, not the allowlist, is broken"
    ghosts = sorted({seat for seat in _seats() if seat not in on_disk})
    assert not ghosts, (
        "registration-allowlist.txt suppresses hooks that do not exist: "
        f"{ghosts}. Each of these excuses nothing; delete the line."
    )


def test_allowlist_seats_are_unique() -> None:
    seats = _seats()
    dupes = sorted({s for s in seats if seats.count(s) > 1})
    assert not dupes, f"duplicate seats in registration-allowlist.txt: {dupes}"
