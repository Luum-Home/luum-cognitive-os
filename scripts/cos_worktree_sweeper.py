#!/usr/bin/env python3
# SCOPE: both
"""Conservative sweeper for stale temporary git worktrees."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ALLOWED_UNTRACKED = (".venv",)


@dataclass(frozen=True)
class Worktree:
    path: Path
    head: str | None
    branch: str | None
    detached: bool


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)  # timeout per ADR-278 (default - review)


def parse_worktrees(output: str) -> list[Worktree]:
    worktrees: list[Worktree] = []
    current: dict[str, str] = {}
    for line in output.splitlines() + [""]:
        if not line.strip():
            if current:
                branch = current.get("branch")
                worktrees.append(Worktree(Path(current["worktree"]).resolve(), current.get("HEAD"), branch, branch is None))
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return worktrees


def list_worktrees(repo: Path) -> list[Worktree]:
    proc = run_command(["git", "worktree", "list", "--porcelain"], repo)
    if proc.returncode != 0:
        raise SystemExit(f"git worktree list failed: {proc.stderr.strip()}")
    return parse_worktrees(proc.stdout)


def default_safe_prefixes() -> list[Path]:
    prefixes = [Path("/tmp").resolve(), Path("/private/tmp").resolve()]
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        prefixes.append(Path(tmpdir).resolve())
    unique: list[Path] = []
    for prefix in prefixes:
        if prefix not in unique:
            unique.append(prefix)
    return unique


def path_under(path: Path, prefix: Path) -> bool:
    try:
        path.resolve().relative_to(prefix.resolve())
        return True
    except ValueError:
        return False


def normalize_untracked(path: str) -> str:
    return path.strip().rstrip("/")


def untracked_allowed(path: str, allowed: tuple[str, ...]) -> bool:
    normalized = normalize_untracked(path)
    return any(normalized == item.rstrip("/") or normalized.startswith(item.rstrip("/") + "/") for item in allowed)


def git_status(path: Path, allowed_untracked: tuple[str, ...]) -> tuple[list[str], list[str], str | None]:
    proc = run_command(["git", "status", "--porcelain=v1", "--untracked-files=all"], path)
    if proc.returncode != 0:
        return [], [], proc.stderr.strip() or "git status failed"
    tracked: list[str] = []
    untracked: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("?? "):
            untracked.append(line[3:])
        elif line.strip():
            tracked.append(line)
    seen = {normalize_untracked(item) for item in untracked}
    for allowed in allowed_untracked:
        allowed_path = path / allowed.rstrip("/")
        marker = allowed.rstrip("/") + ("/" if allowed_path.is_dir() else "")
        if allowed_path.exists() and normalize_untracked(marker) not in seen:
            untracked.append(marker)
            seen.add(normalize_untracked(marker))
    return tracked, untracked, None


def which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def fake_active_paths() -> list[Path]:
    raw = os.environ.get("COS_WORKTREE_SWEEPER_FAKE_ACTIVE_PATHS", "")
    return [Path(item).resolve() for item in raw.split(os.pathsep) if item]


def path_has_lsof_activity(path: Path) -> bool | None:
    if os.environ.get("COS_WORKTREE_SWEEPER_DISABLE_LSOF") == "1":
        return None
    lsof = which("lsof")
    if not lsof:
        return None
    proc = run_command([lsof, "+D", str(path)])
    if proc.returncode == 0 and proc.stdout.strip():
        return True
    if proc.returncode in (0, 1):
        return False
    return None


def path_has_process_activity(path: Path) -> bool:
    for active in fake_active_paths():
        if active == path.resolve() or path_under(active, path):
            return True
    lsof_result = path_has_lsof_activity(path)
    if lsof_result is not None:
        return lsof_result
    proc = run_command(["ps", "-axo", "pid=,command="])
    if proc.returncode != 0:
        return True
    needle = str(path.resolve())
    quoted = shlex.quote(needle)
    return any((needle in line or quoted in line) and "cos_worktree_sweeper.py" not in line for line in proc.stdout.splitlines())


def age_seconds(path: Path) -> float:
    return max(0.0, time.time() - path.stat().st_mtime)


def classify_worktree(worktree: Worktree, repo: Path, safe_prefixes: list[Path], allowed_untracked: tuple[str, ...], ttl_seconds: int) -> dict[str, Any]:
    path = worktree.path
    reasons: list[str] = []
    blockers: list[str] = []
    if path == repo.resolve():
        blockers.append("primary_worktree")
    if not path.exists():
        blockers.append("missing_path")
    if not worktree.detached:
        blockers.append("branch_worktree")
    else:
        reasons.append("detached")
    if not any(path_under(path, prefix) or path == prefix for prefix in safe_prefixes):
        blockers.append("outside_safe_prefix")
    tracked: list[str] = []
    untracked: list[str] = []
    status_error = None
    current_age = 0
    if path.exists():
        current_age = int(age_seconds(path))
        if current_age < ttl_seconds:
            blockers.append("ttl_not_elapsed")
        else:
            reasons.append("ttl_elapsed")
        if path_has_process_activity(path):
            blockers.append("active_process_or_open_file")
        else:
            reasons.append("inactive")
        tracked, untracked, status_error = git_status(path, allowed_untracked)
        if status_error:
            blockers.append("status_unreadable")
        if tracked:
            blockers.append("tracked_changes")
        blocked_untracked = [item for item in untracked if not untracked_allowed(item, allowed_untracked)]
        if blocked_untracked:
            blockers.append("non_allowlisted_untracked")
        elif untracked:
            reasons.append("only_allowlisted_untracked")
        else:
            reasons.append("clean_untracked")
    return {"path": str(path), "head": worktree.head, "branch": worktree.branch, "detached": worktree.detached, "decision": "remove-candidate" if not blockers else "keep", "reasons": reasons, "blockers": blockers, "age_seconds": current_age, "tracked_changes": tracked, "untracked": untracked, "status_error": status_error}


def remove_candidate(repo: Path, path: str) -> dict[str, Any]:
    proc = run_command(["git", "worktree", "remove", "--force", path], repo)
    return {"path": path, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "removed": proc.returncode == 0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getcwd())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ttl-hours", type=float, default=2.0)
    parser.add_argument("--ttl-seconds", type=int)
    parser.add_argument("--safe-prefix", action="append", default=[])
    parser.add_argument("--no-default-safe-prefixes", action="store_true")
    parser.add_argument("--allow-untracked", action="append", default=list(DEFAULT_ALLOWED_UNTRACKED))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).resolve()
    ttl_seconds = args.ttl_seconds if args.ttl_seconds is not None else int(args.ttl_hours * 3600)
    safe_prefixes = ([] if args.no_default_safe_prefixes else default_safe_prefixes()) + [Path(item).resolve() for item in args.safe_prefix]
    allowed_untracked = tuple(args.allow_untracked)
    reports = [classify_worktree(worktree, repo, safe_prefixes, allowed_untracked, ttl_seconds) for worktree in list_worktrees(repo)]
    removed: list[dict[str, Any]] = []
    if args.apply:
        for report in reports:
            if report["decision"] == "remove-candidate":
                removed.append(remove_candidate(repo, report["path"]))
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "repo": str(repo), "ttl_seconds": ttl_seconds, "safe_prefixes": [str(prefix) for prefix in safe_prefixes], "allowed_untracked": list(allowed_untracked), "removed": removed, "worktrees": reports}, indent=2, sort_keys=True))
    return 1 if any(item.get("returncode") not in (None, 0) for item in removed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
