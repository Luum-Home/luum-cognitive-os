#!/usr/bin/env python3
"""Audit Engram command shapes used by COS docs/code.

The audit intentionally flags stale commands that Engram v1.15.x does not
support as documented product/runtime commands. Negative explanatory mentions
such as "does not expose `engram delete`" are allowed.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["docs", "scripts", "hooks", "packages", "lib", "mcp-server", "tests"]


@dataclass
class Finding:
    path: str
    line: int
    pattern: str
    text: str


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("engram-search-json", re.compile(r"engram\s+search\s+--json")),
    ("engram-save-json", re.compile(r"engram\s+save\s+--json")),
    ("engram-save-title-content", re.compile(r"engram\s+save\b.*--title\b.*--content\b")),
    ("engram-topic-key-flag", re.compile(r"--topic-key\b")),
    ("engram-search-query-flag", re.compile(r"engram\s+search\s+--query\b")),
    ("engram-get-json", re.compile(r"engram\s+get\s+--json")),
    ("engram-delete-cli", re.compile(r"engram\s+delete\b")),
    ("engram-cloud-delete-cli", re.compile(r"engram\s+cloud\s+delete\b")),
]


ALLOW_NEGATIVE = (
    "does not expose",
    "unsupported",
    "do not add",
    "non-contract",
    "nonexistent",
    "NO `--json`",
    "rejected",
)


def is_allowed_negative(line: str) -> bool:
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in ALLOW_NEGATIVE)


def is_allowed_context(path: Path, line: str) -> bool:
    relative = str(path.relative_to(ROOT))
    if relative in {
        "scripts/cos_engram_command_audit.py",
        "tests/audit/test_engram_command_contract.py",
    }:
        return True
    if relative == "docs/04-Concepts/architecture/engram-command-contract.md" and line.lstrip().startswith("- `"):
        return True
    return False


def iter_files() -> list[Path]:
    paths: list[Path] = []
    for dirname in SCAN_DIRS:
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            if path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
                continue
            paths.append(path)
    return sorted(paths)


def audit() -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            for name, pattern in PATTERNS:
                if pattern.search(line) and not is_allowed_negative(line) and not is_allowed_context(path, line):
                    findings.append(
                        Finding(
                            path=str(path.relative_to(ROOT)),
                            line=index,
                            pattern=name,
                            text=line.strip(),
                        )
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    findings = audit()
    payload = {
        "status": "fail" if findings else "pass",
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['status']}: {payload['finding_count']} Engram command contract finding(s)")
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.pattern}: {finding.text}")
    if args.fail_on_findings and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
