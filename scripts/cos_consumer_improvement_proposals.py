#!/usr/bin/env python3
# SCOPE: both
"""Export/import sanitized consumer primitive improvement proposals."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.consumer_improvement_proposals import (  # noqa: E402
    build_consumer_improvement_bundle,
    import_consumer_improvement_bundle,
    write_consumer_improvement_bundle,
)
from lib.script_io import print_json_status as _print  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export")
    export.add_argument("--project-dir", type=Path, default=None)
    export.add_argument("--project", required=True)
    export.add_argument("--profile", default="core")
    export.add_argument("--since", default="30d")
    export.add_argument("--reporter", default="consumer-project")
    export.add_argument("--producer-type", default="human", choices=["human", "ci", "agent", "remote-instance", "organization"])
    export.add_argument("--producer-identity")
    export.add_argument("--source-repo")
    export.add_argument("--machine-id")
    export.add_argument("--threshold", type=int, default=3)
    export.add_argument("--output", type=Path)

    imp = sub.add_parser("import")
    imp.add_argument("--project-dir", type=Path, default=None)
    imp.add_argument("bundle", type=Path)

    args = parser.parse_args(argv)
    root = (args.project_dir or PROJECT_ROOT).resolve()

    if args.command == "export":
        bundle = build_consumer_improvement_bundle(
            root,
            project=args.project,
            profile=args.profile,
            since=args.since,
            reporter=args.reporter,
            producer_type=args.producer_type,
            producer_identity=args.producer_identity,
            source_repo=args.source_repo,
            machine_id=args.machine_id,
            threshold=args.threshold,
        )
        if args.output:
            write_consumer_improvement_bundle(bundle, args.output)
            bundle["written_to"] = str(args.output)
        return _print(bundle)

    if args.command == "import":
        return _print(import_consumer_improvement_bundle(root, args.bundle.resolve()))

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
