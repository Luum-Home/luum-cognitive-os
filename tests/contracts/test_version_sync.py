"""Contract: root VERSION and cmd/cos/VERSION must stay in lockstep.

Decided 2026-05-06 in /bump-version skill v0.2.0. Goes with skills/bump-version/SKILL.md
Step 3 (lockstep write). If a future ADR bifurcates the streams, update this test
and the skill in the same change.
"""
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[2]


def test_version_files_in_lockstep() -> None:
    root_version = (ROOT / "VERSION").read_text().strip()
    bin_version = (ROOT / "cmd" / "cos" / "VERSION").read_text().strip()
    assert root_version == bin_version, (
        f"VERSION drift: root={root_version!r} vs cmd/cos={bin_version!r}. "
        "Both files must be bumped together. See skills/bump-version/SKILL.md."
    )


def test_version_files_are_semver() -> None:
    import re

    pattern = re.compile(r"^\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?$")
    for rel in ("VERSION", "cmd/cos/VERSION"):
        v = (ROOT / rel).read_text().strip()
        assert pattern.match(v), f"{rel}={v!r} is not semver"
