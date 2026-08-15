#!/usr/bin/env python3
# SCOPE: os-only
"""Validate short entrypoint ADR links against canonical ADR files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Any relative markdown link whose target sits under an `adrs/` segment. The
# previous pattern anchored on a bare `adrs/` prefix, so the moment the links
# were corrected to real relative paths it matched nothing and the checker went
# green by having stopped looking.
ADR_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?:)([^)#]*adrs/[^)#]+\.md)(?:#[^)]+)?\)")


def find_broken_links(root: Path) -> list[str]:
    entrypoints = root / "docs/00-MOCs/entrypoints"
    missing: list[str] = []
    # rglob, not glob: the previous version only ever read the top level.
    for path in sorted(entrypoints.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in ADR_LINK_RE.finditer(text):
            target = match.group(1)
            # Resolve against the linking file's own directory, which is what a
            # reader's markdown viewer does. Resolving against the canonical ADR
            # root instead made every wrong path look right — the checker
            # normalised away the exact defect it exists to catch.
            canonical = (path.parent / target).resolve()
            if not canonical.exists():
                missing.append(f"{path.relative_to(root)} -> {target}")
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
