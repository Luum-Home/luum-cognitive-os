#!/usr/bin/env python3
# SCOPE: os-only
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.session_lifecycle import reap_sessions


def _run_cleanup(repo: Path, backup_root: Path, apply: bool) -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "cos_cleanup_preserved_wip.py"
    proc = subprocess.run(
        ["python3", str(script), "--repo", str(repo), "--backup-root", str(backup_root), "--all", "--json", *( ["--apply"] if apply else [] )],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    raw_payload = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {"stdout": proc.stdout}
    payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {"payload": raw_payload}
    payload["returncode"] = proc.returncode
    payload["stderr"] = proc.stderr
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run-first safe repair CLI for low-risk Cognitive OS hygiene.")
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--backup-root")
    parser.add_argument("--dry-run", action="store_true", help="Plan repairs without mutation (default).")
    parser.add_argument("--safe", action="store_true", help="Limit to deterministic low-risk repairs.")
    parser.add_argument("--apply", action="store_true", help="Apply safe repairs and write reversible backup records.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    apply = bool(args.apply)
    if apply and not args.safe:
        raise SystemExit("cos repair --apply requires --safe")
    backup_root = Path(args.backup_root).resolve() if args.backup_root else Path.home() / ".codex" / "backups" / repo.name / "repair"
    cleanup = _run_cleanup(repo, backup_root, apply=apply)
    reaper = reap_sessions(repo, grace_seconds=0, dry_run=not apply).to_dict()
    payload = {
        "schema_version": "cos-repair.v1",
        "mode": "apply" if apply else "dry-run",
        "safe": bool(args.safe or not apply),
        "repo": str(repo),
        "backup_root": str(backup_root),
        "repairs": {"preserved_wip_cleanup": cleanup, "session_reaper": reaper},
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"mode={payload['mode']}")
        print(f"backup_root={backup_root}")
        print("repairs=preserved_wip_cleanup,session_reaper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
