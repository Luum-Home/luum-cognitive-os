#!/usr/bin/env python3
# SCOPE: both
"""ADR-279 orphan process audit primitive."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.orphan_process_audit import (  # noqa: E402
    DEFAULT_OLDER_THAN_SECONDS,
    append_metric,
    build_report,
    collect_processes,
    find_orphan_scan_processes,
    parse_ps_output,
    terminate_findings,
)


def _project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for name in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if os.environ.get(name):
            return Path(os.environ[name]).resolve()
    return PROJECT_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit stale orphaned repo-scan processes (ADR-279).")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--older-than-seconds", type=int, default=DEFAULT_OLDER_THAN_SECONDS)
    parser.add_argument("--kill", action="store_true", help="Send SIGTERM/SIGKILL to classified candidates. Default is dry-run.")
    parser.add_argument("--no-force", action="store_true", help="Do not follow SIGTERM with SIGKILL.")
    parser.add_argument("--ps-fixture", default=None, help="Read ps output from a fixture file instead of the live process table.")
    parser.add_argument("--no-metric", action="store_true")
    args = parser.parse_args(argv)

    if args.ps_fixture:
        rows = parse_ps_output(Path(args.ps_fixture).read_text(encoding="utf-8"))
    else:
        rows = collect_processes()

    findings = find_orphan_scan_processes(rows, older_than_seconds=args.older_than_seconds)
    if args.kill:
        findings = terminate_findings(findings, force=not args.no_force)
    report = build_report(findings, killed=args.kill)
    if not args.no_metric:
        append_metric(_project_dir(args.project_dir), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
