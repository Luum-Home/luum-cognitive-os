#!/usr/bin/env python3
# SCOPE: os-only
"""ADR-220 worktree divergence audit.

Read-only audit that compares linked git worktrees against a reference branch and
reports silent divergence / pending path conflicts before agents or operators act
on stale worktree state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    worktree: str
    subject: str
    detail: str
    action: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "worktree": self.worktree,
            "subject": self.subject,
            "detail": self.detail,
            "action": self.action,
        }


def git(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )


def _ok(cwd: Path, args: list[str]) -> str | None:
    result = git(cwd, args)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def repo_root(project_dir: Path) -> Path:
    root = _ok(project_dir, ["rev-parse", "--show-toplevel"])
    if not root:
        raise SystemExit(f"not a git worktree: {project_dir}")
    return Path(root).resolve()


def resolve_reference(project: Path, explicit: str | None = None) -> str:
    candidates = [explicit] if explicit else ["origin/main", "main", "@{upstream}"]
    for ref in candidates:
        if not ref:
            continue
        if git(project, ["rev-parse", "--verify", f"{ref}^{{commit}}"]).returncode == 0:
            return ref
    raise SystemExit("could not resolve reference branch (tried origin/main, main, @{upstream})")


def parse_worktrees(project: Path) -> list[dict[str, str]]:
    result = git(project, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git worktree list failed")
    out: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line:
            if current:
                out.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        out.append(current)
    return out


def branch_name(worktree: dict[str, str]) -> str | None:
    branch = worktree.get("branch", "")
    if branch.startswith("refs/heads/"):
        return branch.removeprefix("refs/heads/")
    return None


def dirty_paths(worktree_path: Path) -> set[str]:
    result = git(worktree_path, ["status", "--porcelain=v1", "--untracked-files=all"])
    if result.returncode != 0:
        return set()
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        raw = line[3:]
        if " -> " in raw:
            old, new = raw.split(" -> ", 1)
            paths.add(old.strip())
            paths.add(new.strip())
        else:
            paths.add(raw.strip())
    return {p for p in paths if p}


def changed_paths(project: Path, older_ref: str, newer_ref: str) -> set[str]:
    result = git(project, ["diff", "--name-only", f"{older_ref}..{newer_ref}"])
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def ahead_behind(project: Path, left: str, right: str) -> tuple[int, int] | None:
    result = git(project, ["rev-list", "--left-right", "--count", f"{left}...{right}"])
    if result.returncode != 0:
        return None
    parts = result.stdout.split()
    if len(parts) != 2:
        return None
    return int(parts[0]), int(parts[1])


def audit(project_dir: Path, *, against: str | None = None) -> dict[str, Any]:
    project = repo_root(project_dir)
    reference = resolve_reference(project, against)
    findings: list[Finding] = []
    items: list[dict[str, Any]] = []

    for wt in parse_worktrees(project):
        path = Path(wt.get("worktree", "")).resolve()
        branch = branch_name(wt)
        head = wt.get("HEAD", "")
        item: dict[str, Any] = {
            "path": str(path),
            "branch": branch,
            "head": head,
            "reference": reference,
            "ahead": None,
            "behind": None,
            "dirty_paths": [],
            "reference_changed_paths": [],
            "overlap_paths": [],
        }
        if not branch:
            items.append(item)
            continue
        counts = ahead_behind(project, branch, reference)
        if counts is None:
            findings.append(
                Finding(
                    "WARN",
                    "worktree-divergence-unknown",
                    str(path),
                    branch,
                    f"Could not compare branch '{branch}' against '{reference}'.",
                    "Inspect refs manually before launching write-capable agents.",
                )
            )
            items.append(item)
            continue
        ahead, behind = counts
        dirty = dirty_paths(path)
        ref_changed: set[str] = {str(p) for p in changed_paths(project, branch, reference)} if behind else set()
        overlap = dirty & ref_changed
        item.update(
            {
                "ahead": ahead,
                "behind": behind,
                "dirty_paths": sorted(dirty),
                "reference_changed_paths": sorted(ref_changed),
                "overlap_paths": sorted(overlap),
            }
        )
        if overlap:
            findings.append(
                Finding(
                    "BLOCK",
                    "path-conflict-pending",
                    str(path),
                    branch,
                    f"Branch '{branch}' is {behind} commit(s) behind '{reference}' and has local changes to path(s) also changed by the reference: {', '.join(sorted(overlap))}.",
                    "Merge/rebase the worktree or preserve/apply its WIP explicitly before continuing.",
                )
            )
        elif behind:
            findings.append(
                Finding(
                    "WARN",
                    "silent-worktree-divergence",
                    str(path),
                    branch,
                    f"Branch '{branch}' is {behind} commit(s) behind '{reference}'. Files may look stale in this worktree even though fixes landed on the reference branch.",
                    "Review `git log --oneline {branch}..{reference}` and update the worktree before trusting file contents.",
                )
            )
        items.append(item)

    levels = [f.level for f in findings]
    status = "block" if "BLOCK" in levels else "warn" if findings else "pass"
    return {
        "schema_version": "worktree-audit-report/v1",
        "status": status,
        "project_dir": str(project),
        "reference": reference,
        "worktrees": items,
        "findings": [f.to_dict() for f in findings],
        "summary": {
            "worktree_count": len(items),
            "finding_count": len(findings),
            "block_count": sum(1 for f in findings if f.level == "BLOCK"),
            "warn_count": sum(1 for f in findings if f.level == "WARN"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit git worktree divergence against a reference branch")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--against", default=None, help="Reference branch/ref (default: origin/main, main, upstream)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 2 when BLOCK findings exist")
    args = parser.parse_args(argv)

    report = audit(Path(args.project_dir), against=args.against)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"worktree audit: {report['status']} ({report['summary']['finding_count']} findings)")
        for finding in report["findings"]:
            print(f"[{finding['level']}] {finding['code']} {finding['subject']}: {finding['detail']}")
    if args.strict and report["summary"]["block_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
