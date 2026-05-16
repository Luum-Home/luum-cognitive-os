#!/usr/bin/env python3
# SCOPE: project
"""CLI for domain_model scaffolder (ADR-054 Phase 2).

Usage:
  uv run python3 scripts/domain_model.py \
      --project-dir /tmp/proj --brief "ecommerce platform" [--overwrite] [--json]

This is a SCAFFOLDER — emits templates with TODO markers. Does not
generate domain content from prose.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.domain_model import DomainModelScaffolder  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold docs/03-domain-risk/domain-model.md")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--brief", default="", help="Short prose describing the domain (inserted verbatim).")
    p.add_argument("--project-name", default="")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    s = DomainModelScaffolder(
        project_dir=Path(args.project_dir).expanduser().resolve(),
        brief=args.brief,
        project_name=args.project_name,
        overwrite=args.overwrite,
    )
    result = s.scaffold()

    if args.json:
        print(json.dumps({"path": str(result.path), "action": result.action}, indent=2))
    else:
        print(result.summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
