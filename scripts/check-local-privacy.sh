#!/usr/bin/env bash
# SCOPE: both
# check-local-privacy.sh — block local operator privacy leaks before commit.
#
# This scanner complements check_absolute_paths.py. It blocks generic local
# home paths and high-risk key filenames by default, and it can also load
# operator/project-specific private patterns from a gitignored file:
#   .cognitive-os/private/local-privacy-patterns.txt
#
# Pattern file format:
#   literal: exact text to match
#   regex: extended regular expression to match
#   bare lines are treated as literal strings
#
# Exit codes:
#   0 — no violations
#   1 — privacy violations found
#   2 — usage/runtime error
set -euo pipefail

exec python3 - "$@" <<'PYEOF'
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOW_MARKER = "cos-allow-local-privacy-pattern"
MAC_HOME_PREFIX = "/" + "Users" + "/"
LINUX_HOME_PREFIX = "/" + "home" + "/"
POSIX_HOME_RE = re.compile(
    rf"(?:{re.escape(MAC_HOME_PREFIX)}|{re.escape(LINUX_HOME_PREFIX)})"
    r"[^/\s`'\"<>)]+"  # username segment
    r"(?:/[^\s`'\"<>)]*)?"
)
WINDOWS_HOME_RE = re.compile(r"[A-Za-z]:\\Users\\[^\s`'\"<>)]*(?:\\[^\s`'\"<>)]*)?")

PLACEHOLDER_USERS = {"<user>", "{user}", "$USER", "${USER}", "USER", "..."}
ALLOWED_POSIX_PREFIXES = {LINUX_HOME_PREFIX + "jovyan/"}
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "target",
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
    ".pyc",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line_number: int
    reason: str
    matched_text: str


@dataclass(frozen=True)
class PrivatePattern:
    kind: str
    pattern: str
    regex: re.Pattern[str] | None = None


def run_git(root: Path, args: list[str], *, text: bool = True) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=text,
        capture_output=True,
        check=False,
        timeout=60,
    )


def is_git_repository(root: Path) -> bool:
    result = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and str(result.stdout).strip() == "true"


def git_deleted_from_index(root: Path) -> set[str]:
    result = run_git(root, ["diff", "--cached", "--name-only", "--diff-filter=D"])
    if result.returncode != 0:
        return set()
    return {line for line in str(result.stdout).splitlines() if line}


def git_tracked_files(root: Path) -> list[str]:
    result = run_git(root, ["ls-files"])
    if result.returncode != 0:
        return []
    deleted = git_deleted_from_index(root)
    return [line for line in str(result.stdout).splitlines() if line and line not in deleted]


def staged_files(root: Path) -> list[str]:
    result = run_git(root, ["diff", "--cached", "--raw", "-M", "-C", "--diff-filter=ACM"])
    if result.returncode != 0:
        return []

    files: list[str] = []
    for line in str(result.stdout).splitlines():
        if not line:
            continue
        meta, _, raw_path = line.partition("\t")
        if not raw_path:
            continue
        fields = meta.split()
        if len(fields) >= 4 and fields[1] == "160000":
            continue
        files.append(raw_path.split("\t")[-1])
    return files


def should_skip(path: Path, root: Path, content: bytes | None = None) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    if any(part in DEFAULT_EXCLUDED_DIRS for part in rel_parts):
        return True
    if path.suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
        return True
    if content is None:
        try:
            content = path.read_bytes()[:4096]
        except OSError:
            return True
    return b"\0" in content[:4096]


def decode_text(content: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def posix_user_segment(match: str) -> str:
    prefix = MAC_HOME_PREFIX if match.startswith(MAC_HOME_PREFIX) else LINUX_HOME_PREFIX
    return match[len(prefix) :].split("/", 1)[0]


def is_allowed_posix_home(match: str) -> bool:
    if any(match.startswith(prefix) for prefix in ALLOWED_POSIX_PREFIXES):
        return True
    return posix_user_segment(match) in PLACEHOLDER_USERS


def load_private_patterns(path: Path) -> list[PrivatePattern]:
    if not path.is_file():
        return []
    patterns: list[PrivatePattern] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("literal:"):
            patterns.append(PrivatePattern(kind="literal", pattern=line.removeprefix("literal:")))
        elif line.startswith("regex:"):
            pattern = line.removeprefix("regex:")
            try:
                patterns.append(PrivatePattern(kind="regex", pattern=pattern, regex=re.compile(pattern)))
            except re.error as exc:
                print(f"ERROR: invalid private regex in {path}: {pattern}: {exc}", file=sys.stderr)
                raise SystemExit(2)
        else:
            patterns.append(PrivatePattern(kind="literal", pattern=line))
    return patterns


def scan_text(path: Path, root: Path, text: str, private_patterns: list[PrivatePattern]) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for match in POSIX_HOME_RE.findall(line):
            if not is_allowed_posix_home(match):
                findings.append(Finding(path, line_number, "developer home path", match))
        for match in WINDOWS_HOME_RE.findall(line):
            findings.append(Finding(path, line_number, "Windows developer home path", match))
        for private in private_patterns:
            if private.kind == "literal" and private.pattern and private.pattern in line:
                findings.append(Finding(path, line_number, "private literal pattern", private.pattern))
            elif private.kind == "regex" and private.regex and private.regex.search(line):
                findings.append(Finding(path, line_number, "private regex pattern", private.pattern))
    return findings


def scan_file(path: Path, root: Path, private_patterns: list[PrivatePattern]) -> list[Finding]:
    try:
        content = path.read_bytes()
    except OSError:
        return []
    if should_skip(path, root, content):
        return []
    text = decode_text(content)
    if text is None:
        return []
    return scan_text(path, root, text, private_patterns)


def scan_staged(root: Path, private_patterns: list[PrivatePattern]) -> list[Finding]:
    findings: list[Finding] = []
    for rel in staged_files(root):
        path = root / rel
        result = run_git(root, ["show", f":{rel}"], text=False)
        if result.returncode != 0:
            continue
        content = bytes(result.stdout)
        if should_skip(path, root, content):
            continue
        text = decode_text(content)
        if text is None:
            continue
        findings.extend(scan_text(path, root, text, private_patterns))
    return findings


def iter_paths(root: Path, raw_paths: list[str], all_files: bool) -> list[Path]:
    if all_files:
        if is_git_repository(root):
            return [(root / rel).resolve() for rel in git_tracked_files(root) if (root / rel).is_file()]
        return [p for p in root.rglob("*") if p.is_file()]
    if not raw_paths:
        return iter_paths(root, [], True)
    files: list[Path] = []
    for raw in raw_paths:
        path = Path(raw) if Path(raw).is_absolute() else root / raw
        if path.is_file():
            files.append(path.resolve())
        elif path.is_dir():
            files.extend(p.resolve() for p in path.rglob("*") if p.is_file())
    return files


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scan for local privacy leaks before commit.")
    parser.add_argument("paths", nargs="*", help="Files or directories to scan.")
    parser.add_argument("--root", default=None, help="Repository root. Defaults to git root or cwd.")
    parser.add_argument("--staged", action="store_true", help="Scan staged files only.")
    parser.add_argument("--all", "--all-files", action="store_true", dest="all_files", help="Scan all tracked files under root.")
    args = parser.parse_args(argv)

    if args.root:
        root = Path(args.root).resolve()
    else:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)
        root = Path(result.stdout.strip()).resolve() if result.returncode == 0 else Path.cwd().resolve()

    pattern_path = Path(os.environ.get("COS_LOCAL_PRIVACY_PATTERNS_FILE", root / ".cognitive-os/private/local-privacy-patterns.txt"))
    private_patterns = load_private_patterns(pattern_path)

    if args.staged:
        if not is_git_repository(root):
            print("ERROR: --staged requires a git repository", file=sys.stderr)
            return 2
        findings = scan_staged(root, private_patterns)
    else:
        findings = []
        for path in iter_paths(root, args.paths, args.all_files):
            findings.extend(scan_file(path, root, private_patterns))

    if findings:
        for finding in sorted(set(findings), key=lambda item: (str(item.path), item.line_number, item.reason, item.matched_text)):
            rel = finding.path.relative_to(root)
            print(f"{rel}:{finding.line_number}: {finding.reason}: {finding.matched_text}", file=sys.stderr)
        print(
            "\nBLOCKED: local privacy guard found host/user/project-specific content.\n"
            "Use repo-relative paths, $PROJECT_DIR, $HOME, placeholders, or move private\n"
            "patterns into .cognitive-os/private/local-privacy-patterns.txt.",
            file=sys.stderr,
        )
        return 1

    print("privacy-guard-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PYEOF
