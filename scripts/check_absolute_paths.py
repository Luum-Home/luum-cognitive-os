#!/usr/bin/env python3
# SCOPE: both
"""Detect developer-specific absolute home paths in repository text files.

The scanner is intentionally focused on portability/privacy leaks, not every
absolute path in Unix syntax. Container paths may be valid runtime
configuration; developer home paths under a user's home directory should not be
committed to Cognitive OS or to projects that install it.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


MAC_HOME_PREFIX = "/" + "Users" + "/"
LINUX_HOME_PREFIX = "/" + "home" + "/"
WINDOWS_HOME_PATTERN = re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\\\s]+(?:\\\\[^\s`'\"<>)]*)?")
POSIX_PATH_PATTERN = re.compile(
    rf"(?:{re.escape(MAC_HOME_PREFIX)}|{re.escape(LINUX_HOME_PREFIX)})"
    r"[^/\s`'\"<>)]+"  # username segment
    r"(?:/[^\s`'\"<>)]*)?"
)

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

DEFAULT_EXCLUDED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".zip",
    ".gz",
    ".tar",
    ".db",
    ".sqlite",
}

PLACEHOLDER_USER_SEGMENTS = {
    "...",
    "<user>",
    "{user}",
    "$USER",
    "${USER}",
    "USER",
}

ALLOWED_POSIX_PREFIXES = {
    # Container paths, not developer host-home paths.
    LINUX_HOME_PREFIX + "jovyan/",
}

ALLOW_MARKER = "cos-allow-absolute-path"


@dataclass(frozen=True)
class Finding:
    path: Path
    line_number: int
    matched_text: str
    reason: str


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(4096)
    except OSError:
        return True
    return b"\0" in chunk


def _should_skip(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(part in DEFAULT_EXCLUDED_DIRS for part in rel_parts):
        return True
    if path.suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
        return True
    return _is_binary(path)


def _posix_user_segment(match: str) -> str:
    prefix = MAC_HOME_PREFIX if match.startswith(MAC_HOME_PREFIX) else LINUX_HOME_PREFIX
    remainder = match[len(prefix) :]
    return remainder.split("/", 1)[0]


def _is_allowed_match(match: str) -> bool:
    if any(match.startswith(prefix) for prefix in ALLOWED_POSIX_PREFIXES):
        return True
    if match.startswith(MAC_HOME_PREFIX) or match.startswith(LINUX_HOME_PREFIX):
        return _posix_user_segment(match) in PLACEHOLDER_USER_SEGMENTS
    return False


def scan_file(path: Path, root: Path) -> list[Finding]:
    if _should_skip(path, root):
        return []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        try:
            lines = path.read_text(encoding="latin-1").splitlines()
        except UnicodeDecodeError:
            return []
    except OSError:
        return []

    findings: list[Finding] = []
    for line_number, line in enumerate(lines, start=1):
        if ALLOW_MARKER in line:
            continue
        for match in POSIX_PATH_PATTERN.findall(line):
            if not _is_allowed_match(match):
                findings.append(
                    Finding(
                        path=path,
                        line_number=line_number,
                        matched_text=match,
                        reason="developer home path",
                    )
                )
        for match in WINDOWS_HOME_PATTERN.findall(line):
            findings.append(
                Finding(
                    path=path,
                    line_number=line_number,
                    matched_text=match,
                    reason="Windows developer home path",
                )
            )
    return findings


def git_deleted_from_index(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=D"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def git_tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    deleted = git_deleted_from_index(root)
    return [line for line in result.stdout.splitlines() if line and line not in deleted]


def iter_files(root: Path, paths: list[str]) -> list[Path]:
    if paths:
        result: list[Path] = []
        for raw in paths:
            path = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
            if path.is_file():
                result.append(path)
            elif path.is_dir():
                result.extend(p for p in path.rglob("*") if p.is_file())
        return result
    tracked = git_tracked_files(root)
    if tracked:
        return [(root / p).resolve() for p in tracked if (root / p).is_file()]
    if is_git_repository(root):
        return []
    return [p for p in root.rglob("*") if p.is_file()]



def is_git_repository(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"

def staged_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--raw", "--diff-filter=ACM"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        meta, _, raw_path = line.partition("\t")
        if not raw_path:
            continue
        fields = meta.split()
        if len(fields) < 4:
            continue
        new_mode = fields[1]
        if new_mode == "160000":
            continue
        paths.append(raw_path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan for developer-specific absolute home paths."
    )
    parser.add_argument("paths", nargs="*", help="Files or directories to scan.")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan staged files only.",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Scan every file under root instead of only git-tracked files.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root. Defaults to current directory.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.staged:
        raw_paths = staged_files(root)
    elif args.all_files:
        raw_paths = [str(root)]
    else:
        raw_paths = args.paths
    findings: list[Finding] = []
    for path in iter_files(root, raw_paths):
        try:
            path.relative_to(root)
        except ValueError:
            continue
        findings.extend(scan_file(path, root))

    if findings:
        for finding in findings:
            rel = finding.path.relative_to(root)
            print(
                f"{rel}:{finding.line_number}: {finding.reason}: "
                f"{finding.matched_text}",
                file=sys.stderr,
            )
        print(
            "\nBLOCKED: developer-specific absolute home paths are not portable. "
            "Use repo-relative paths, $PROJECT_DIR, $HOME, or placeholders such "
            "as <repo-root> instead.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
