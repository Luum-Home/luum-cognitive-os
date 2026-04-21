#!/usr/bin/env python3
"""CLI for project_scaffolder — creates the 10-category docs/ skeleton (ADR-054).

Usage:
  uv run python3 scripts/project-scaffold.py \
      --project-dir /tmp/my-new-proj --project-name "My Project" [--overwrite] [--json]

Exit codes:
  0 — scaffold written (or all files already existed with --no-overwrite)
  1 — validation error (missing args, bad path)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure lib/ is importable when running as a script
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.project_scaffolder import ProjectScaffolder, expected_file_count  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold the 10-category docs/ tree in a project directory.",
    )
    parser.add_argument("--project-dir", required=True, help="Target project root.")
    parser.add_argument("--project-name", required=True, help="Human-readable project name.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report to stdout.")
    args = parser.parse_args()

    target = Path(args.project_dir).expanduser().resolve()
    try:
        scaffolder = ProjectScaffolder(
            project_name=args.project_name,
            project_dir=target,
            overwrite=args.overwrite,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = scaffolder.scaffold_all()

    if args.json:
        print(json.dumps(
            {
                "project_dir": str(result.project_dir),
                "docs_dir": str(result.docs_dir),
                "created_count": len(result.created),
                "skipped_count": len(result.skipped),
                "expected_total": expected_file_count(),
                "created": [str(p.relative_to(result.project_dir)) for p in result.created],
                "skipped": [str(p.relative_to(result.project_dir)) for p in result.skipped],
            },
            indent=2,
        ))
    else:
        print(result.summary)
        print(f"docs_dir: {result.docs_dir}")
        if result.created:
            print(f"\nCreated {len(result.created)}:")
            for p in result.created:
                print(f"  + {p.relative_to(result.project_dir)}")
        if result.skipped:
            print(f"\nSkipped {len(result.skipped)} (already existed — use --overwrite to replace)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
