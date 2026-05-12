#!/usr/bin/env python3
# SCOPE: both
"""ADR-281 — ADR implementation reality audit.

Cross-validates `implementation_status: implemented` ADR claims against
on-disk reality. Allowlist for legitimate runtime artifacts in
`manifests/adr-implementation-runtime-allowlist.yaml`.

Schema: adr-implementation-audit/v1.
Emits findings in the control-plane runner shape (ADR-248).

Usage:
  python3 scripts/cos-adr-implementation-audit.py             # JSON to stdout
  python3 scripts/cos-adr-implementation-audit.py --strict    # exit 2 if any overclaim
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "adr-implementation-audit/v1"
ALLOWLIST_PATH = "manifests/adr-implementation-runtime-allowlist.yaml"
ADR_GLOB = "docs/02-Decisions/adrs/ADR-*.md"


def _resolve_project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if env_var in os.environ:
            return Path(os.environ[env_var]).resolve()
    return Path.cwd().resolve()


def _load_allowlist(root: Path) -> list[dict[str, Any]]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return []
    p = root / ALLOWLIST_PATH
    if not p.exists():
        return []
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except OSError:
        return []
    return d.get("entries", []) or []


def _matches_allowlist(rel_path: str, allowlist: list[dict[str, Any]]) -> bool:
    for entry in allowlist:
        pattern = entry.get("pattern")
        if not pattern:
            continue
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def _strip_comment(value: str) -> str:
    """Strip inline YAML comments like '`lib/foo.py # description`'."""
    if "#" in value:
        return value.split("#", 1)[0].strip()
    return value.strip()


def _parse_impl_files(content: str) -> list[str]:
    m = re.search(r"^implementation_files:\s*\n((?:\s+-\s+.+\n)+)", content[:5000], re.MULTILINE)
    if not m:
        return []
    files: list[str] = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        entry = _strip_comment(s.removeprefix("-").strip())
        if entry:
            files.append(entry)
    return files


def _path_exists(root: Path, rel: str) -> bool:
    """Check disk existence with glob support."""
    target = root / rel
    if target.exists():
        return True
    if rel.endswith("/") and (root / rel.rstrip("/")).exists():
        return True
    if "*" in rel:
        if list(root.glob(rel)):
            return True
    return False


def audit(root: Path) -> dict[str, Any]:
    allowlist = _load_allowlist(root)
    findings: list[dict[str, Any]] = []
    total_implemented = 0
    total_files_checked = 0
    overclaim_adrs: set[str] = set()
    allowlisted_count = 0

    for adr_path in sorted(root.glob(ADR_GLOB)):
        try:
            text = adr_path.read_text(encoding="utf-8")
        except OSError:
            continue
        m_status = re.search(r"^implementation_status:\s*([\w-]+)", text[:3000], re.MULTILINE)
        if not m_status or m_status.group(1).lower() != "implemented":
            continue
        total_implemented += 1
        files = _parse_impl_files(text)
        for rel in files:
            total_files_checked += 1
            if _path_exists(root, rel):
                continue
            if _matches_allowlist(rel, allowlist):
                allowlisted_count += 1
                continue
            overclaim_adrs.add(adr_path.name)
            findings.append({
                "severity": "warn",
                "code": "adr-implementation-file-missing",
                "message": (
                    f"{adr_path.name}: implementation_status: implemented "
                    f"but implementation_files entry {rel!r} does not exist "
                    "on disk and is not in the runtime allowlist."
                ),
                "details": {
                    "adr": adr_path.name,
                    "missing_path": rel,
                },
                "stable_id": f"adr-281/missing/{adr_path.stem}/{rel}",
                "adr": "ADR-281",
            })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowlist_path": ALLOWLIST_PATH,
        "summary": {
            "total_implemented_adrs": total_implemented,
            "total_files_checked": total_files_checked,
            "missing_files": len(findings),
            "allowlisted_files": allowlisted_count,
            "overclaim_adr_count": len(overclaim_adrs),
        },
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-281 implementation reality audit")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if any overclaim (missing non-allowlisted file) is present",
    )
    args = parser.parse_args(argv)

    root = _resolve_project_dir(args.project_dir)
    payload = audit(root)
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.strict and payload["summary"]["missing_files"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
