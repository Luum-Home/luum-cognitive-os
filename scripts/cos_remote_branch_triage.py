#!/usr/bin/env python3
# SCOPE: both
"""Audit remote branches against a target ref and identify patch-equivalent cleanup candidates.

Default mode is read-only. A branch is safe to delete only when every commit on
`target..remote/branch` is patch-equivalent to the target according to
`git log --cherry-pick`.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
import sys
from lib.script_helpers import run_git

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any


def git_required(repo: Path, args: list[str]) -> str:
    result = run_git(repo, args)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def remote_branches(repo: Path, remote: str) -> list[str]:
    refs = git_required(repo, ["for-each-ref", "--format=%(refname:short)", f"refs/remotes/{remote}"])
    rows: list[str] = []
    for ref in refs.splitlines():
        ref = ref.strip()
        if not ref or ref == f"{remote}/HEAD":
            continue
        rows.append(ref)
    return rows


def branch_name(remote_ref: str, remote: str) -> str:
    prefix = f"{remote}/"
    return remote_ref.removeprefix(prefix)


def parse_commits(repo: Path, target: str, remote_ref: str) -> list[dict[str, Any]]:
    all_result = run_git(repo, ["log", "--reverse", "--format=%H%x1f%h%x1f%s", f"{target}..{remote_ref}"])
    if all_result.returncode != 0:
        raise SystemExit(f"git log failed for {remote_ref}: {all_result.stderr.strip()}")
    unique_result = run_git(repo, ["log", "--reverse", "--right-only", "--cherry-pick", "--format=%H", f"{target}...{remote_ref}"])
    if unique_result.returncode != 0:
        raise SystemExit(f"git log --cherry-pick failed for {remote_ref}: {unique_result.stderr.strip()}")
    unique_shas = set(unique_result.stdout.splitlines())
    commits: list[dict[str, Any]] = []
    for line in all_result.stdout.splitlines():
        if not line.strip():
            continue
        sha, short, subject = line.split("\x1f", 2)
        needs_port = sha in unique_shas
        commits.append({"sha": sha, "short": short, "subject": subject, "patch_equivalent_on_target": not needs_port, "needs_port": needs_port})
    return commits


def diff_files(repo: Path, target: str, remote_ref: str) -> list[dict[str, str]]:
    result = run_git(repo, ["diff", "--name-status", f"{target}...{remote_ref}"])
    if result.returncode != 0:
        return []
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if parts:
            rows.append({"status": parts[0], "path": parts[-1]})
    return rows


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.project_dir or os.getcwd()).expanduser().resolve()
    if run_git(repo, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
        raise SystemExit(f"Not a git repository: {repo}")
    remote = args.remote
    target = args.target
    git_required(repo, ["rev-parse", "--verify", target])
    if args.fetch:
        fetch = run_git(repo, ["fetch", "--prune", remote])
        if fetch.returncode != 0:
            raise SystemExit(f"git fetch --prune {remote} failed: {fetch.stderr.strip()}")

    refs = [f"{remote}/{item}" for item in args.branch] if args.branch else remote_branches(repo, remote)
    protected = {f"{remote}/{name}" for name in args.protected_branch}
    protected.add(f"{remote}/{branch_name(target, remote) if target.startswith(f'{remote}/') else target}")

    findings: list[dict[str, Any]] = []
    for ref in refs:
        if run_git(repo, ["rev-parse", "--verify", ref]).returncode != 0:
            findings.append({"remote_ref": ref, "status": "missing", "safe_to_delete": False, "reason": "remote ref not found"})
            continue
        commits = parse_commits(repo, target, ref)
        needs_port = [commit for commit in commits if commit["needs_port"]]
        patch_equivalent = [commit for commit in commits if commit["patch_equivalent_on_target"]]
        is_protected = ref in protected or branch_name(ref, remote) in args.protected_branch
        safe_to_delete = bool(commits) and not needs_port and not is_protected
        if is_protected:
            status = "protected"
            reason = "branch is protected by CLI policy"
        elif not commits:
            status = "already_merged_or_no_unique_history"
            reason = "target..branch has no commits"
        elif needs_port:
            status = "needs_port"
            reason = f"{len(needs_port)} commit(s) are not patch-equivalent to target"
        else:
            status = "patch_equivalent"
            reason = "all branch-only commits are patch-equivalent to target"
        findings.append(
            {
                "remote_ref": ref,
                "branch": branch_name(ref, remote),
                "status": status,
                "reason": reason,
                "safe_to_delete": safe_to_delete,
                "commit_count": len(commits),
                "patch_equivalent_count": len(patch_equivalent),
                "needs_port_count": len(needs_port),
                "commits": commits,
                "diff_files": diff_files(repo, target, ref),
                "delete_command": f"git push {remote} :{branch_name(ref, remote)}" if safe_to_delete else None,
            }
        )
    delete_candidates = [finding for finding in findings if finding.get("safe_to_delete")]
    return {
        "schema_version": "remote-branch-triage/v1",
        "project_dir": str(repo),
        "remote": remote,
        "target": target,
        "mode": "delete" if args.delete else "dry-run",
        "summary": {
            "remote_branches_checked": len(findings),
            "safe_to_delete": len(delete_candidates),
            "needs_port": sum(1 for finding in findings if finding.get("status") == "needs_port"),
            "protected": sum(1 for finding in findings if finding.get("status") == "protected"),
            "missing": sum(1 for finding in findings if finding.get("status") == "missing"),
        },
        "findings": findings,
    }


def delete_candidates(repo: Path, payload: dict[str, Any], *, yes: bool) -> list[dict[str, Any]]:
    if not yes:
        raise SystemExit("Refusing deletion without --yes. Re-run with --delete --yes after reviewing dry-run output.")
    results: list[dict[str, Any]] = []
    remote = payload["remote"]
    for finding in payload["findings"]:
        if not finding.get("safe_to_delete"):
            continue
        branch = finding["branch"]
        result = run_git(repo, ["push", remote, f":{branch}"])
        results.append({"branch": branch, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()})
    return results


def print_text(payload: dict[str, Any]) -> None:
    print(f"Remote branch triage: {payload['remote']} vs {payload['target']} ({payload['mode']})")
    print(f"Summary: {payload['summary']}")
    for finding in payload["findings"]:
        print(f"- {finding['remote_ref']}: {finding['status']} safe_to_delete={finding.get('safe_to_delete', False)} :: {finding['reason']}")
        for commit in finding.get("commits", []):
            mark = "SKIP" if commit["patch_equivalent_on_target"] else "TODO"
            print(f"    {mark} {commit['short']} {commit['subject']}")
        if finding.get("delete_command"):
            print(f"    delete: {finding['delete_command']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", help="Repository path. Defaults to current directory.")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--target", default="origin/main")
    parser.add_argument("--branch", action="append", default=[], help="Remote branch name without remote prefix. Repeatable. Defaults to all remote branches.")
    parser.add_argument("--protected-branch", action="append", default=["main", "master"], help="Remote branch name that must never be deleted. Repeatable.")
    parser.add_argument("--fetch", action="store_true", help="Run git fetch --prune before auditing.")
    parser.add_argument("--delete", action="store_true", help="Delete safe-to-delete remote branches. Requires --yes.")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion when --delete is set.")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_payload(args)
    if args.delete:
        payload["delete_results"] = delete_candidates(Path(payload["project_dir"]), payload, yes=args.yes)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_text(payload)
        if args.delete:
            print("Deletion results:")
            for result in payload.get("delete_results", []):
                print(f"- {result['branch']}: rc={result['returncode']} {result['stderr'] or result['stdout']}")
    return 0 if payload["summary"]["needs_port"] == 0 and payload["summary"]["missing"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
