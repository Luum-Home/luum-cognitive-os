#!/usr/bin/env python3
# SCOPE: os-only
"""Report and optionally clear stale pytest lastfailed cache.

Pytest's ``.pytest_cache/v/cache/lastfailed`` is useful during repair, but in a
large multi-lane repo it can preserve historical failures after the relevant
node IDs have passed in later targeted runs. This tool makes that state explicit
so agents do not treat stale cache entries as current failing evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]


def load_lastfailed(project_dir: Path) -> dict[str, Any]:
    path = project_dir / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"<unreadable-cache>": True}
    return payload if isinstance(payload, dict) else {"<invalid-cache>": True}


def default_python(project_dir: Path) -> str:
    env_python = os.environ.get("PYTHON_BIN") or os.environ.get("PYTHON")
    if env_python:
        return env_python
    venv_python = project_dir / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def run_lastfailed(project_dir: Path, *, timeout_seconds: int) -> dict[str, Any]:
    command = [default_python(project_dir), "-m", "pytest", "--lf", "-q", "-ra"]
    try:
        proc = subprocess.run(
            command,
            cwd=project_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "command": command,
            "returncode": None,
            "stdout_tail": (exc.stdout or "")[-2000:],
            "stderr_tail": (exc.stderr or "")[-2000:],
        }
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "command": command,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def clear_cache(project_dir: Path) -> bool:
    path = project_dir / ".pytest_cache" / "v" / "cache" / "lastfailed"
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def build_report(project_dir: Path, *, verify: bool, clear_stale: bool, timeout_seconds: int) -> dict[str, Any]:
    before = load_lastfailed(project_dir)
    verification = run_lastfailed(project_dir, timeout_seconds=timeout_seconds) if verify and before else None
    stale = bool(before) and verification is not None and verification.get("status") == "pass"
    cleared = clear_cache(project_dir) if stale and clear_stale else False
    after = load_lastfailed(project_dir)
    status = "stale" if stale else ("active_failures" if before else "empty")
    if verification and verification.get("status") in {"fail", "timeout"}:
        status = str(verification["status"])
    return {
        "schema_version": "pytest-lastfailed-health/v1",
        "status": "pass" if status in {"empty", "stale"} else "warn",
        "cache_state": status,
        "lastfailed_count_before": len(before),
        "lastfailed_count_after": len(after),
        "cleared": cleared,
        "verification": verification,
        "next_actions": next_actions(status, cleared),
    }


def next_actions(status: str, cleared: bool) -> list[str]:
    if status == "stale" and cleared:
        return ["Stale pytest lastfailed cache cleared after --lf passed."]
    if status == "stale":
        return ["Run scripts/cos-pytest-lastfailed-health --verify --clear-stale to clear stale cache after --lf passes."]
    if status in {"fail", "timeout", "active_failures"}:
        return ["Treat the listed --lf result as current repair evidence before running broad lanes."]
    return ["No pytest lastfailed cache entries are present."]


def print_text(report: dict[str, Any]) -> None:
    print(f"pytest lastfailed health: {report['status']} ({report['cache_state']})")
    print(f"entries_before={report['lastfailed_count_before']} entries_after={report['lastfailed_count_after']} cleared={report['cleared']}")
    verification = report.get("verification")
    if isinstance(verification, dict):
        print(f"verification={verification.get('status')} rc={verification.get('returncode')}")
    for action in report.get("next_actions", []):
        print(f"- {action}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=ROOT)
    parser.add_argument("--verify", action="store_true", help="run pytest --lf to determine whether cache entries are stale")
    parser.add_argument("--clear-stale", action="store_true", help="delete lastfailed cache only when --verify passes")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = build_report(args.project_dir.resolve(), verify=args.verify, clear_stale=args.clear_stale, timeout_seconds=args.timeout_seconds)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 2 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
