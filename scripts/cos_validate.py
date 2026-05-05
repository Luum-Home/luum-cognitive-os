#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.validation_lanes import recommend_lane


def changed_files(repo: Path) -> list[str]:
    proc = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recommend a validation lane for the current diff.")
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--recommend", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--changed-file", action="append", default=[])
    args = parser.parse_args(argv)
    files = args.changed_file or changed_files(Path(args.repo).resolve())
    rec = recommend_lane(files).to_dict()
    payload = {"schema_version": "validation-recommendation.v1", **rec}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"recommended_lane={payload['recommended_lane']}")
        for reason in payload["rationale"]:
            print(f"- {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
