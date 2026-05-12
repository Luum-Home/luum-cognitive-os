#!/usr/bin/env python3
# SCOPE: both
"""ADR-278 — subprocess.run timeout discipline audit.

Background: the 2026-05-12 verification surfaced pytest contracts+audit
suites hanging because 169 of 174 `subprocess.run(...)` calls in tests
omit `timeout=`. The same anti-pattern is present in production
(scripts/, hooks/, lib/) with 142 of 220 calls omitting timeout. A test
suite or hook chain can be hung indefinitely by one buggy subprocess
that never returns.

This audit scans the repo for `subprocess.run(...)` calls without an
explicit `timeout=` keyword and emits findings in the control-plane
runner shape (ADR-248). Allowlist-driven via
`manifests/subprocess-timeout-allowlist.yaml` (intentional unbounded
runs, e.g. servers, REPLs, watchers).

Output:
  schema_version: subprocess-timeout-audit/v1
  summary:
    total_calls:        <int>
    timed_calls:        <int>
    untimed_calls:      <int>
    allowlisted_calls:  <int>
    coverage_pct:       <float>
  findings: [<warn per untimed-non-allowlisted call>]

Usage:
  python3 scripts/cos-subprocess-timeout-audit.py             # JSON to stdout
  python3 scripts/cos-subprocess-timeout-audit.py --strict    # exit 2 if any
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "subprocess-timeout-audit/v1"
ALLOWLIST_PATH = "manifests/subprocess-timeout-allowlist.yaml"
SCAN_AREAS = ("scripts", "hooks", "lib", "tests", "packages")
SKIP_DIRS = {".venv", "__pycache__", "node_modules", ".git", "reference"}
# Match subprocess.run(...) including its argument tuple. We use a balanced
# parser rather than a regex so nested parens (lambdas, comprehensions) are
# handled correctly.
RUN_TOKEN = "subprocess.run("


def _resolve_project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if env_var in os.environ:
            return Path(os.environ[env_var]).resolve()
    return Path.cwd().resolve()


def _load_allowlist(root: Path) -> set[str]:
    """Return set of "rel/path.py:line" allowlist entries."""
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return set()
    p = root / ALLOWLIST_PATH
    if not p.exists():
        return set()
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except OSError:
        return set()
    out: set[str] = set()
    for entry in d.get("entries", []) or []:
        path = entry.get("path")
        line = entry.get("line")
        if path and line is not None:
            out.add(f"{path}:{line}")
    return out


def _extract_call(text: str, start: int) -> tuple[str, int] | None:
    """Return (call_substring, line_of_start) starting at subprocess.run(."""
    depth = 0
    i = start + len(RUN_TOKEN)
    end = i
    in_string = None
    while end < len(text):
        c = text[end]
        if in_string:
            if c == "\\":
                end += 2
                continue
            if c == in_string:
                in_string = None
        elif c in ("'", '"'):
            in_string = c
        elif c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                # Closing bracket of subprocess.run(...)
                line_of_start = text[:start].count("\n") + 1
                return text[start:end + 1], line_of_start
            depth -= 1
        end += 1
    return None


def scan_file(path: Path, root: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    rel = path.relative_to(root).as_posix()
    findings: list[dict[str, Any]] = []
    cursor = 0
    while True:
        idx = text.find(RUN_TOKEN, cursor)
        if idx == -1:
            break
        result = _extract_call(text, idx)
        if not result:
            break
        call, line = result
        cursor = idx + len(RUN_TOKEN)
        has_timeout = bool(re.search(r"\btimeout\s*=", call))
        findings.append({
            "rel": rel,
            "line": line,
            "has_timeout": has_timeout,
        })
    return findings


def audit(root: Path) -> dict[str, Any]:
    allowlist = _load_allowlist(root)
    all_calls: list[dict[str, Any]] = []
    for area in SCAN_AREAS:
        area_path = root / area
        if not area_path.is_dir():
            continue
        for p in area_path.rglob("*.py"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            for f in scan_file(p, root):
                all_calls.append(f)

    findings: list[dict[str, Any]] = []
    timed = 0
    allowlisted = 0
    untimed = 0
    for c in all_calls:
        if c["has_timeout"]:
            timed += 1
            continue
        key = f"{c['rel']}:{c['line']}"
        if key in allowlist:
            allowlisted += 1
            continue
        untimed += 1
        findings.append({
            "severity": "warn",
            "code": "subprocess-run-without-timeout",
            "message": (
                f"{c['rel']}:{c['line']} calls subprocess.run without an "
                "explicit timeout= keyword; a buggy subprocess can hang "
                "the caller indefinitely (ADR-278)."
            ),
            "details": {"path": c["rel"], "line": c["line"]},
            "stable_id": f"adr-278/subprocess-timeout/{c['rel']}:{c['line']}",
            "adr": "ADR-278",
        })

    total = len(all_calls)
    coverage = (timed + allowlisted) / total * 100.0 if total else 100.0
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowlist_path": ALLOWLIST_PATH,
        "summary": {
            "total_calls": total,
            "timed_calls": timed,
            "untimed_calls": untimed,
            "allowlisted_calls": allowlisted,
            "coverage_pct": round(coverage, 2),
        },
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-278 subprocess.run timeout audit")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if any untimed-non-allowlisted call is present",
    )
    args = parser.parse_args(argv)

    root = _resolve_project_dir(args.project_dir)
    payload = audit(root)
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.strict and payload["summary"]["untimed_calls"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
