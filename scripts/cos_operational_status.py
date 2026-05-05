#!/usr/bin/env python3
# SCOPE: os-only
"""Answer safe-to-work/launch/validate/push questions for ADR-123-S4."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.operational_status import build_status  # noqa: E402


def render_text(payload: dict) -> str:
    lines = ["COS Operational Status", "======================", f"project: {payload['project']}", ""]
    labels = {
        "safe_to_work": "SAFE TO WORK",
        "safe_to_launch_agent": "SAFE TO LAUNCH AGENT",
        "safe_to_validate": "SAFE TO VALIDATE",
        "safe_to_push": "SAFE TO PUSH",
    }
    for item in payload["decisions"]:
        lines.append(f"{labels[item['name']]}: {'yes' if item['safe'] else 'no'}")
        lines.append(f"  reason: {item['reason']}")
        lines.append(f"  severity: {item['severity']}")
        lines.append(f"  primitive: {item['owning_primitive']}")
        lines.append(f"  repair: {item['repair']}")
        lines.append(f"  risk: {item['risk_class']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = build_status(Path(args.project_dir))
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else render_text(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
