"""ADR numbering integrity contracts."""

from __future__ import annotations

import re
from pathlib import Path


def test_adr_numbers_are_contiguous() -> None:
    adr_dir = Path(__file__).resolve().parents[2] / "docs" / "adrs"
    numbers: set[int] = set()
    for path in adr_dir.glob("ADR-*.md"):
        match = re.match(r"ADR-(\d+)", path.name)
        if match:
            numbers.add(int(match.group(1)))

    assert numbers, "ADR directory must contain numbered ADRs"
    missing = [number for number in range(min(numbers), max(numbers) + 1) if number not in numbers]
    assert missing == []


def test_tombstone_adrs_use_neutral_contract() -> None:
    adr_dir = Path(__file__).resolve().parents[2] / "docs" / "adrs"
    tombstones = sorted(adr_dir.glob("ADR-*-tombstone.md"))
    assert tombstones, "Expected explicit ADR tombstones for reserved gaps"
    required_sections = (
        "Status",
        "Context",
        "Decision",
        "Consequences",
        "Alternatives rejected",
        "Verification",
    )
    for path in tombstones:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "status: tombstone" in text, f"{path.name} must declare tombstone status"
        for section in required_sections:
            assert f"## {section}" in text, f"{path.name} missing ## {section}"
