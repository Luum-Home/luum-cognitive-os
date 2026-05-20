#!/usr/bin/env python3
# SCOPE: os-only
"""Verify high-stakes plan checkbox claims.

This is the first executable slice of ADR-105/ADR-108. It intentionally focuses
on deterministic filesystem claims that caused real false-done failures:
archive/remove/done plan checkboxes must include bilateral proof, and hook
archive claims can be verified directly.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as _read

HIGH_STAKES = re.compile(
    r"\b(archiv(?:e|ed|ado|ar)|deleted?|removed?|wired|integrated|registered|done|closed|migrated)\b",
    re.IGNORECASE,
)
HOOK_FILE = re.compile(r"([A-Za-z0-9_.-]+\.sh)\b")
CHECKED = re.compile(r"^\s*-?\s*\[x\]\s+(.*)$", re.IGNORECASE)
VERIFIED = re.compile(r"\(\s*verified\s*:", re.IGNORECASE)
WORK_ID = re.compile(r"\(\s*work_id\s*:\s*([A-Za-z0-9][A-Za-z0-9_.:-]{7,127})\s*\)", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    line: int
    message: str


def _config_refs(root: Path, needle: str) -> list[Path]:
    candidates = [
        root / "cognitive-os.yaml",
        root / ".claude" / "settings.json",
        root / ".codex" / "hooks.json",
    ]
    refs: list[Path] = []
    for path in candidates:
        if path.exists() and needle in _read(path):
            refs.append(path)
    return refs


def _verify_hook_archive(root: Path, hook_name: str) -> list[str]:
    problems: list[str] = []
    archive = root / "docs" / "archive" / "hooks" / hook_name
    original = root / "hooks" / hook_name
    if not archive.exists():
        problems.append(f"archive missing: {archive.relative_to(root)}")
    elif not archive.is_file() or archive.is_symlink():
        problems.append(f"archive is not a regular file: {archive.relative_to(root)}")
    if original.exists():
        problems.append(f"original still exists: {original.relative_to(root)}")
    refs = _config_refs(root, hook_name)
    if refs:
        rels = ", ".join(path.relative_to(root).as_posix() for path in refs)
        problems.append(f"config still references {hook_name}: {rels}")
    return problems


def verify_plan(root: Path, plan: Path) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(_read(plan).splitlines(), start=1):
        m = CHECKED.match(line)
        if not m:
            continue
        claim = m.group(1)
        if not HIGH_STAKES.search(claim):
            continue

        if not VERIFIED.search(line):
            findings.append(
                Finding(
                    lineno,
                    "high-stakes checked claim is missing inline bilateral proof '(verified: ...)'",
                )
            )
        if not WORK_ID.search(line):
            findings.append(
                Finding(
                    lineno,
                    "high-stakes checked claim is missing work identity '(work_id: <hash>)'",
                )
            )

        hook_match = HOOK_FILE.search(claim)
        archive_like = re.search(r"archiv(?:e|ed|ado|ar)", claim, re.IGNORECASE)
        if archive_like and hook_match:
            problems = _verify_hook_archive(root, hook_match.group(1))
            if problems:
                findings.append(Finding(lineno, "; ".join(problems)))
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="plan markdown file to verify")
    parser.add_argument("--project-dir", default=".", help="project root for bilateral filesystem checks")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.project_dir).resolve()
    plan = Path(args.plan)
    if not plan.is_absolute():
        plan = (root / plan).resolve()
    findings = verify_plan(root, plan)
    if findings:
        for finding in findings:
            print(f"FAIL {plan.relative_to(root) if plan.is_relative_to(root) else plan}:{finding.line}: {finding.message}")
        return 2
    print(f"PASS {plan.relative_to(root) if plan.is_relative_to(root) else plan}: high-stakes checked claims verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
