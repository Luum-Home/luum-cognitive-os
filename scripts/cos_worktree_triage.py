#!/usr/bin/env python3
# SCOPE: both
"""Read-only triage of a linked worktree against a target branch.

Use this before manually porting/deleting a worktree. It answers:
- which commits are already patch-equivalent to the target;
- which commits still need selective porting;
- whether dirty files or stashes block cleanup;
- what validation/cleanup commands are appropriate.

The script never cherry-picks, merges, commits, pushes, drops stashes, or removes
worktrees. It emits a checklist and suggested commands for an operator/agent to
execute deliberately.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def run_git(repo: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git_required(repo: Path, args: list[str]) -> str:
    result = run_git(repo, args)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def resolve_worktree(path: str) -> Path:
    worktree = Path(path).expanduser().resolve()
    if not worktree.exists():
        raise SystemExit(f"Worktree path does not exist: {worktree}")
    if run_git(worktree, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
        raise SystemExit(f"Not a git worktree: {worktree}")
    return worktree


def status_counts(repo: Path) -> dict[str, Any]:
    result = run_git(repo, ["status", "--porcelain=v2", "--branch"])
    counts = {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0}
    entries: list[dict[str, str]] = []
    branch: str | None = None
    upstream: str | None = None
    ahead = 0
    behind = 0
    for line in result.stdout.splitlines():
        if line.startswith("# branch.head "):
            value = line.removeprefix("# branch.head ").strip()
            branch = None if value == "(detached)" else value
        elif line.startswith("# branch.upstream "):
            upstream = line.removeprefix("# branch.upstream ").strip()
        elif line.startswith("# branch.ab "):
            for part in line.split():
                if part.startswith("+"):
                    ahead = int(part[1:])
                elif part.startswith("-"):
                    behind = int(part[1:])
        elif line.startswith("? "):
            counts["untracked"] += 1
            entries.append({"kind": "untracked", "path": line[2:]})
        elif line.startswith("u "):
            counts["unmerged"] += 1
            entries.append({"kind": "unmerged", "path": line.split()[-1]})
        elif line.startswith(("1 ", "2 ")):
            parts = line.split()
            xy = parts[1]
            path = parts[-1]
            if xy[0] != ".":
                counts["staged"] += 1
            if xy[1] != ".":
                counts["modified"] += 1
            entries.append({"kind": "tracked", "xy": xy, "path": path})
    return {
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "counts": counts,
        "entries": entries,
        "is_dirty": any(counts.values()),
    }


def parse_cherry(repo: Path, target: str, head: str) -> list[dict[str, Any]]:
    """Classify target..head commits by patch-equivalence to target.

    `git cherry` omits some already-equivalent commits in common workflows, so
    compare all target-only-right commits with `--cherry-pick` unique commits.
    """
    all_result = run_git(repo, ["log", "--reverse", "--format=%H%x1f%s", f"{target}..{head}"])
    if all_result.returncode != 0:
        raise SystemExit(f"git log failed: {all_result.stderr.strip()}")
    unique_result = run_git(repo, ["log", "--reverse", "--right-only", "--cherry-pick", "--format=%H", f"{target}...{head}"])
    if unique_result.returncode != 0:
        raise SystemExit(f"git log --cherry-pick failed: {unique_result.stderr.strip()}")
    unique_shas = set(unique_result.stdout.splitlines())
    rows: list[dict[str, Any]] = []
    for line in all_result.stdout.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition("\x1f")
        needs_port = sha in unique_shas
        rows.append(
            {
                "sha": sha,
                "short": sha[:12],
                "subject": subject,
                "patch_equivalent_on_target": not needs_port,
                "needs_port": needs_port,
            }
        )
    return rows


def collect_stashes(repo: Path) -> list[dict[str, Any]]:
    result = run_git(repo, ["stash", "list", "--date=unix", "--format=%gd%x1f%ct%x1f%gs"])
    if result.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        ref, epoch, subject = parts
        files = run_git(repo, ["stash", "show", "--name-only", ref])
        file_list = [item for item in files.stdout.splitlines() if item.strip()] if files.returncode == 0 else []
        rows.append({"ref": ref, "epoch": int(epoch), "subject": subject, "file_count": len(file_list), "files": file_list[:50]})
    return rows


def collect_diff_files(repo: Path, target: str, head: str) -> list[dict[str, str]]:
    result = run_git(repo, ["diff", "--name-status", f"{target}...{head}"])
    if result.returncode != 0:
        return []
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        rows.append({"status": parts[0], "path": parts[-1]})
    return rows


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    worktree = resolve_worktree(args.worktree)
    target_repo = Path(args.project_dir or os.getcwd()).expanduser().resolve()
    if run_git(target_repo, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
        raise SystemExit(f"Target project is not a git repository: {target_repo}")

    target = args.target
    git_required(target_repo, ["rev-parse", "--verify", target])
    head = git_required(worktree, ["rev-parse", "HEAD"])
    target_sha = git_required(target_repo, ["rev-parse", target])
    merge_base = git_required(target_repo, ["merge-base", target, head])

    status = status_counts(worktree)
    stashes = collect_stashes(worktree)
    commits = parse_cherry(target_repo, target, head)
    needs_port = [commit for commit in commits if commit["needs_port"]]
    already_applied = [commit for commit in commits if commit["patch_equivalent_on_target"]]
    diff_files = collect_diff_files(target_repo, target, head)

    blockers: list[dict[str, str]] = []
    if status["counts"]["unmerged"]:
        blockers.append({"code": "worktree-conflicts", "detail": f"{status['counts']['unmerged']} unmerged path(s)"})
    if status["is_dirty"]:
        blockers.append({"code": "worktree-dirty", "detail": str(status["counts"])})
    if stashes:
        blockers.append({"code": "worktree-stashes-present", "detail": f"{len(stashes)} stash(es) visible from worktree"})

    safe_to_remove = not blockers and not needs_port
    checklist = [
        {"item": "worktree has no conflicts", "status": "PASS" if not status["counts"]["unmerged"] else "BLOCK"},
        {"item": "worktree has no uncommitted WIP", "status": "PASS" if not status["is_dirty"] else "BLOCK"},
        {"item": "worktree has no stashes", "status": "PASS" if not stashes else "BLOCK"},
        {"item": "all commits are patch-equivalent to target", "status": "PASS" if not needs_port else "TODO"},
        {"item": "safe to remove worktree", "status": "PASS" if safe_to_remove else "BLOCK"},
    ]

    suggested_commands: list[str] = []
    if needs_port:
        suggested_commands.append(f"git switch {target}")
        for commit in needs_port:
            suggested_commands.append(f"git cherry-pick {commit['sha']}")
    if stashes:
        for stash in stashes:
            suggested_commands.append(f"git -C {worktree} stash show --name-status {stash['ref']}")
    suggested_commands.append("python3 -m pytest tests/behavior/test_cos_work_inventory.py -q  # replace with slice-specific validation")
    if safe_to_remove:
        suggested_commands.append(f"git worktree remove {worktree}")
    else:
        suggested_commands.append(f"# not safe to remove yet: {worktree}")

    return {
        "target_repo": str(target_repo),
        "worktree": str(worktree),
        "target": target,
        "target_sha": target_sha[:12],
        "worktree_head": head[:12],
        "merge_base": merge_base[:12],
        "worktree_status": status,
        "stashes": stashes,
        "commits": commits,
        "already_applied_commits": already_applied,
        "commits_to_port": needs_port,
        "diff_files": diff_files,
        "blockers": blockers,
        "checklist": checklist,
        "safe_to_remove": safe_to_remove,
        "suggested_commands": suggested_commands,
    }


def print_text(payload: dict[str, Any]) -> None:
    print(f"Target repo: {payload['target_repo']}")
    print(f"Target: {payload['target']} @ {payload['target_sha']}")
    print(f"Worktree: {payload['worktree']} @ {payload['worktree_head']}")
    print(f"Merge-base: {payload['merge_base']}")
    print("Checklist:")
    for item in payload["checklist"]:
        print(f"  {item['status']} {item['item']}")
    print(f"Already applied commits: {len(payload['already_applied_commits'])}")
    for commit in payload["already_applied_commits"]:
        print(f"  SKIP {commit['short']} {commit['subject']}")
    print(f"Commits to port: {len(payload['commits_to_port'])}")
    for commit in payload["commits_to_port"]:
        print(f"  TODO {commit['short']} {commit['subject']}")
    if payload["blockers"]:
        print("Blockers:")
        for blocker in payload["blockers"]:
            print(f"  BLOCK {blocker['code']} :: {blocker['detail']}")
    print("Suggested commands:")
    for command in payload["suggested_commands"]:
        print(f"  {command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True, help="Path to the worktree being triaged.")
    parser.add_argument("--project-dir", help="Target repository/worktree path. Defaults to current directory.")
    parser.add_argument("--target", default="main", help="Target branch/ref to compare against. Defaults to main.")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_payload(args)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_text(payload)
    return 2 if payload["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
