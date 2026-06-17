#!/usr/bin/env python3
# SCOPE: both
"""Governed branch/worktree closure helper for Cognitive OS repositories.

The helper makes the ADR-116 path executable and discoverable across CLIs/IDEs:

inventory -> classify -> optional protected landing -> optional merged cleanup.

It is intentionally conservative. It never lands from main, never deletes dirty
worktrees, and never deletes remote branches unless --apply is present.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BRANCH_PATTERNS = ("codex/", "claude/")
SCHEMA = "cos.branch-worktree-closure.v1"


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def run_git(project: Path, args: list[str], *, check: bool = False, timeout: int = 120) -> CmdResult:
    proc = subprocess.run(
        ["git", "-C", str(project), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed rc={proc.returncode}: {proc.stderr.strip()}")
    return CmdResult(proc.returncode, proc.stdout, proc.stderr)


def run_shell(project: Path, command: str, *, timeout: int = 900) -> CmdResult:
    proc = subprocess.run(
        command,
        cwd=project,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
        executable=os.environ.get("SHELL") or None,
    )
    return CmdResult(proc.returncode, proc.stdout, proc.stderr)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_branch_name(name: str) -> bool:
    return name.startswith(BRANCH_PATTERNS)


def current_branch(project: Path) -> str:
    result = run_git(project, ["branch", "--show-current"])
    return result.stdout.strip()


def local_agent_branches(project: Path) -> list[str]:
    result = run_git(project, ["branch", "--format=%(refname:short)"])
    return sorted(line.strip() for line in result.stdout.splitlines() if is_branch_name(line.strip()))


def remote_agent_branches(project: Path, remote: str) -> list[str]:
    result = run_git(project, ["branch", "-r", "--format=%(refname:short)"])
    prefix = f"{remote}/"
    out: list[str] = []
    for line in result.stdout.splitlines():
        ref = line.strip()
        if not ref.startswith(prefix):
            continue
        short = ref.removeprefix(prefix)
        if is_branch_name(short):
            out.append(short)
    return sorted(set(out))


def parse_worktrees(project: Path) -> dict[str, str]:
    result = run_git(project, ["worktree", "list", "--porcelain"])
    worktrees: dict[str, str] = {}
    current_path = ""
    for raw in result.stdout.splitlines():
        if raw.startswith("worktree "):
            current_path = raw.removeprefix("worktree ")
        elif raw.startswith("branch refs/heads/") and current_path:
            branch = raw.removeprefix("branch refs/heads/")
            worktrees[branch] = current_path
    return worktrees


def parse_all_worktrees(project: Path) -> list[dict[str, Any]]:
    result = run_git(project, ["worktree", "list", "--porcelain"])
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw in result.stdout.splitlines():
        if raw.startswith("worktree "):
            if current:
                rows.append(current)
            current = {"path": raw.removeprefix("worktree ")}
        elif raw.startswith("HEAD "):
            current["head"] = raw.removeprefix("HEAD ")
        elif raw.startswith("branch refs/heads/"):
            current["branch"] = raw.removeprefix("branch refs/heads/")
        elif raw == "bare":
            current["bare"] = True
        elif raw == "detached":
            current["detached"] = True
    if current:
        rows.append(current)
    for row in rows:
        path = Path(str(row.get("path", "")))
        row["dirty_status"] = dirty_status(path) if path.exists() else {"dirty": None, "entries": [], "reason": "missing-worktree"}
    return rows


def dirty_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"dirty": None, "entries": [], "reason": "missing-worktree"}
    result = run_git(path, ["status", "--porcelain=v1"])
    entries = [line for line in result.stdout.splitlines() if line.strip()]
    return {"dirty": bool(entries), "entries": entries[:50], "entry_count": len(entries)}


def count_rev(project: Path, revspec: str) -> int:
    result = run_git(project, ["rev-list", "--count", revspec])
    if result.returncode != 0:
        return -1
    try:
        return int(result.stdout.strip() or "0")
    except ValueError:
        return -1


def is_ancestor(project: Path, ancestor: str, descendant: str) -> bool:
    return run_git(project, ["merge-base", "--is-ancestor", ancestor, descendant]).returncode == 0


def stash_count(project: Path) -> int:
    result = run_git(project, ["stash", "list"])
    return len([line for line in result.stdout.splitlines() if line.strip()])


def classify_branch(project: Path, branch: str, main_ref: str, worktrees: dict[str, str], stash_total: int, current: str) -> dict[str, Any]:
    wt = worktrees.get(branch)
    status = dirty_status(Path(wt)) if wt else {"dirty": False, "entries": [], "entry_count": 0}
    merged = is_ancestor(project, branch, main_ref)
    ahead = count_rev(project, f"{main_ref}..{branch}")
    behind = count_rev(project, f"{branch}..{main_ref}")
    if status.get("dirty"):
        classification = "blocked-dirty-worktree"
        action = "preserve: clean or commit WIP before landing/deleting"
    elif stash_total > 0:
        classification = "blocked-stash-present"
        action = "preserve: inspect stashes before destructive cleanup"
    elif merged:
        classification = "merged-cleanup"
        action = "delete local branch and optionally delete matching remote branch in batch"
    elif ahead > 0:
        classification = "useful-land-required"
        action = "land from this branch via scripts/cos land or scripts/merge-to-main.sh, then cleanup"
    else:
        classification = "needs-review"
        action = "inspect diff against main before cleanup"
    return {
        "branch": branch,
        "current": branch == current,
        "worktree": wt,
        "dirty_status": status,
        "merged_to_main": merged,
        "ahead_of_main": ahead,
        "behind_main": behind,
        "classification": classification,
        "action": action,
    }


def inventory(project: Path, remote: str, main: str, integration_mode: str = "rebase-ff") -> dict[str, Any]:
    main_ref = f"{remote}/{main}"
    run_git(project, ["fetch", remote, main], timeout=120)
    current = current_branch(project)
    worktrees = parse_worktrees(project)
    all_worktrees = parse_all_worktrees(project)
    stashes = stash_count(project)
    root_status = dirty_status(project)
    locals_ = local_agent_branches(project)
    remotes = remote_agent_branches(project, remote)
    branches = [classify_branch(project, b, main_ref, worktrees, stashes, current) for b in locals_]
    remote_merged = [b for b in remotes if is_ancestor(project, f"{remote}/{b}", main_ref)]
    local_merged = [b["branch"] for b in branches if b["classification"] == "merged-cleanup" and not b["current"]]
    blockers = [b for b in branches if b["classification"].startswith("blocked-")]
    useful = [b for b in branches if b["classification"] == "useful-land-required"]
    return {
        "schema_version": SCHEMA,
        "generated_at": utc_now(),
        "project_dir": str(project),
        "remote": remote,
        "main": main,
        "main_ref": main_ref,
        "current_branch": current,
        "stash_count": stashes,
        "root_dirty_status": root_status,
        "worktrees": all_worktrees,
        "branches": branches,
        "remote_merged_branches": remote_merged,
        "local_merged_branches": local_merged,
        "blocker_count": len(blockers),
        "useful_unmerged_count": len(useful),
        "integration_mode": integration_mode,
        "landing_command": landing_command(integration_mode),
        "backup_tag_command": f"git tag backup/{main}-before-branch-worktree-closure-{utc_now().replace(':', '').replace('-', '').replace('Z', 'Z')} {main_ref}",
        "batch_remote_delete_command": batch_delete_command(remote, remote_merged),
    }


def landing_command(integration_mode: str) -> str:
    suffix = "" if integration_mode == "rebase-ff" else " --integration-mode merge-no-rebase"
    return f"scripts/cos land{suffix} --validate '<targeted validation command>'"


def batch_delete_command(remote: str, branches: list[str]) -> str | None:
    if not branches:
        return None
    specs = " ".join(f":refs/heads/{b}" for b in branches)
    return f"git push {remote} {specs}"


def write_receipt(project: Path, payload: dict[str, Any]) -> Path:
    out_dir = project / ".cognitive-os" / "branch-worktree-closure"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "latest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def land_current_branch(project: Path, args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    current = report["current_branch"]
    if current in {args.main, "master"}:
        return {"attempted": False, "status": "blocked", "reason": "current-branch-is-main"}
    branch_rows = {row["branch"]: row for row in report["branches"]}
    row = branch_rows.get(current)
    if not row:
        return {"attempted": False, "status": "blocked", "reason": "current-branch-not-agent-branch", "branch": current}
    if row["classification"].startswith("blocked-"):
        return {"attempted": False, "status": "blocked", "reason": row["classification"], "branch": current}
    command = f"scripts/cos land --repo {sh_quote(str(project))} --remote {sh_quote(args.remote)} --main {sh_quote(args.main)} --validate {sh_quote(args.validate)} --executed-lane {sh_quote(args.executed_lane)} --integration-mode {sh_quote(args.integration_mode)}"
    if not args.apply:
        return {"attempted": False, "status": "dry-run", "branch": current, "command": command}
    result = run_shell(project, command, timeout=args.timeout)
    return {
        "attempted": True,
        "status": "landed" if result.returncode == 0 else "failed",
        "branch": current,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def cleanup_merged(project: Path, args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    local_deleted: list[dict[str, Any]] = []
    remote_deleted: dict[str, Any] = {"attempted": False, "branches": report.get("remote_merged_branches", [])}
    current = current_branch(project)
    if report.get("blocker_count", 0) and not args.allow_blockers:
        return {"status": "blocked", "reason": "blockers-present", "local_deleted": [], "remote_deleted": remote_deleted}
    for branch in report.get("local_merged_branches", []):
        if branch == current:
            continue
        if not args.apply:
            local_deleted.append({"branch": branch, "status": "dry-run"})
            continue
        result = run_git(project, ["branch", "-d", branch])
        local_deleted.append({"branch": branch, "status": "deleted" if result.returncode == 0 else "failed", "returncode": result.returncode, "stderr_tail": result.stderr[-1000:]})
    remote_branches = list(report.get("remote_merged_branches", []))
    if remote_branches:
        command = ["push", args.remote, *[f":refs/heads/{b}" for b in remote_branches]]
        remote_deleted = {"attempted": bool(args.apply), "branches": remote_branches, "command": "git " + " ".join(command)}
        if args.apply:
            result = run_git(project, command, timeout=args.timeout)
            remote_deleted.update({"status": "deleted" if result.returncode == 0 else "failed", "returncode": result.returncode, "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-4000:]})
        else:
            remote_deleted["status"] = "dry-run"
    return {"status": "ok", "local_deleted": local_deleted, "remote_deleted": remote_deleted}


def create_backup_tag(project: Path, args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    tag = args.backup_tag or f"backup/{args.main}-before-branch-worktree-closure-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    command = ["tag", tag, report["main_ref"]]
    if not args.apply:
        return {"attempted": False, "status": "dry-run", "tag": tag, "command": "git " + " ".join(command)}
    exists = run_git(project, ["rev-parse", "--verify", tag])
    if exists.returncode == 0:
        return {"attempted": False, "status": "exists", "tag": tag}
    result = run_git(project, command)
    return {"attempted": True, "status": "created" if result.returncode == 0 else "failed", "tag": tag, "returncode": result.returncode, "stderr_tail": result.stderr[-1000:]}


def command_run(args: argparse.Namespace) -> int:
    project = Path(args.project_dir).resolve()
    report = inventory(project, args.remote, args.main, args.integration_mode)
    actions: dict[str, Any] = {}
    if args.create_backup_tag:
        actions["backup_tag"] = create_backup_tag(project, args, report)
    if args.land_current:
        actions["land_current"] = land_current_branch(project, args, report)
    if args.cleanup_merged:
        refreshed = inventory(project, args.remote, args.main, args.integration_mode)
        actions["cleanup_merged"] = cleanup_merged(project, args, refreshed)
        report = inventory(project, args.remote, args.main, args.integration_mode) if args.apply else refreshed
    payload = {**report, "mode": "apply" if args.apply else "dry-run", "actions": actions}
    payload["receipt_path"] = str(write_receipt(project, payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"branch-worktree-closure: current={payload['current_branch']} blockers={payload['blocker_count']} useful={payload['useful_unmerged_count']}")
        print(f"integration: {payload['integration_mode']}")
        print(f"landing: {payload['landing_command']}")
        print(f"backup: {payload['backup_tag_command']}")
        if payload.get("batch_remote_delete_command"):
            print(f"remote cleanup: {payload['batch_remote_delete_command']}")
        print(f"receipt: {payload['receipt_path']}")
    failed_actions = [a for a in actions.values() if isinstance(a, dict) and a.get("status") == "failed"]
    if failed_actions:
        return 2
    if payload["blocker_count"] and args.strict:
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inventory, land, and cleanup agent branches/worktrees through the protected main path")
    parser.add_argument("--project-dir", default=os.getcwd())
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--main", default="main")
    parser.add_argument("--validate", default="scripts/cos-primitive-closure-check --json --strict")
    parser.add_argument("--integration-mode", default="rebase-ff", choices=["rebase-ff", "merge-no-rebase"], help="how scripts/cos land should integrate useful branches")
    parser.add_argument("--executed-lane", default="branch-worktree-closure")
    parser.add_argument("--create-backup-tag", action="store_true", help="create backup/<main>-before-branch-worktree-closure-* before apply operations")
    parser.add_argument("--backup-tag", help="explicit backup tag name for --create-backup-tag")
    parser.add_argument("--land-current", action="store_true", help="land the current non-main agent branch through scripts/cos land")
    parser.add_argument("--cleanup-merged", action="store_true", help="delete merged local branches and matching remote branches in one batch push")
    parser.add_argument("--apply", action="store_true", help="perform landing/deletion; omitted means dry-run report only")
    parser.add_argument("--allow-blockers", action="store_true", help="allow cleanup even if dirty/stash blockers exist")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return command_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
