#!/usr/bin/env python3
# SCOPE: both
"""CLI for the governed Cognitive OS self-improvement loop."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.governed_self_improvement import (
    create_improvement_draft,
    load_improvement_draft,
    promote_improvement_draft,
    suggest_improvement_signals,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed self-improvement loop")
    parser.add_argument("--project-dir", default=".", help="Project root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("suggest", help="Print evidence-backed improvement signals as JSON")

    draft_parser = sub.add_parser("draft", help="Create a draft from a signal slug")
    draft_parser.add_argument("slug", help="Signal slug from suggest output")

    promote_parser = sub.add_parser("promote", help="Promote an approved draft")
    promote_parser.add_argument("draft_id")
    promote_parser.add_argument("--approved-by")
    promote_parser.add_argument("--auto-promote", action="store_true")

    inspect_parser = sub.add_parser("inspect", help="Inspect an existing draft")
    inspect_parser.add_argument("draft_id")

    args = parser.parse_args()
    project_dir = Path(args.project_dir)

    if args.command == "suggest":
        signals = suggest_improvement_signals(project_dir)
        print(json.dumps([asdict(signal) for signal in signals], indent=2, sort_keys=True))
        return 0

    if args.command == "draft":
        signals = {signal.slug: signal for signal in suggest_improvement_signals(project_dir)}
        if args.slug not in signals:
            parser.error(f"unknown signal slug: {args.slug}")
        draft = create_improvement_draft(project_dir, signals[args.slug])
        print(json.dumps(asdict(draft), indent=2, sort_keys=True))
        return 0

    if args.command == "inspect":
        draft = load_improvement_draft(project_dir, args.draft_id)
        print(json.dumps(asdict(draft), indent=2, sort_keys=True))
        return 0

    if args.command == "promote":
        promotion = promote_improvement_draft(
            project_dir,
            args.draft_id,
            approved_by=args.approved_by,
            auto_promote=args.auto_promote,
        )
        print(json.dumps(promotion, indent=2, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
