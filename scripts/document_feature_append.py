#!/usr/bin/env python3
# SCOPE: project
"""CLI for document-feature append-to-backlog path (ADR-054 Phase 2).

This CLI handles the NEW --project-dir flag behavior only — it appends
a row to docs/05-features/features-backlog.md in the adopter project.
The original document-feature skill behavior (full feature doc under
docs/features/) is invoked separately and is unaffected by this script.

Usage:
  uv run python3 scripts/document_feature_append.py \
      --project-dir /tmp/proj --feature "Biometric login" \
      [--status backlog|in-progress|done|blocked] [--priority L|M|H] \
      [--owner "team-auth"] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.document_feature_writer import BacklogAppender  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Append feature entry to features-backlog.md")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--feature", required=True, help="Feature name (human-readable)")
    p.add_argument("--status", default="backlog",
                   choices=["backlog", "in-progress", "done", "blocked"])
    p.add_argument("--priority", default="M", choices=["L", "M", "H"])
    p.add_argument("--owner", default="<!-- TODO -->")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    try:
        a = BacklogAppender(
            project_dir=Path(args.project_dir).expanduser().resolve(),
            feature_name=args.feature,
            status=args.status,
            priority=args.priority,
            owner=args.owner,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = a.append()
    if args.json:
        print(json.dumps(
            {"path": str(result.path), "feature_id": result.feature_id, "action": result.action},
            indent=2,
        ))
    else:
        print(result.summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
