#!/usr/bin/env python3
# SCOPE: both
"""Score WIP safety from stashes, snapshot markers, and dirty files."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_git(args: list[str], root: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def build_score(root: Path = REPO_ROOT) -> dict[str, Any]:
    status_lines = [line for line in run_git(["status", "--short"], root).splitlines() if line.strip()]
    stash_lines = [line for line in run_git(["stash", "list"], root).splitlines() if line.strip()]
    markers = sorted((root / ".cognitive-os" / "runtime").glob("pre-agent-snapshot-*.json"))
    penalty = min(60, len(stash_lines) * 10 + len(markers) * 8 + len(status_lines) * 2)
    score = max(0, 100 - penalty)
    return {
        "status": "pass" if score >= 90 else ("warn" if score >= 70 else "fail"),
        "score": score,
        "dirty_paths": len(status_lines),
        "stash_count": len(stash_lines),
        "snapshot_marker_count": len(markers),
        "markers": [str(path.relative_to(root)) for path in markers[:20]],
        "recommendations": [
            "clear or archive orphan pre-agent snapshot markers" if markers else "snapshot markers clean",
            "triage git stashes before launching more agents" if stash_lines else "stash list clean",
            "commit, archive, or isolate dirty WIP" if status_lines else "working tree clean",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    print(json.dumps(build_score(args.project_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
