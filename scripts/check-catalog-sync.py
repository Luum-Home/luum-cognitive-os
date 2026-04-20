#!/usr/bin/env python3
# SCOPE: both
"""Validate that skills on disk match CATALOG.md entries.

Exit 0 if in sync, exit 1 with details if mismatched.
Run as pre-commit hook to prevent phantom/invisible skills.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_skills_on_disk(root: Path) -> set[str]:
    """Return set of skill names from .cognitive-os/skills/*/SKILL.md"""
    skills_dir = root / ".cognitive-os" / "skills"
    if not skills_dir.exists():
        return set()
    result = set()
    for entry in skills_dir.iterdir():
        if entry.is_dir() and (entry / "SKILL.md").exists():
            result.add(entry.name)
    return result


def get_skills_in_catalog(root: Path) -> set[str]:
    """Return set of skill names from skills/CATALOG.md (excluding header/separator rows)."""
    catalog = root / "skills" / "CATALOG.md"
    if not catalog.exists():
        return set()

    result = set()
    # Skip known non-skill table cell values
    _skip = {"Skill", "-------", ""}
    for line in catalog.read_text().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Extract first column of a table row
        m = re.match(r"\|\s*([\w][\w\-]*)\s*\|", line)
        if not m:
            continue
        cell = m.group(1)
        if cell in _skip:
            continue
        # Skip separator rows like |-------|
        if re.match(r"^[-]+$", cell):
            continue
        result.add(cell)
    return result


def load_allowlist(root: Path) -> tuple[set[str], set[str]]:
    """Return (phantom_allowlist, invisible_allowlist) from .cognitive-os/skills/_catalog-allowlist.txt."""
    path = root / ".cognitive-os" / "skills" / "_catalog-allowlist.txt"
    phantom_ok: set[str] = set()
    invisible_ok: set[str] = set()
    if not path.exists():
        return phantom_ok, invisible_ok
    section = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "[phantom]":
            section = "phantom"
        elif line == "[invisible]":
            section = "invisible"
        elif section == "phantom":
            phantom_ok.add(line)
        elif section == "invisible":
            invisible_ok.add(line)
    return phantom_ok, invisible_ok


def main() -> int:
    root = get_project_root()

    try:
        on_disk = get_skills_on_disk(root)
    except Exception as exc:
        print(f"ERROR: could not scan skills on disk: {exc}", file=sys.stderr)
        return 1

    try:
        in_catalog = get_skills_in_catalog(root)
    except Exception as exc:
        print(f"ERROR: could not parse CATALOG.md: {exc}", file=sys.stderr)
        return 1

    if not on_disk and not in_catalog:
        print("Catalog sync OK: 0 skills (both disk and catalog are empty)")
        return 0

    phantom_allowlist, invisible_allowlist = load_allowlist(root)

    phantom = (in_catalog - on_disk) - phantom_allowlist    # in catalog but missing from disk
    invisible = (on_disk - in_catalog) - invisible_allowlist  # on disk but not in catalog

    if phantom or invisible:
        if phantom:
            print(f"PHANTOM skills (in CATALOG but don't exist on disk) [{len(phantom)}]:")
            for s in sorted(phantom):
                print(f"  - {s}")
        if invisible:
            print(f"INVISIBLE skills (on disk but not in CATALOG) [{len(invisible)}]:")
            for s in sorted(invisible):
                print(f"  - {s}")
        print(
            "\nFix: run /add-skill to register new skills, or remove stale CATALOG entries."
        )
        print(
            "To allowlist known discrepancies, add to "
            ".cognitive-os/skills/_catalog-allowlist.txt"
        )
        return 1

    total_allowlisted = len(phantom_allowlist) + len(invisible_allowlist)
    print(
        f"Catalog sync OK: {len(on_disk)} skills on disk, "
        f"{len(in_catalog)} in CATALOG "
        f"({total_allowlisted} discrepancies grandfathered)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
