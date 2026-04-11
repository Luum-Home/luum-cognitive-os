#!/usr/bin/env python3
"""Validate that every lib/*.py is imported by at least 1 non-lib file.

Exit 0 if all wired (or allowlisted), exit 1 with details of unwired libs.

This is a RATCHET — existing unwired libs are grandfathered in via
lib/_wiring-allowlist.txt.  New unwired libs are BLOCKED.
As libs get wired in subsequent phases, remove them from the allowlist.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_libs(root: Path) -> list[str]:
    """Return sorted list of bare module names from lib/*.py."""
    lib_dir = root / "lib"
    if not lib_dir.exists():
        return []
    names = []
    for f in lib_dir.iterdir():
        if (
            f.is_file()
            and f.suffix == ".py"
            and f.name not in ("__init__.py",)
            and not f.name.startswith("_")
        ):
            names.append(f.stem)
    return sorted(names)


def _is_imported(bare: str, root: Path) -> bool:
    """Return True if bare module name is imported by at least 1 file outside lib/."""
    patterns = [
        re.compile(rf"from\s+lib\.{re.escape(bare)}\s+import"),
        re.compile(rf"import\s+lib\.{re.escape(bare)}"),
    ]
    # Search dirs that are allowed to import from lib/
    # Includes both .py and .sh files (hooks embed Python via heredocs)
    search_dirs = ["hooks", "tests", "scripts", "skills", ".cognitive-os"]
    for dir_name in search_dirs:
        search = root / dir_name
        if not search.exists():
            continue
        for candidate in (*search.rglob("*.py"), *search.rglob("*.sh")):
            if "__pycache__" in str(candidate):
                continue
            try:
                content = candidate.read_text(errors="ignore")
            except OSError:
                continue
            if any(p.search(content) for p in patterns):
                return True
    return False


def load_allowlist(root: Path) -> set[str]:
    path = root / "lib" / "_wiring-allowlist.txt"
    if not path.exists():
        return set()
    result = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            result.add(line)
    return result


def main() -> int:
    root = get_project_root()
    libs = get_libs(root)
    allowlist = load_allowlist(root)

    if not libs:
        print("Lib wiring OK: no lib modules found")
        return 0

    unwired: list[str] = []
    for lib_name in libs:
        if lib_name in allowlist:
            continue
        if not _is_imported(lib_name, root):
            unwired.append(lib_name)

    total = len(libs)
    allowlisted = len([l for l in libs if l in allowlist])
    checked = total - allowlisted
    wired_count = checked - len(unwired)

    if unwired:
        print(f"UNWIRED libs ({len(unwired)}/{total}):")
        for lib in unwired:
            print(f"  - lib/{lib}.py")
        print(
            f"\nWiring rate: {100 * wired_count // checked if checked else 0}% "
            f"({wired_count}/{checked} checked, {allowlisted} grandfathered)"
        )
        print(
            "\nFix: import the lib from a hook/script/skill, "
            "or add to lib/_wiring-allowlist.txt if intentionally standalone."
        )
        return 1

    print(
        f"Lib wiring OK: {wired_count}/{checked} checked libs are imported "
        f"({allowlisted} grandfathered in allowlist)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
