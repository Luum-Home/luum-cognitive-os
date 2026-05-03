#!/usr/bin/env python3
# SCOPE: both
"""Block shell snippets that pipe data into `python - <<HEREDOC`.

That pattern is broken because the heredoc is consumed as the Python program on
stdin, so the piped data is not available to `sys.stdin`. Use `python -c`, a temp
file, process substitution, or pass a filename argument to `python -` instead.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
ANTI_PATTERN = re.compile(r"\|\s*python(?:3(?:\.\d+)?)?\s+-\s*<<")
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".sqlite", ".db"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    text: str
    message: str


def tracked_files(root: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return sorted(path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts)
    return [root / line for line in proc.stdout.splitlines() if line]


def scan_file(path: Path, root: Path) -> list[Finding]:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if "cos: allow-python-stdin-heredoc-example" in line:
            continue
        if ANTI_PATTERN.search(line):
            findings.append(
                Finding(
                    path=str(path.relative_to(root)),
                    line=idx,
                    text=line.strip()[:240],
                    message="Pipe into `python - <<HEREDOC` drops the piped stdin; use `python -c` or pass a file argument.",
                )
            )
    return findings


def scan(root: Path = REPO_ROOT, files: Iterable[Path] | None = None) -> list[Finding]:
    candidates = list(files) if files is not None else tracked_files(root)
    findings: list[Finding] = []
    for path in candidates:
        findings.extend(scan_file(path, root))
    return findings


def build_report(root: Path = REPO_ROOT) -> dict:
    findings = scan(root)
    return {
        "status": "fail" if findings else "pass",
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "policy": "Never pipe data into `python - <<HEREDOC`; heredoc owns stdin.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"python-stdin-antipattern-audit: {report['status']} findings={report['finding_count']}")
        for finding in report["findings"][:20]:
            print(f"- {finding['path']}:{finding['line']}: {finding['message']}")
    if args.fail_on_findings and report["finding_count"]:
        return 1
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
