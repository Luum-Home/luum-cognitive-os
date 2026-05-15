#!/usr/bin/env python3
# SCOPE: os-only
"""Validate short entrypoint ADR links against canonical ADR files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ADR_LINK_RE = re.compile(r"\[[^\]]+\]\((adrs/[^)#]+)(?:#[^)]+)?\)")


def find_broken_links(root: Path) -> list[str]:
    entrypoints = root / "docs/00-MOCs/entrypoints"
    adr_root = root / "docs/02-Decisions/adrs"
    missing: list[str] = []
    for path in sorted(entrypoints.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in ADR_LINK_RE.finditer(text):
            target = match.group(1)
            canonical = adr_root / target.removeprefix("adrs/")
            if not canonical.exists():
                missing.append(
                    f"{path.relative_to(root)} -> {target} "
                    f"(expected {canonical.relative_to(root)})"
                )
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate entrypoint adrs/... links.")
    parser.add_argument("--project-dir", default=".")
    args = parser.parse_args(argv)
    root = Path(args.project_dir).resolve()
    missing = find_broken_links(root)
    if missing:
        print("Broken entrypoint ADR links:", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        return 2
    print("entrypoint ADR links: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
