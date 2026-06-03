#!/usr/bin/env python3
# SCOPE: both
"""Audit prompt-style aggressive language in model-facing repository surfaces.

The audit separates allowed protocol/security/severity wording from likely
prompt-style overtrigger debt. It is intentionally conservative: it reports debt
with file and line context, and callers decide whether to fail with --fail-debt.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMS = ("IMPORTANT", "CRITICAL", "MUST", "NEVER", "ALWAYS", "DO NOT", "DON'T")
DEFAULT_PATHS = (
    "AGENTS.md",
    "rules",
    "skills",
    ".codex/skills",
    ".claude/commands",
    "hooks",
)
TEXT_SUFFIXES = {".md", ".sh", ".txt"}

ALLOW_PATTERNS = [
    re.compile(r"\bcritical_radius\b", re.I),
    re.compile(r"\bnon-critical\b", re.I),
    re.compile(r"\b(radius|severity|complexity|non-critical|critical findings|security)\b.*\bcritical\b", re.I),
    re.compile(r"\bcritical\b.*\b(radius|severity|complexity|findings|security)\b", re.I),
    re.compile(r"\balways-active\b", re.I),
    re.compile(r"\balways active\b", re.I),
    re.compile(r"\bdo not use when\b", re.I),  # skill frontmatter boundary language.
    re.compile(r"\bnever\b.*\bnot\b.*\bdo not\b", re.I),  # quoted negation-preservation examples.
    re.compile(r"\b(blocked paths|credentials|secrets|\.env|private key|license|agpl|sspl|bsl|elv2)\b", re.I),
    re.compile(r"\bIDE hooks do not fire in service mode\b", re.I),
    re.compile(r"\b(exit|return|status|severity|enum|protocol|metric|jsonl|yaml|config|error|warning)\b", re.I),
    re.compile(r"\bmust\b.*\b(fix|parse|exist|runnable|positive|valid|register|follow)\b", re.I),
]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    term: str
    classification: str
    text: str


def git_tracked_files() -> set[str]:
    proc = subprocess.run(
        ["git", "ls-files", *DEFAULT_PATHS],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return set()
    return {line for line in proc.stdout.splitlines() if line}


def is_text_surface(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name == "AGENTS.md"


def is_default_surface(rel: str) -> bool:
    return any(rel == raw or rel.startswith(raw.rstrip("/") + "/") for raw in DEFAULT_PATHS)


def changed_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", *DEFAULT_PATHS],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()] if proc.returncode == 0 else []
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *DEFAULT_PATHS],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if untracked.returncode == 0:
        paths.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(path for path in paths if is_default_surface(path) and is_text_surface(ROOT / path)))


def iter_files(paths: list[str]) -> list[Path]:
    selected: list[Path] = []
    tracked = git_tracked_files()
    for raw in paths:
        p = (ROOT / raw).resolve()
        if not p.exists():
            continue
        if p.is_file():
            selected.append(p)
            continue
        for child in sorted(p.rglob("*")):
            if not child.is_file():
                continue
            rel = child.relative_to(ROOT).as_posix()
            if tracked and rel not in tracked:
                continue
            if is_text_surface(child):
                selected.append(child)
    return selected


def classify(line: str) -> str:
    if any(pattern.search(line) for pattern in ALLOW_PATTERNS):
        return "allowed"
    return "debt"


def audit(paths: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(paths):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(lines, 1):
            upper = line.upper()
            for term in TERMS:
                if term in upper:
                    findings.append(Finding(rel, number, term, classify(line), line.strip()))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-debt", action="store_true")
    parser.add_argument("--changed", action="store_true", help="audit only changed/untracked model-facing files under the default surfaces")
    args = parser.parse_args()

    paths = changed_paths() if args.changed else args.paths
    findings = audit(paths)
    debt = [f for f in findings if f.classification == "debt"]
    allowed = [f for f in findings if f.classification == "allowed"]
    report = {
        "status": "FAIL" if debt and args.fail_debt else "PASS",
        "total": len(findings),
        "allowed": len(allowed),
        "debt": len(debt),
        "paths": paths,
        "findings": [asdict(f) for f in findings],
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"prompt-aggressive-language-audit: total={len(findings)} allowed={len(allowed)} debt={len(debt)}")
        for f in debt[:100]:
            print(f"DEBT {f.path}:{f.line}: {f.term}: {f.text}")
        if len(debt) > 100:
            print(f"... {len(debt) - 100} more debt finding(s)")
    return 1 if debt and args.fail_debt else 0


if __name__ == "__main__":
    raise SystemExit(main())
