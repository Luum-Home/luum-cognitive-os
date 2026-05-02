#!/usr/bin/env python3
# SCOPE: both
"""Detect unreachable local commits and overwritten tracked changes."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from lib.session_bus import append_event


def run(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False, timeout=20)


def orphan_commits(root: Path) -> list[str]:
    proc = run(root, ["fsck", "--no-reflogs", "--unreachable", "--no-progress"])
    commits: list[str] = []
    for line in (proc.stdout + proc.stderr).splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[-2] == "commit":
            commits.append(parts[-1])
    return sorted(set(commits))


def overwritten_paths(root: Path, before: str, after: str) -> list[str]:
    proc = run(root, ["diff", "--name-only", before, after])
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--before")
    parser.add_argument("--after", default="HEAD")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    report = {
        "orphan_commits": orphan_commits(root),
        "overwritten_paths": overwritten_paths(root, args.before, args.after) if args.before else [],
    }
    if args.emit and (report["orphan_commits"] or report["overwritten_paths"]):
        append_event("orphan_overwrite_detected", report, project_dir=root)
        out = root / ".cognitive-os" / "runtime" / "orphan-overwrite.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(report, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"orphan commits: {len(report['orphan_commits'])}")
        print(f"overwritten paths: {len(report['overwritten_paths'])}")
    return 1 if report["orphan_commits"] or report["overwritten_paths"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
