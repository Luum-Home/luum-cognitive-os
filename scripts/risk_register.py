#!/usr/bin/env python3
"""CLI for risk_register scaffolder (ADR-054 Phase 2).

Usage:
  uv run python3 scripts/risk_register.py \
      --project-dir /tmp/proj --assets "user db, api keys" [--overwrite] [--json]

STRIDE-seeded scaffolder. Emits 6 STRIDE rows as TODO placeholders.
Does not generate risks from prose.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.risk_register import RiskRegisterScaffolder  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold docs/03-dominio-riesgo/risk-register.md (STRIDE)")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--assets", default="", help="Brief description of system assets.")
    p.add_argument("--project-name", default="")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    s = RiskRegisterScaffolder(
        project_dir=Path(args.project_dir).expanduser().resolve(),
        assets_brief=args.assets,
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
