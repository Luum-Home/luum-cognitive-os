#!/usr/bin/env python3
"""Deterministic Definition of Done checker for Codex-local work.

The checker is intentionally conservative and cheap by default: it inspects the
current Git worktree, classifies change complexity, checks high-signal hygiene,
and recommends a smallest validation command for the changed surface. It can run
that command with --run-recommended when the operator wants an executable pass.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    evidence: str


@dataclass(frozen=True)
class Report:
    verdict: str
    complexity: str
    changed_files: list[str]
    recommended_command: str | None
    checks: list[Check]


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False, timeout=timeout)


def changed_files() -> list[str]:
    proc = run(["git", "diff", "--name-only", "HEAD"])
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    proc_untracked = run(["git", "ls-files", "--others", "--exclude-standard"])
    files.extend(line.strip() for line in proc_untracked.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(files))


def classify(files: list[str]) -> str:
    if not files:
        return "trivial"
    lowered = "\n".join(files).lower()
    if any(token in lowered for token in ("secret", "credential", "auth", "payment", "migration", "release", "version")):
        return "critical"
    if len(files) > 10 or any(path.startswith(("cmd/", "packages/", "internal/", "hooks/")) for path in files):
        return "large"
    if len(files) > 3 or any(path.startswith(("rules/", "skills/", ".codex/skills/", ".claude/commands/")) for path in files):
        return "medium"
    return "small"


def recommended_command(files: list[str]) -> str | None:
    if not files:
        return None
    file_set = set(files)
    if any(path.endswith(".sh") or path.startswith("hooks/") for path in file_set):
        hook_files = [path for path in files if path.endswith(".sh")]
        if hook_files:
            return "bash -n " + " ".join(hook_files)
    if any(path.endswith(".py") for path in file_set):
        py_files = [path for path in files if path.endswith(".py")]
        return "python3 -m py_compile " + " ".join(py_files)
    if any(path.startswith(("rules/", "skills/", ".codex/skills/", ".claude/commands/", "AGENTS.md")) for path in file_set):
        return "python3 scripts/prompt_aggressive_language_audit.py " + " ".join(files) + " --fail-debt"
    return "git diff --check"


def file_text(path: str) -> str:
    try:
        return (ROOT / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def check_hygiene(files: list[str]) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check("changed_files_present", "PASS" if files else "WARN", f"{len(files)} changed/untracked file(s)"))
    blocked_paths = [p for p in files if p == ".env" or p.startswith("secrets/") or p.endswith((".pem", ".key")) or p == ".git/config"]
    checks.append(Check("blocked_paths_absent", "PASS" if not blocked_paths else "FAIL", ", ".join(blocked_paths) or "no blocked paths touched"))
    todo_hits: list[str] = []
    for path in files:
        if not path.endswith((".py", ".sh", ".md", ".go", ".ts", ".tsx", ".js", ".jsx")):
            continue
        text = file_text(path)
        for idx, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(" + "TO" + "DO|FIXME|HACK)\b", line):
                todo_hits.append(f"{path}:{idx}")
                break
    checks.append(Check("todo_fixme_absent", "PASS" if not todo_hits else "FAIL", ", ".join(todo_hits) or "no TODO/FIXME/HACK markers in changed text files"))
    return checks


def run_recommended(command: str | None) -> Check:
    if not command:
        return Check("recommended_validation", "WARN", "no changed files; no validation command recommended")
    proc = subprocess.run(command, cwd=ROOT, shell=True, text=True, capture_output=True, check=False, timeout=120)
    evidence = f"exit={proc.returncode}; command={command}"
    if proc.stdout.strip():
        evidence += f"; stdout={proc.stdout.strip()[:200]}"
    if proc.stderr.strip():
        evidence += f"; stderr={proc.stderr.strip()[:200]}"
    return Check("recommended_validation", "PASS" if proc.returncode == 0 else "FAIL", evidence)


def build_report(run_validation: bool = False) -> Report:
    files = changed_files()
    complexity = classify(files)
    command = recommended_command(files)
    checks = check_hygiene(files)
    if command:
        checks.append(Check("recommended_command_present", "PASS", command))
    else:
        checks.append(Check("recommended_command_present", "WARN", "no command recommended for empty worktree"))
    if run_validation:
        checks.append(run_recommended(command))
    statuses = [check.status for check in checks]
    verdict = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return Report(verdict, complexity, files, command, checks)


def markdown(report: Report) -> str:
    lines = [f"## DoD Check: {report.verdict}", f"Complexity: {report.complexity}", ""]
    lines.append(f"Changed files: {len(report.changed_files)}")
    if report.recommended_command:
        lines.append(f"Recommended validation: `{report.recommended_command}`")
    lines.append("\n| Check | Status | Evidence |")
    lines.append("|---|---|---|")
    for check in report.checks:
        evidence = check.evidence.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check.name} | {check.status} | {evidence} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--run-recommended", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true")
    args = parser.parse_args()
    report = build_report(run_validation=args.run_recommended)
    if args.format == "json":
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    if report.verdict == "FAIL" or (args.fail_on_warn and report.verdict == "WARN"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
