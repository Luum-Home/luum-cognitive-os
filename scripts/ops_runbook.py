#!/usr/bin/env python3
# SCOPE: project
"""CLI for ops_runbook scaffolder (ADR-054 Phase 2).

Usage:
  uv run python3 scripts/ops_runbook.py \
      --project-dir /tmp/proj [--overwrite] [--json]

Emits operations.md + admin-processes.md + monitoring.md under
docs/06-backoffice/. Idempotent — extends autogen region, preserves
user content below the autogen-footer marker.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.ops_runbook import OpsRunbookScaffolder  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold docs/06-backoffice ops runbooks")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--project-name", default="")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    s = OpsRunbookScaffolder(
        project_dir=Path(args.project_dir).expanduser().resolve(),
        project_name=args.project_name,
        overwrite=args.overwrite,
    )
    result = s.scaffold()

    if args.json:
        print(json.dumps(
            {
                "project_dir": str(result.project_dir),
                "created": [str(p) for p in result.created],
                "extended": [str(p) for p in result.extended],
                "overwritten": [str(p) for p in result.overwritten],
                "skipped": [str(p) for p in result.skipped],
            },
            indent=2,
        ))
    else:
        print(result.summary)
        for p in result.created:
            print(f"  + created  {p}")
        for p in result.extended:
            print(f"  ~ extended {p}")
        for p in result.overwritten:
            print(f"  ! overwrote {p}")
        for p in result.skipped:
            print(f"  - skipped  {p} (no autogen markers; preserve user content)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
