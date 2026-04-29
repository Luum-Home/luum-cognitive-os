#!/usr/bin/env python3
# SCOPE: both
"""Generate, inspect, or wipe the local Cognitive OS project profile draft."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.project_profile_bootstrap import (  # noqa: E402
    build_project_profile_draft,
    wipe_project_profile,
    write_project_profile_draft,
)


def _project_dir(raw: str | None) -> Path:
    value = (
        raw
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )
    return Path(value).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", help="Project root. Defaults to COS/Codex/Claude env or cwd.")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Generate draft.json and draft.md when bootstrap window permits.")
    generate.add_argument("--force", action="store_true", help="Regenerate even after the early bootstrap window.")

    sub.add_parser("inspect", help="Print the computed draft JSON without writing files.")
    sub.add_parser("wipe", help="Remove .cognitive-os/project-profile/.")

    args = parser.parse_args(argv)
    project = _project_dir(args.project_dir)

    if args.command == "generate":
        path = write_project_profile_draft(project, force=args.force)
        if path is None:
            print("profile bootstrap skipped: outside bootstrap window and no existing draft")
            return 0
        print(path)
        return 0
    if args.command == "inspect":
        print(json.dumps(build_project_profile_draft(project), indent=2, sort_keys=True))
        return 0
    if args.command == "wipe":
        wipe_project_profile(project)
        print(project / ".cognitive-os" / "project-profile")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
