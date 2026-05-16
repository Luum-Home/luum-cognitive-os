#!/usr/bin/env python3
# SCOPE: os-only
"""Audit repository text for English-only content.

This audit scans repository text for signals that content is written in a
human language other than English. It is heuristic by design: deterministic CI
coverage catches obvious drift, while allow markers preserve intentional test
fixtures and protocol examples.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import json
import re
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA_VERSION = "english-only-content-audit/v1"

TEXT_SUFFIXES = {
    "", ".adoc", ".bats", ".c", ".cfg", ".conf", ".css", ".go", ".h",
    ".html", ".ini", ".js", ".json", ".jsonl", ".jsx", ".md", ".mdx",
    ".py", ".rs", ".sh", ".sql", ".toml", ".ts", ".tsx", ".txt",
    ".yaml", ".yml",
}

DEFAULT_EXCLUDE_GLOBS = (
    ".git/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.venv/**",
    "**/node_modules/**",
)

# Base64 keeps the detector corpus out of repository prose while preserving
# runtime matching for forbidden non-English natural-language signals.
NON_ENGLISH_TERMS_B64 = (
    # Romance-language and operator-prompt terms observed in this repository.
    "YWRlbcOhcw==", "YWdyZWfDoQ==", "YWdyZWdhcg==", "YWdyZWd1ZW1vcw==",
    "YWxndWllbg==", "YW7DoWxpc2lz", "YXJyZWdsw6E=", "YXJyZWdsYXI=",
    "YXPDrQ==", "YXV0b23DoXRpY28=", "Ym9ycsOh", "Ym9ycmFy", "YnVlbmFz",
    "Y8OzZGlnbw==", "Y8OzbW8=", "Y29uc3RydWNjacOzbg==", "Y3XDoWw=",
    "Y3XDoWxlcw==", "ZGViZXLDrWE=", "ZGViZXLDrWFu", "ZGVjaXNpw7Nu",
    "ZGVzYXJyb2xsYWRvcg==", "ZG9jdW1lbnRhY2nDs24=", "ZMOzbmRl",
    "ZWplY3V0w6E=", "ZW4gZXNwYcOxb2w=", "ZXNwYcOxb2w=", "ZXN0w6E=",
    "ZXN0w6Fu", "ZXN0bw==", "ZXh0cmHDrWRv", "aGFjw6k=", "aGFnYW1vcw==",
    "aGVycmFtaWVudGE=", "aGVycmFtaWVudGFz", "aW52ZXN0aWdhY2nDs24=",
    "aW52ZXN0aWfDoQ==", "bMOtbmVh", "bcOhcw==", "bmVjZXNpdG8=",
    "bmluZ8O6bg==", "b3JxdWVzdGFjacOzbg==", "cGFsYWJyZXLDrWE=",
    "cG9kw6lz", "cG9kcsOtYXM=", "cHLDoWN0aWNhcw==", "cXXDqQ==",
    "cXVlZMOz", "cXVlcsOpcw==", "cmV2aXPDoQ==", "c2VzacOzbg==",
    "c8OtbnRlc2lz", "c29sdWNpb25lbW9z", "dGFtYmnDqW4=", "dMOpY25pY28=",
    "dG9kYXbDrWE=", "w7puaWNv", "dXPDoQ==", "dsOtYQ==",
    # Additional common non-English stop/content words.
    "Ym9uam91cg==", "bWVyY2k=", "bW9uc2lldXI=", "bWFkYW1l", "cG91cnF1b2k=",
    "YXVmZ2FiZQ==", "Yml0dGU=", "ZGFua2U=", "d2ljaHRpZw==",
    "c2NobmVsbA==", "Z3Jhemll", "cHJlZ28=", "cGVyY2jDqA==", "YWRlc3Nv",
    "b2JyaWdhZG8=", "b2JyaWdhZGE=", "cG9ycXVl", "cXVhbmRv", "ZmVjaGFy",
)

FORBIDDEN_PUNCTUATION = "".join(chr(code) for code in (0x00A1, 0x00BF))


def _decode_terms(encoded_terms: Iterable[str]) -> tuple[str, ...]:
    return tuple(base64.b64decode(term).decode("utf-8") for term in encoded_terms)


NON_ENGLISH_TERMS = _decode_terms(NON_ENGLISH_TERMS_B64)
NON_ENGLISH_TERM_RE = re.compile(
    r"(?<!\w)(?:"
    + "|".join(re.escape(term) for term in sorted(NON_ENGLISH_TERMS, key=len, reverse=True))
    + r")(?!\w)",
    re.IGNORECASE,
)
FORBIDDEN_PUNCTUATION_RE = re.compile("[" + re.escape(FORBIDDEN_PUNCTUATION) + "]")
ALLOW_MARKERS = (
    "english-only-content-audit: allow",
    "non-english-content-audit: allow",
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    file: str
    line: int
    evidence: str
    message: str


@dataclass(frozen=True)
class Report:
    schema_version: str
    root: str
    scanned_files: int
    finding_count: int
    findings: tuple[Finding, ...]


def run_git_ls_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [p for p in proc.stdout.decode("utf-8", errors="ignore").split("\0") if p]


def discover_files(root: Path, include_untracked: bool = False) -> list[str]:
    tracked = run_git_ls_files(root)
    if not include_untracked:
        return tracked
    seen = set(tracked)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel not in seen:
            tracked.append(rel)
            seen.add(rel)
    return tracked


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in chunk


def excluded(rel_path: str, exclude_globs: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_globs)


def line_allowed(line: str, previous: str, following: str) -> bool:
    window = "\n".join((previous, line, following))
    return any(marker in window for marker in ALLOW_MARKERS)


def first_non_ascii_letter(line: str) -> str | None:
    for char in line:
        if not char.isalpha() or ord(char) < 128:
            continue
        return char
    return None


def first_non_latin_letter(line: str) -> str | None:
    for char in line:
        if not char.isalpha() or ord(char) < 128:
            continue
        try:
            name = unicodedata.name(char)
        except ValueError:
            return char
        if "LATIN" not in name:
            return char
    return None


def classify_line(line: str) -> tuple[str, str, str] | None:
    script_match = first_non_latin_letter(line)
    if script_match is not None:
        return ("non-english-script", "error", script_match)

    term_match = NON_ENGLISH_TERM_RE.search(line)
    if term_match:
        return ("non-english-term", "error", term_match.group(0))

    punctuation_match = FORBIDDEN_PUNCTUATION_RE.search(line)
    if punctuation_match:
        return ("non-english-punctuation", "error", punctuation_match.group(0))

    non_ascii_letter = first_non_ascii_letter(line)
    if non_ascii_letter is not None:
        return ("non-ascii-letter", "error", non_ascii_letter)
    return None


def _finding_for_line(rel_path: str, line_no: int, line: str) -> Finding | None:
    classified = classify_line(line)
    if classified is None:
        return None
    code, severity, evidence = classified
    return Finding(
        code=code,
        severity=severity,
        file=rel_path,
        line=line_no,
        evidence=evidence,
        message="Non-English-language signal found in repository text.",
    )


def scan_file(root: Path, rel_path: str) -> list[Finding]:
    path = root / rel_path
    if not is_probably_text(path):
        return []

    findings: list[Finding] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            previous = ""
            pending_line_no = 0
            pending_line = ""
            for line_no, raw_line in enumerate(handle, 1):
                line = raw_line.rstrip("\n")
                if pending_line_no and not line_allowed(pending_line, previous, line):
                    finding = _finding_for_line(rel_path, pending_line_no, pending_line)
                    if finding is not None:
                        findings.append(finding)
                previous = pending_line
                pending_line_no = line_no
                pending_line = line
            if pending_line_no and not line_allowed(pending_line, previous, ""):
                finding = _finding_for_line(rel_path, pending_line_no, pending_line)
                if finding is not None:
                    findings.append(finding)
    except OSError:
        return []
    return findings


def audit(root: Path, *, include_untracked: bool = False, exclude_globs: Sequence[str] = ()) -> Report:
    root = root.resolve()
    all_excludes = tuple(DEFAULT_EXCLUDE_GLOBS) + tuple(exclude_globs)
    scanned_files = 0
    findings: list[Finding] = []
    for rel_path in discover_files(root, include_untracked=include_untracked):
        if excluded(rel_path, all_excludes):
            continue
        path = root / rel_path
        if not path.is_file() or not is_probably_text(path):
            continue
        scanned_files += 1
        findings.extend(scan_file(root, rel_path))
    return Report(
        schema_version=SCHEMA_VERSION,
        root=str(root),
        scanned_files=scanned_files,
        finding_count=len(findings),
        findings=tuple(findings),
    )


def report_to_markdown(report: Report) -> str:
    lines = [
        "# English-only Content Audit",
        "",
        f"Schema: `{report.schema_version}`",
        f"Root: `{report.root}`",
        f"Scanned files: **{report.scanned_files}**",
        f"Findings: **{report.finding_count}**",
        "",
    ]
    if not report.findings:
        lines.append("No non-English-language signals found.")
        return "\n".join(lines) + "\n"

    lines.extend([
        "| Severity | Code | Location | Evidence |",
        "|---|---|---|---|",
    ])
    for finding in report.findings:
        evidence = finding.evidence.replace("|", "\\|")
        lines.append(
            f"| {finding.severity} | {finding.code} | `{finding.file}:{finding.line}` | `{evidence}` |"
        )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit repository text for English-only content.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument("--include-untracked", action="store_true", help="Also scan untracked files")
    parser.add_argument("--exclude-glob", action="append", default=[], help="Additional glob to exclude")
    parser.add_argument("--no-fail", action="store_true", help="Always exit 0 after reporting")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = audit(
        Path(args.root),
        include_untracked=args.include_untracked,
        exclude_globs=args.exclude_glob,
    )
    if args.json:
        payload = asdict(report)
        payload["findings"] = [asdict(finding) for finding in report.findings]
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(report_to_markdown(report), end="")

    if args.no_fail:
        return 0
    return 1 if report.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
