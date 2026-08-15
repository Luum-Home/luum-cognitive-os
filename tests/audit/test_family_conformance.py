"""Recurrence guard for the family conformance probe.

This is not a second instrument. It is `scripts/family_conformance_probe.py`
run at a second moment: the probe answers "who differs from the family" during a
session, and this file freezes that answer so a member cannot quietly rejoin the
defective set later.

Three assertions, in the order they matter:

  1. POPULATION. A probe that finds nobody exits 0 and measures nothing. If the
     family scans to fewer members than it declares, the test fails — silence is
     never a pass.
  2. PARTITION, exactly. The known-defective set is compared with `==`, not
     `<=`. A ledger that accepts more than reality is a cushion: it leaves free
     slots while reporting zero new findings. When one of the entries below is
     repaired, this test goes red and the entry must be deleted — that is the
     intended way to learn that a fix landed.
  3. THE PROBE STILL BITES. Run against `3a6e737ba~1`, a revision that predates
     a known repair, the two guards that commit fixed must come back DEFECTIVE.
     This is the mutation direction: it fails if someone weakens the fixtures
     until everything looks conforming.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "scripts" / "family_conformance_probe.py"

# Defective members accepted at the time of writing (2026-08-15), each with the
# reason it is not fixed here. This file MEASURES; the repairs belong to the
# owners of those files.
#
# Compared exactly. Remove an entry the day it is repaired.
KNOWN_DEFECTIVE: dict[str, str] = {
    "hooks/research-compliance-guard.sh": (
        "Blocks a documented git grep whose quoted regex is <home>/<charclass>/Projects/. A repair "
        "was in flight in the working tree on 2026-08-15 (it added the "
        "describes_a_username discriminator from 3a6e737b) and this branch of the "
        "pattern was still blocking after it. Owned by that change, not by the probe."
    ),
    "scripts/provenance_scan.py": (
        "Fourth member of the family, found by this probe and never reported before. "
        "Carries the same defect 3a6e737b fixed in check-local-privacy.sh and "
        "check_absolute_paths.py: it reads a quoted regex in a documented command as a "
        "real home path. It reports the quoted character class as a forbidden path."
    ),
}

FAMILY = "home-path-leak"
PRE_FIX_REV = "3a6e737ba~1"


def run_probe(*args: str) -> tuple[int, dict]:
    import json

    proc = subprocess.run(
        [sys.executable, str(PROBE), "--family", FAMILY, "--json", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode == 2 and not proc.stdout.strip():
        pytest.fail(f"probe errored: {proc.stderr[-2000:]}")
    return proc.returncode, json.loads(proc.stdout)[0]


def names(result: dict, verdict: str) -> set[str]:
    return {row["candidate"] for row in result["buckets"].get(verdict, [])}


@pytest.fixture(scope="module")
def working_tree() -> dict:
    _, result = run_probe()
    return result


@pytest.mark.slow
@pytest.mark.timeout(1800)
def test_population_guard(working_tree: dict) -> None:
    """An empty scan must fail, not pass."""
    assert working_tree["members"] >= working_tree["min_members"], (
        f"family {FAMILY} found {working_tree['members']} members "
        f"(minimum {working_tree['min_members']}). Either the channel screen stopped "
        "matching the population, or the fixtures stopped triggering anyone. Both are "
        "instrument failures, not a clean bill of health."
    )


@pytest.mark.slow
@pytest.mark.timeout(1800)
def test_defective_set_is_exact(working_tree: dict) -> None:
    """No new defective member, and no stale entry in the ledger either."""
    defective = names(working_tree, "DEFECTIVE") | names(working_tree, "INVERTED")
    known = set(KNOWN_DEFECTIVE)
    new = defective - known
    repaired = known - defective
    assert not new, (
        "new member of the home-path-leak family blocks the discriminator "
        f"(a document ABOUT leaked paths): {sorted(new)}. Fix it or add it to "
        "KNOWN_DEFECTIVE with the reason it stays."
    )
    assert not repaired, (
        f"KNOWN_DEFECTIVE lists {sorted(repaired)} as broken and the probe finds them "
        "conforming. A suppressor that suppresses nothing is a bug: delete the entry."
    )


@pytest.mark.slow
@pytest.mark.timeout(1800)
def test_probe_still_bites_on_a_known_broken_revision() -> None:
    """Mutation direction: at a pre-fix revision the repaired guards must fail.

    Uses real history rather than a synthetic mutant. `3a6e737b` repaired
    check-local-privacy.sh and check_absolute_paths.py; one commit earlier both
    carried the defect. If the fixtures are ever weakened until nothing trips,
    this is the assertion that notices.
    """
    _, result = run_probe("--at", PRE_FIX_REV)
    defective = names(result, "DEFECTIVE")
    for path in ("scripts/check-local-privacy.sh", "scripts/check_absolute_paths.py"):
        assert path in defective, (
            f"{path} is DEFECTIVE at {PRE_FIX_REV} by construction (commit 3a6e737b is "
            f"its repair) and the probe reports it as {_verdict_of(result, path)}. The "
            "fixtures no longer detect the defect they were written for."
        )


def _verdict_of(result: dict, candidate: str) -> str:
    for row in result["rows"]:
        if row["candidate"] == candidate:
            return row["verdict"]
    return "not scanned at all"
