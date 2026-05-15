#!/usr/bin/env python3
# SCOPE: both
"""Audit unsafe Git stash recovery instructions.

The audit is intentionally about operator instructions and automation snippets,
not about tests that reproduce stash drift. It flags two classes:

- bare `git stash apply`, `git stash pop`, or `git stash drop` without an
  explicit reviewed target;
- positional `stash@{N}` references in non-forensic guidance.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

BARE_STASH_RE = re.compile(r"\bgit\s+stash\s+(apply|pop|drop)\b(?P<tail>[^`\n]*)")
POSITIONAL_REF_RE = re.compile(r"stash@\{\d+\}")
FORENSIC_WORDS = re.compile(r"\b(test|fixture|forensic|example|reproduce|reproduction|drift|position|positional|transient|not identity|do not|don\'t|bare|without|unsafe|pattern)\b", re.I)
DEFAULT_EXCLUDE_PARTS = {".git", ".venv", "node_modules", "__pycache__"}
DEFAULT_EXTENSIONS = {".md", ".sh", ".py", ".txt", ".yaml", ".yml"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    code: str
    severity: str
    message: str
    text: str


def _is_scannable(path: Path) -> bool:
    if not path.is_file():
        return False
    if any(part in DEFAULT_EXCLUDE_PARTS for part in path.parts):
        return False
    return path.suffix in DEFAULT_EXTENSIONS or path.name.startswith("cos-")


def _iter_paths(root: Path, explicit: list[str]) -> Iterable[Path]:
    if explicit:
        for item in explicit:
            path = (root / item).resolve() if not Path(item).is_absolute() else Path(item)
            if path.is_dir():
                yield from (p for p in path.rglob("*") if _is_scannable(p))
            elif _is_scannable(path):
                yield path
        return
    for base in ("hooks", "scripts", "rules", "skills", "docs", "lib"):
        folder = root / base
        if folder.exists():
            yield from (p for p in folder.rglob("*") if _is_scannable(p))


def _line_is_forensic(path: Path, line: str) -> bool:
    normalized = str(path).replace("\\", "/")
    if "/tests/" in f"/{normalized}" or normalized.startswith("tests/"):
        return True
    return bool(FORENSIC_WORDS.search(line))


def audit(root: Path, paths: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[Path] = set()
    for path in _iter_paths(root, paths):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, 1):
            stripped = line.strip()
            bare_match = BARE_STASH_RE.search(line)
            if bare_match and not _line_is_forensic(path, line):
                tail = bare_match.group("tail").strip()
                has_reviewed_target = any(token in tail for token in ("<reviewed", "reviewed-stash", "$stash_ref", "${stash_ref}", "<ref", "<sha", "<reviewed-stash-ref-or-sha>"))
                if not has_reviewed_target:
                    findings.append(
                        Finding(
                            path=rel,
                            line=index,
                            code="bare-stash-operation",
                            severity="error",
                            message="Use an inspected explicit stash target; do not instruct bare stash apply/pop/drop.",
                            text=stripped,
                        )
                    )
            if POSITIONAL_REF_RE.search(line) and not _line_is_forensic(path, line):
                findings.append(
                    Finding(
                        path=rel,
                        line=index,
                        code="positional-stash-reference",
                        severity="warning",
                        message="Do not use stash@{N} as durable identity outside forensic examples/tests.",
                        text=stripped,
                    )
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Optional files or directories to scan; defaults to OS docs/code surfaces.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail", action="store_true", help="Exit non-zero when findings are present.")
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve()
    findings = audit(root, args.paths)
    payload = {
        "schema_version": "stash-quarantine-audit/v1",
        "project_dir": str(root),
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if not findings:
            print("PASS stash quarantine audit: no unsafe stash guidance found")
        else:
            for item in findings:
                print(f"{item.severity.upper()} {item.path}:{item.line} {item.code}: {item.message}")
    return 1 if args.fail and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
