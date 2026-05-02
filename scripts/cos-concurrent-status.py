#!/usr/bin/env python3
# SCOPE: both
"""Print read-only Concurrent Agent Safety status as JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.concurrent_agent_safety_status import collect_status, status_to_json  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only concurrent-agent safety status")
    parser.add_argument("--project-dir", default=".", help="Project root to inspect")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    args = parser.parse_args(argv)
    status = collect_status(args.project_dir)
    print(status_to_json(status, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
