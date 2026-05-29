#!/usr/bin/env python3
# SCOPE: os-only
"""Cognitive OS benchmark-bound self-improvement CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.improve_loop import build_context, build_feedback, run_improvement_loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(PROJECT_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a benchmark-bound improvement loop")
    run.add_argument("--project-dir", dest="sub_project_dir", help="project root for wrapper compatibility")
    run.add_argument("--task-dir", required=True, help="benchmark task contract directory")
    run.add_argument("--run-id", help="stable run identifier; defaults to task timestamp")
    run.add_argument("--max-gen", type=int, default=1, help="number of generations to run")
    run.add_argument("--json", action="store_true", help="emit JSON summary")

    feedback = sub.add_parser("feedback", help="propose gated changes from run artifacts")
    feedback.add_argument("--project-dir", dest="sub_project_dir", help="project root for wrapper compatibility")
    feedback.add_argument("--run-id", required=True)
    feedback.add_argument("--generation", type=int)
    feedback.add_argument("--json", action="store_true")

    context = sub.add_parser("context", help="render context.md for a run")
    context.add_argument("--project-dir", dest="sub_project_dir", help="project root for wrapper compatibility")
    context.add_argument("--run-id", required=True)
    context.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    project_root = Path(getattr(args, "sub_project_dir", None) or args.project_dir).resolve()

    if args.command == "run":
        payload = run_improvement_loop(project_root, Path(args.task_dir), run_id=args.run_id, max_gen=args.max_gen)
    elif args.command == "feedback":
        payload = build_feedback(project_root, args.run_id, generation=args.generation)
    elif args.command == "context":
        rendered = build_context(project_root, args.run_id)
        payload = {"run_id": args.run_id, "context_path": str(project_root / ".cognitive-os" / "improvement-runs" / args.run_id / "context.md")}
        if not args.json:
            print(rendered, end="")
            return 0
    else:
        raise AssertionError(args.command)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
