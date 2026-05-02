#!/usr/bin/env python3
# SCOPE: both
"""Read-only checklist for branches, worktrees, stashes, and dirty WIP.

This doctor is intentionally projectable: keep it in the Cognitive OS repo and
run it against any consumer repository with ``--project-dir``.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BRANCH_PATTERN = "codex/preserve-*"
DEFAULT_STASH_WARN_TTL = 600
DEFAULT_STASH_BLOCK_TTL = 3600


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    subject: str
    detail: str
    action: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "subject": self.subject,
            "detail": self.detail,
            "action": self.action,
        }


def git(project: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def is_git_repo(project: Path) -> bool:
    return git(project, ["rev-parse", "--is-inside-work-tree"]).returncode == 0


def safe_branch_name(branch: str) -> str:
    return branch.replace("/", "__") + ".json"


def manifest_path(project: Path, branch: str) -> Path:
    return project / ".cognitive-os" / "preserve-manifests" / safe_branch_name(branch)


def load_manifest(project: Path, branch: str) -> dict[str, Any] | None:
    path = manifest_path(project, branch)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_corrupt": str(exc)}
    if not isinstance(data, dict):
        return {"_corrupt": "manifest is not a JSON object"}
    return data


def category_for(path: str) -> str:
    if path.startswith(("docs/", "README", "CHANGELOG")):
        return "docs"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith("hooks/"):
        return "hooks"
    if path.startswith("scripts/"):
        return "scripts"
    if path.startswith("lib/"):
        return "lib"
    if path.startswith("packages/"):
        return "packages"
    if path.startswith((".cognitive-os/", ".claude/", ".codex/")) or path in {
        "cognitive-os.yaml",
        "Makefile",
        "pyproject.toml",
        "pytest.ini",
    }:
        return "config"
    return "other"


def changed_files_between(project: Path, base_ref: str, branch: str) -> list[str]:
    result = git(project, ["diff", "--name-only", f"{base_ref}...{branch}"])
    if result.returncode == 0:
        files = [line for line in result.stdout.splitlines() if line.strip()]
    else:
        show = git(project, ["show", "--name-only", "--format=", branch])
        files = [line for line in show.stdout.splitlines() if line.strip()]
    return sorted(set(files))


def current_head(project: Path) -> str | None:
    result = git(project, ["rev-parse", "--short", "HEAD"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_branch(project: Path) -> str | None:
    result = git(project, ["branch", "--show-current"])
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def collect_status(project: Path) -> dict[str, Any]:
    result = git(project, ["status", "--porcelain=v2", "--branch"])
    entries: list[dict[str, Any]] = []
    counts = {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0}
    ahead = 0
    behind = 0
    upstream = None
    for line in result.stdout.splitlines():
        if line.startswith("# branch.upstream "):
            upstream = line.removeprefix("# branch.upstream ").strip()
            continue
        if line.startswith("# branch.ab "):
            parts = line.split()
            for part in parts:
                if part.startswith("+"):
                    ahead = int(part[1:])
                elif part.startswith("-"):
                    behind = int(part[1:])
            continue
        if line.startswith("? "):
            path = line[2:]
            counts["untracked"] += 1
            entries.append({"kind": "untracked", "path": path})
            continue
        if line.startswith("u "):
            path = line.split()[-1]
            counts["unmerged"] += 1
            entries.append({"kind": "unmerged", "path": path})
            continue
        if line.startswith("1 ") or line.startswith("2 "):
            parts = line.split()
            xy = parts[1]
            path = parts[-1]
            if xy[0] != ".":
                counts["staged"] += 1
            if xy[1] != ".":
                counts["modified"] += 1
            entries.append({"kind": "tracked", "xy": xy, "path": path})
    return {
        "branch": current_branch(project),
        "head": current_head(project),
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "counts": counts,
        "entries": entries,
        "is_dirty": any(counts.values()),
    }


def list_branches(project: Path, pattern: str, base_ref: str) -> list[dict[str, Any]]:
    raw = git(project, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    branches = sorted(branch for branch in raw.stdout.splitlines() if fnmatch.fnmatch(branch, pattern))
    rows: list[dict[str, Any]] = []
    for branch in branches:
        tip_result = git(project, ["rev-parse", branch])
        if tip_result.returncode != 0:
            continue
        tip = tip_result.stdout.strip()
        ancestor = git(project, ["merge-base", "--is-ancestor", tip, base_ref]).returncode == 0
        manifest = load_manifest(project, branch)
        manifest_exists = manifest is not None and not (isinstance(manifest, dict) and manifest.get("_corrupt"))
        status = manifest.get("status") if isinstance(manifest, dict) and not manifest.get("_corrupt") else None
        files = changed_files_between(project, base_ref, branch)
        categories = sorted({category_for(path) for path in files})
        findings: list[str] = []
        if manifest is None:
            findings.append("missing-manifest")
        elif isinstance(manifest, dict) and manifest.get("_corrupt"):
            findings.append("corrupt-manifest")
        if len(categories) > 1:
            findings.append("mixed-scope")
        if ancestor:
            findings.append("already-integrated")
        else:
            findings.append("tip-not-ancestor-of-base")
        candidate_delete = ancestor or status in {"integrated", "obsolete", "delete-approved"}
        if candidate_delete:
            findings.append("candidate-delete")
        rows.append(
            {
                "branch": branch,
                "tip": tip[:12],
                "manifest_exists": manifest_exists,
                "manifest_path": str(manifest_path(project, branch).relative_to(project)),
                "manifest_status": status,
                "categories": categories,
                "file_count": len(files),
                "tip_is_ancestor_of_base": ancestor,
                "candidate_delete": candidate_delete,
                "findings": findings,
            }
        )
    return rows


def parse_worktree_porcelain(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree" and current:
            rows.append(current)
            current = {}
        current[key] = value
    if current:
        rows.append(current)
    return rows


def collect_worktrees(project: Path) -> list[dict[str, Any]]:
    result = git(project, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    for item in parse_worktree_porcelain(result.stdout):
        path = Path(item.get("worktree", "")).resolve()
        branch = item.get("branch", "")
        if branch.startswith("refs/heads/"):
            branch = branch.removeprefix("refs/heads/")
        status = collect_status(path) if path.exists() and is_git_repo(path) else {"is_dirty": None, "counts": {}}
        rows.append(
            {
                "path": str(path),
                "head": item.get("HEAD"),
                "branch": branch or None,
                "bare": "bare" in item,
                "detached": "detached" in item or not branch,
                "prunable": item.get("prunable"),
                "locked": item.get("locked"),
                "is_current_project": path == project.resolve(),
                "dirty": status.get("is_dirty"),
                "dirty_counts": status.get("counts", {}),
            }
        )
    return rows


def collect_stashes(project: Path, warn_ttl: int, block_ttl: int) -> list[dict[str, Any]]:
    result = git(project, ["stash", "list", "--date=unix", "--format=%gd%x1f%ct%x1f%gs"])
    if result.returncode != 0:
        return []
    now = int(time.time())
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        ref, epoch_raw, subject = parts
        try:
            epoch = int(epoch_raw)
        except ValueError:
            epoch = now
        age = max(0, now - epoch)
        files_result = git(project, ["stash", "show", "--name-only", ref])
        files = [item for item in files_result.stdout.splitlines() if item.strip()] if files_result.returncode == 0 else []
        level = "PASS"
        if age >= block_ttl:
            level = "BLOCK"
        elif age >= warn_ttl:
            level = "WARN"
        rows.append(
            {
                "ref": ref,
                "epoch": epoch,
                "age_seconds": age,
                "subject": subject,
                "file_count": len(files),
                "files": files[:50],
                "is_auto_pre_agent": "auto-pre-agent-" in subject,
                "level": level,
            }
        )
    return rows


def build_findings(payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    status = payload["status"]
    counts = status["counts"]
    if counts["unmerged"]:
        findings.append(
            Finding(
                "BLOCK",
                "worktree-conflicts",
                "current worktree",
                f"{counts['unmerged']} unmerged path(s)",
                "Resolve conflicts before integrating or deleting preserved work.",
            )
        )
    if counts["staged"] or counts["modified"] or counts["untracked"]:
        findings.append(
            Finding(
                "WARN",
                "worktree-dirty",
                "current worktree",
                f"staged={counts['staged']} modified={counts['modified']} untracked={counts['untracked']}",
                "Commit, intentionally preserve, or discard current WIP before cleanup.",
            )
        )
    if status.get("ahead"):
        findings.append(
            Finding(
                "WARN",
                "unpushed-commits",
                status.get("branch") or "current branch",
                f"ahead of upstream by {status['ahead']} commit(s)",
                "Push or document why local commits should remain local.",
            )
        )
    for branch in payload["preserve_branches"]:
        if "missing-manifest" in branch["findings"] or "corrupt-manifest" in branch["findings"]:
            findings.append(
                Finding(
                    "WARN",
                    "preserve-manifest-missing",
                    branch["branch"],
                    f"tip={branch['tip']} files={branch['file_count']} categories={','.join(branch['categories']) or '-'}",
                    "Create or update a preserve manifest before deleting the branch.",
                )
            )
        if "mixed-scope" in branch["findings"]:
            findings.append(
                Finding(
                    "WARN",
                    "preserve-mixed-scope",
                    branch["branch"],
                    f"categories={','.join(branch['categories'])}",
                    "Review/cherry-pick selectively; do not merge the branch wholesale.",
                )
            )
        if "tip-not-ancestor-of-base" in branch["findings"]:
            findings.append(
                Finding(
                    "WARN",
                    "preserve-not-integrated",
                    branch["branch"],
                    f"tip={branch['tip']} is not an ancestor of the base ref",
                    "Prove duplicated, cherry-pick needed files, or mark obsolete with evidence.",
                )
            )
    for worktree in payload["worktrees"]:
        if worktree.get("is_current_project"):
            continue
        if worktree.get("dirty"):
            findings.append(
                Finding(
                    "WARN",
                    "linked-worktree-dirty",
                    worktree["path"],
                    f"branch={worktree.get('branch') or 'detached'} counts={worktree.get('dirty_counts')}",
                    "Inspect linked worktree before pruning, deleting branches, or claiming cleanup complete.",
                )
            )
        if worktree.get("prunable"):
            findings.append(
                Finding(
                    "WARN",
                    "linked-worktree-prunable",
                    worktree["path"],
                    str(worktree.get("prunable")),
                    "Run git worktree prune only after checking no WIP remains there.",
                )
            )
    for stash in payload["stashes"]:
        if stash["level"] in {"WARN", "BLOCK"}:
            findings.append(
                Finding(
                    stash["level"],
                    "stash-aged",
                    stash["ref"],
                    f"age={stash['age_seconds']}s files={stash['file_count']} subject={stash['subject']}",
                    f"Inspect with `git stash show --name-status {stash['ref']}`; pop/apply/drop only after review.",
                )
            )
        elif stash["is_auto_pre_agent"]:
            findings.append(
                Finding(
                    "WARN",
                    "stash-auto-pre-agent-present",
                    stash["ref"],
                    f"age={stash['age_seconds']}s files={stash['file_count']}",
                    "Auto-preserved stash exists; include it in the closure checklist.",
                )
            )
    return findings


def collect_inventory(args: argparse.Namespace) -> dict[str, Any]:
    project = Path(args.project_dir).expanduser().resolve()
    if not is_git_repo(project):
        raise SystemExit(f"Not a git repository: {project}")
    payload = {
        "project": str(project),
        "base_ref": args.base_ref,
        "branch_pattern": args.branch_pattern,
        "status": collect_status(project),
        "preserve_branches": list_branches(project, args.branch_pattern, args.base_ref),
        "worktrees": collect_worktrees(project),
        "stashes": collect_stashes(project, args.stash_warn_ttl, args.stash_block_ttl),
    }
    findings = build_findings(payload)
    payload["findings"] = [finding.to_dict() for finding in findings]
    payload["summary"] = {
        "blockers": sum(1 for finding in findings if finding.level == "BLOCK"),
        "warnings": sum(1 for finding in findings if finding.level == "WARN"),
        "preserve_branch_count": len(payload["preserve_branches"]),
        "worktree_count": len(payload["worktrees"]),
        "stash_count": len(payload["stashes"]),
    }
    return payload


def print_text(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    status = payload["status"]
    print(f"Project: {payload['project']}")
    print(f"Base ref: {payload['base_ref']}")
    print(f"Branch: {status.get('branch') or 'detached'} head={status.get('head') or '-'} upstream={status.get('upstream') or '-'} ahead={status.get('ahead')} behind={status.get('behind')}")
    print("Checklist:")
    checks = [
        ("current worktree has no conflicts", status["counts"]["unmerged"] == 0),
        ("current worktree has no uncommitted/untracked WIP", not status["is_dirty"]),
        ("no unpushed commits", status.get("ahead", 0) == 0),
        ("preserve branches have manifests", all(b["manifest_exists"] for b in payload["preserve_branches"])),
        ("preserve branches are integrated/closed", all(b["candidate_delete"] for b in payload["preserve_branches"])),
        ("linked worktrees are clean", all((w.get("is_current_project") or not w.get("dirty")) for w in payload["worktrees"])),
        ("no stashes require review", not payload["stashes"]),
    ]
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'WARN'} {label}")
    if payload["findings"]:
        print("Findings:")
        for finding in payload["findings"]:
            print(f"  {finding['level']} {finding['code']} {finding['subject']} :: {finding['detail']}")
            print(f"    action: {finding['action']}")
    else:
        print("Findings: none")
    print(
        "Result: "
        + ("BLOCK" if summary["blockers"] else "WARN" if summary["warnings"] else "PASS")
        + f" ({summary['blockers']} blocker(s), {summary['warnings']} warning(s))"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--branch-pattern", default=DEFAULT_BRANCH_PATTERN)
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--stash-warn-ttl", type=int, default=int(os.environ.get("COS_STASH_LEAK_TTL", DEFAULT_STASH_WARN_TTL)))
    parser.add_argument("--stash-block-ttl", type=int, default=int(os.environ.get("COS_STASH_LEAK_BLOCK_TTL", DEFAULT_STASH_BLOCK_TTL)))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when warnings or blockers exist.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = collect_inventory(args)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print_text(payload)
    summary = payload["summary"]
    if summary["blockers"]:
        return 2
    if args.strict and summary["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
