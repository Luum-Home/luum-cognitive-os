#!/usr/bin/env python3
# SCOPE: both
"""Read-only checklist for branches, worktrees, stashes, and dirty WIP.

This doctor is intentionally projectable: keep it in the Cognitive OS repo and
run it against any consumer repository with ``--project-dir``.

Extended dimensions (P3.3):
  --sessions    Active session metadata from .cognitive-os/sessions/
  --orphans     Orphan-notifier JSONL or reflog-based scan
  --worktrees   Read .git/worktrees/ directly (no destructive git worktree cmd)
  --stashes     Git stash list with auto-pre-agent provenance
  --claims      Active task claims from .cognitive-os/tasks/active-claims.json
  --race-risks  Heuristic multi-session/worktree/stash race-condition detection
  --all         Enable all dimensions above
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_BRANCH_PATTERN = "codex/preserve-*,codex/stash-*"
DEFAULT_STASH_WARN_TTL = 600
DEFAULT_STASH_BLOCK_TTL = 3600

# Race-risk heuristics
RACE_RISK_STALE_STASH_THRESHOLD = 3600  # 1 hour

# ---------------------------------------------------------------------------
# ADR-121: Preflight gate refinements
# ---------------------------------------------------------------------------

# Glob patterns for paths that belong to ephemeral validation workspaces.
# These should never trigger BLOCK — they are transient and self-cleaning.
# Add new patterns here when new ephemeral path conventions are introduced.
EPHEMERAL_PATH_PATTERNS: tuple[str, ...] = (
    "*/cos-validation-capsules/*",
    "*/luum-agent-os-validation-*",
)

# Subagent types that are structurally read-only and cannot write to the main
# worktree.  Matches the preamble convention in templates/agent-preamble.md.
READ_ONLY_SUBAGENT_TYPES: frozenset[str] = frozenset(
    {"Explore", "Plan", "Code Reviewer", "Security Engineer"}
)


def _ephemeral_tmpdir() -> str:
    """Return the resolved $TMPDIR (or /tmp) for ephemeral path matching."""
    raw = os.environ.get("TMPDIR", "") or "/tmp"
    try:
        return str(Path(raw).resolve())
    except OSError:
        return raw


def _is_ephemeral_path(path: Path) -> bool:
    """Return True if *path* matches any ephemeral workspace pattern.

    Matches against EPHEMERAL_PATH_PATTERNS (glob). Do not classify every
    child of $TMPDIR as ephemeral: pytest fixtures, ad-hoc consumer repos, and
    temporary linked worktrees often live under TMPDIR while still representing
    real WIP that the inventory must report.
    """
    path_str = str(path)
    for pattern in EPHEMERAL_PATH_PATTERNS:
        if fnmatch.fnmatch(path_str, pattern):
            return True
    return False


def _canonical_path(path: str | Path) -> str:
    """Return the canonical (resolved) string form of a path."""
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(path)


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
        timeout=60,
    )


def is_git_repo(project: Path) -> bool:
    return git(project, ["rev-parse", "--is-inside-work-tree"]).returncode == 0


def git_common_dir(project: Path) -> Path | None:
    result = git(project, ["rev-parse", "--git-common-dir"])
    if result.returncode != 0:
        fallback = project / ".git"
        if fallback.exists() and fallback.is_dir():
            return fallback.resolve()
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = project / path
    return path.resolve()


def worktree_status(path: Path) -> dict[str, Any]:
    if path.exists() and is_git_repo(path):
        return collect_status(path)
    return {"is_dirty": None, "counts": {}, "entries": []}


def _status_paths(status: dict[str, Any]) -> list[str]:
    """Return changed paths from a ``collect_status`` payload."""
    paths: list[str] = []
    for entry in status.get("entries", []):
        path = entry.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return sorted(set(paths))


def branch_from_head_file(head_file: Path) -> str | None:
    if not head_file.exists():
        return None
    content = head_file.read_text(encoding="utf-8").strip()
    if content.startswith("ref: refs/heads/"):
        return content.removeprefix("ref: refs/heads/")
    return None


def short_head_from_head_file(head_file: Path) -> str | None:
    if not head_file.exists():
        return None
    content = head_file.read_text(encoding="utf-8").strip()
    if content.startswith("ref:"):
        return None
    return content[:12] if content else None


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


def is_runtime_status_path(path: str) -> bool:
    """Return True for untracked COS runtime files created by coordination gates."""

    runtime_prefixes = (
        ".cognitive-os/tasks/",
        ".cognitive-os/sessions/",
        ".cognitive-os/runtime/",
        ".cognitive-os/metrics/",
        ".cognitive-os/reports/",
    )
    return any(path.startswith(prefix) for prefix in runtime_prefixes)


def collect_status(project: Path) -> dict[str, Any]:
    result = git(project, ["status", "--porcelain=v2", "--branch", "--untracked-files=all"])
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
            if is_runtime_status_path(path):
                continue
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
    patterns = [item.strip() for item in pattern.split(",") if item.strip()]
    branches = sorted(
        branch
        for branch in raw.stdout.splitlines()
        if any(fnmatch.fnmatch(branch, item) for item in patterns)
    )
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


def collect_worktrees(
    project: Path,
    *,
    skip_ephemeral: bool = True,
) -> list[dict[str, Any]]:
    result = git(project, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    for item in parse_worktree_porcelain(result.stdout):
        path = Path(item.get("worktree", "")).resolve()
        # ADR-121: skip ephemeral validation workspace paths (unless disabled)
        if skip_ephemeral and _is_ephemeral_path(path):
            continue
        branch = item.get("branch", "")
        if branch.startswith("refs/heads/"):
            branch = branch.removeprefix("refs/heads/")
        status = worktree_status(path)
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
                "dirty_files": _status_paths(status)[:200],
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


# ---------------------------------------------------------------------------
# P3.3 NEW DIMENSIONS
# ---------------------------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    """Return True if the given PID exists in the OS process table.

    Note: on macOS/Linux, PIDs can be reused, so True only means *some*
    process with that PID is alive — not necessarily the original session.
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # We don't own it, but it exists
        return True
    except OSError:
        return False


def collect_sessions(project: Path) -> list[dict[str, Any]]:
    """Read active-sessions.json + per-session meta.json files.

    Returns a list of dicts with keys:
      id, pid, alive, age_seconds, start_time, working_directory, current_task
    """
    sessions_dir = project / ".cognitive-os" / "sessions"
    rows: list[dict[str, Any]] = []
    now = int(time.time())

    # 1. Collect IDs from active-sessions.json (authoritative registry)
    active_ids: set[str] = set()
    active_sessions_file = sessions_dir / "active-sessions.json"
    if active_sessions_file.exists():
        try:
            data = json.loads(active_sessions_file.read_text(encoding="utf-8"))
            for entry in data.get("sessions", []):
                sid = entry.get("id")
                if sid:
                    active_ids.add(sid)
        except (OSError, json.JSONDecodeError):
            pass

    # 2. Walk session directories to read meta.json + tasks.json
    if sessions_dir.exists():
        for session_dir in sorted(sessions_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            sid = session_dir.name
            meta_file = session_dir / "meta.json"
            if not meta_file.exists():
                continue
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}

            pid = meta.get("pid")
            start_epoch = meta.get("start_epoch") or 0
            age = max(0, now - start_epoch) if start_epoch else None
            alive = _pid_alive(int(pid)) if pid else False

            # Current task: last in_progress entry from tasks.json
            current_task: str | None = None
            tasks_file = session_dir / "tasks.json"
            if tasks_file.exists():
                try:
                    tasks_data = json.loads(tasks_file.read_text(encoding="utf-8"))
                    tasks_list = tasks_data if isinstance(tasks_data, list) else tasks_data.get("tasks", [])
                    for t in reversed(tasks_list):
                        if isinstance(t, dict) and t.get("status") == "in_progress":
                            current_task = t.get("description")
                            break
                except (OSError, json.JSONDecodeError):
                    pass

            rows.append(
                {
                    "id": sid,
                    "pid": pid,
                    "alive": alive,
                    "age_seconds": age,
                    "start_time": meta.get("start_time"),
                    "working_directory": meta.get("working_directory"),
                    "current_task": current_task,
                    "in_active_registry": sid in active_ids,
                }
            )

    return rows


def collect_session_fs_stats(project: Path) -> dict[str, Any]:
    """Count session filesystem artifacts independently from active registry."""
    sessions_dir = project / ".cognitive-os" / "sessions"
    if not sessions_dir.exists():
        return {"session_dir_count": 0, "marker_file_count": 0, "total_artifact_count": 0, "path": str(sessions_dir)}
    session_dir_count = 0
    marker_file_count = 0
    for child in sessions_dir.iterdir():
        if child.is_dir():
            session_dir_count += 1
        elif child.is_file() and child.name != "active-sessions.json":
            marker_file_count += 1
    return {
        "session_dir_count": session_dir_count,
        "marker_file_count": marker_file_count,
        "total_artifact_count": session_dir_count + marker_file_count,
        "path": str(sessions_dir),
    }


def collect_orphans(project: Path) -> list[dict[str, Any]]:
    """Return orphan-commit records.

    Priority: read .cognitive-os/metrics/orphan-notifier.jsonl if it exists
    (written by P3.1 orphan-notifier hook). Fallback: scan git reflog for
    commits that are not reachable from any branch ref.
    """
    rows: list[dict[str, Any]] = []

    # --- Primary: orphan-notifier JSONL from P3.1 ---
    notifier_file = project / ".cognitive-os" / "metrics" / "orphan-notifier.jsonl"
    if notifier_file.exists():
        try:
            for line in notifier_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    rows.append(record)
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
        return rows

    # --- Fallback: reflog-based scan ---
    # Collect all reachable commits from refs
    reachable_result = git(project, ["rev-list", "--all"])
    reachable: set[str] = set()
    if reachable_result.returncode == 0:
        reachable = set(reachable_result.stdout.splitlines())

    # Walk reflog entries
    reflog_result = git(project, ["reflog", "--format=%H %gD %gs"])
    if reflog_result.returncode != 0:
        return rows

    seen: set[str] = set()
    for line in reflog_result.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 1:
            continue
        commit_hash = parts[0]
        ref_name = parts[1] if len(parts) > 1 else "unknown"
        subject = parts[2] if len(parts) > 2 else ""
        if commit_hash in reachable or commit_hash in seen:
            continue
        seen.add(commit_hash)
        rows.append(
            {
                "commit": commit_hash[:12],
                "full_hash": commit_hash,
                "ref": ref_name,
                "subject": subject,
                "source": "reflog-scan",
            }
        )
    return rows


def collect_worktrees_direct(
    project: Path,
    *,
    skip_ephemeral: bool = True,
) -> list[dict[str, Any]]:
    """Read .git/worktrees/ directly and include dirty status.

    This path is independent of IDE state and avoids relying on the
    human-facing `git worktree list` output for linked-worktree discovery.
    """
    common_dir = git_common_dir(project)
    rows: list[dict[str, Any]] = []

    main_status = worktree_status(project)
    main_git_dir = common_dir or (project / ".git")
    # ADR-121: skip main project path if ephemeral (edge case, but consistent)
    if not skip_ephemeral or not _is_ephemeral_path(project.resolve()):
        rows.append(
            {
                "path": str(project.resolve()),
                "branch": main_status.get("branch") or current_branch(project) or branch_from_head_file(main_git_dir / "HEAD"),
                "head": main_status.get("head") or current_head(project) or short_head_from_head_file(main_git_dir / "HEAD"),
                "source": "main",
                "locked": False,
                "prunable": False,
                "is_current_project": True,
                "dirty": main_status.get("is_dirty"),
                "dirty_counts": main_status.get("counts", {}),
                "dirty_files": _status_paths(main_status)[:200],
            }
        )

    if common_dir is None:
        return rows
    worktrees_dir = common_dir / "worktrees"
    if not worktrees_dir.exists():
        return rows

    for wt_entry in sorted(worktrees_dir.iterdir()):
        if not wt_entry.is_dir():
            continue
        name = wt_entry.name
        head_file = wt_entry / "HEAD"
        gitdir_file = wt_entry / "gitdir"
        locked_file = wt_entry / "locked"

        branch: str | None = None
        head: str | None = None

        if head_file.exists():
            content = head_file.read_text(encoding="utf-8").strip()
            if content.startswith("ref: refs/heads/"):
                branch = content.removeprefix("ref: refs/heads/")
            else:
                head = content[:12]

        wt_path: str | None = None
        if gitdir_file.exists():
            gitdir_content = gitdir_file.read_text(encoding="utf-8").strip()
            wt_path = str(Path(gitdir_content).parent)

        locked = locked_file.exists()
        prunable = False
        if gitdir_file.exists():
            target = Path(gitdir_file.read_text(encoding="utf-8").strip())
            prunable = not target.parent.exists()

        path = Path(wt_path).resolve() if wt_path else Path(name)
        # ADR-121: skip ephemeral validation workspace paths (unless disabled)
        if skip_ephemeral and _is_ephemeral_path(path):
            continue
        status = worktree_status(path)
        rows.append(
            {
                "path": str(path),
                "branch": branch or status.get("branch"),
                "head": head or status.get("head"),
                "source": "linked",
                "locked": locked,
                "prunable": prunable,
                "is_current_project": path == project.resolve(),
                "dirty": status.get("is_dirty"),
                "dirty_counts": status.get("counts", {}),
                "dirty_files": _status_paths(status)[:200],
            }
        )

    return rows


def process_activity_for_worktree(path: Path) -> dict[str, Any]:
    """Return best-effort process activity for a worktree path.

    This is a liveness hint, not proof of ownership. A process with cwd or open
    files under a worktree means cleanup must fail closed; no process found does
    not prove the WIP is safe to delete.
    """
    needle = str(path.resolve())
    rows: list[dict[str, Any]] = []
    ps_proc = subprocess.run(
        ["ps", "-axo", "pid=,comm=,command="],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,  # timeout per ADR-278 (default - review)
    )
    if ps_proc.returncode == 0:
        for line in ps_proc.stdout.splitlines():
            if needle not in line:
                continue
            parts = line.strip().split(None, 2)
            if not parts:
                continue
            rows.append(
                {
                    "source": "ps",
                    "pid": parts[0],
                    "command": parts[2] if len(parts) >= 3 else line.strip(),
                }
            )

    lsof_candidates = [Path(item) / "lsof" for item in os.environ.get("PATH", "").split(os.pathsep) if item]
    lsof_candidates.extend([Path("/usr/sbin/lsof"), Path("/usr/bin/lsof")])
    lsof_bin = next((candidate for candidate in lsof_candidates if candidate.is_file()), None)
    lsof_available = lsof_bin is not None
    if lsof_bin is not None:
        lsof_proc = subprocess.run(
            [str(lsof_bin), "+D", needle],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,  # timeout per ADR-278 (default - review)
        )
        if lsof_proc.returncode == 0:
            for line in lsof_proc.stdout.splitlines()[1:20]:
                parts = line.split()
                if len(parts) < 2:
                    continue
                rows.append({"source": "lsof", "pid": parts[1], "command": parts[0], "raw": line[:300]})

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (str(row.get("source")), str(row.get("pid")), str(row.get("command")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return {"available": lsof_available or ps_proc.returncode == 0, "count": len(deduped), "processes": deduped[:20]}


def collect_edit_lock_for_path(project: Path, rel_path: str) -> dict[str, Any]:
    """Return edit-coop lock state for a path without mutating the lock."""
    coop = project / "scripts" / "edit-coop.sh"
    if not coop.exists():
        return {"available": False, "state": "unknown", "detail": "scripts/edit-coop.sh not found"}
    proc = subprocess.run(
        ["bash", str(coop), "check", rel_path],
        cwd=str(project),
        env={**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(project)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,  # timeout per ADR-278 (default - review)
    )
    output = (proc.stdout + proc.stderr).strip()
    if "FREE" in output:
        state = "free"
    elif "STALE" in output:
        state = "stale"
    elif "OWN" in output:
        state = "own"
    elif "HELD" in output:
        state = "held"
    else:
        state = "unknown"
    return {"available": True, "state": state, "exit_code": proc.returncode, "detail": output}


def _agent_id_from_stash(stash: dict[str, Any]) -> str | None:
    subject = str(stash.get("subject") or "")
    match = re.search(r"(toolu_[A-Za-z0-9]+|native-agent-[A-Za-z0-9_-]+)", subject)
    return match.group(1) if match else None


def collect_agent_heartbeat(project: Path, agent_id: str) -> dict[str, Any]:
    """Return last heartbeat-like row for an agent id from local metrics."""
    candidates = [
        project / ".cognitive-os" / "metrics" / "agent-heartbeat.jsonl",
        project / ".cognitive-os" / "metrics" / "native-agent-heartbeat.jsonl",
    ]
    last: dict[str, Any] | None = None
    for path in candidates:
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if agent_id not in line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                row_agent = row.get("agent_id") or (row.get("payload") or {}).get("agent_id")
                if row_agent == agent_id:
                    last = row
        except OSError:
            continue
    if last is None:
        return {"agent_id": agent_id, "seen": False, "alive": None, "last_event": None}
    payload = last.get("payload") if isinstance(last.get("payload"), dict) else {}
    alive = last.get("alive", payload.get("alive"))
    event_type = last.get("event_type") or last.get("event")
    ts = last.get("timestamp") or last.get("ts") or last.get("ended_at") or last.get("started_at")
    return {"agent_id": agent_id, "seen": True, "alive": alive, "last_event": event_type, "last_timestamp": ts}


def collect_stashes_by_worktree(
    project: Path,
    worktrees: list[dict[str, Any]],
    warn_ttl: int,
    block_ttl: int,
) -> list[dict[str, Any]]:
    """Run stash inspection from each worktree path.

    Git stores stash refs per repository, but running the check from every
    linked worktree proves the inventory is IDE-independent and records which
    worktree paths were inspected.
    """
    rows: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for worktree in worktrees:
        raw_path = worktree.get("path")
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        path_key = str(path)
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)
        if not path.exists() or not is_git_repo(path):
            rows.append(
                {
                    "worktree_path": path_key,
                    "worktree_branch": worktree.get("branch"),
                    "is_current_project": path == project.resolve(),
                    "available": False,
                    "stash_count": 0,
                    "stashes": [],
                }
            )
            continue
        stashes = collect_stashes(path, warn_ttl, block_ttl)
        rows.append(
            {
                "worktree_path": path_key,
                "worktree_branch": worktree.get("branch"),
                "is_current_project": path == project.resolve(),
                "available": True,
                "stash_count": len(stashes),
                "stashes": stashes,
            }
        )
    return rows


def collect_stashes_extended(project: Path, warn_ttl: int, block_ttl: int) -> list[dict[str, Any]]:
    """Like collect_stashes but also parses branch provenance from stash messages.

    Adds keys: on_branch, is_manual_preserve, provenance_tag
    """
    base = collect_stashes(project, warn_ttl, block_ttl)
    for stash in base:
        subject = stash.get("subject", "")
        # Parse "On <branch>: <msg>" format
        on_branch: str | None = None
        if subject.startswith("On ") and ": " in subject:
            on_branch = subject[3:subject.index(": ")]
        stash["on_branch"] = on_branch
        # Detect manual-preserve from either the raw subject or the message part
        _msg_part = subject[subject.index(": ") + 2:] if ": " in subject else subject
        stash["is_manual_preserve"] = _msg_part.startswith("manual-preserve-")
        # Derive a short tag
        if stash["is_auto_pre_agent"]:
            stash["provenance_tag"] = "auto-pre-agent"
        elif stash["is_manual_preserve"]:
            stash["provenance_tag"] = "manual-preserve"
        else:
            stash["provenance_tag"] = "user"
    return base


def collect_claims(project: Path) -> list[dict[str, Any]]:
    """Read .cognitive-os/tasks/active-claims.json (written by P1.1 task-claim hook).

    Falls back gracefully if the file does not exist.
    """
    claims_file = project / ".cognitive-os" / "tasks" / "active-claims.json"
    if not claims_file.exists():
        return []
    try:
        data = json.loads(claims_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("claims", [])
    return []


def _normalize_requested_path(project: Path, raw: str) -> str:
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        try:
            return str(candidate.resolve().relative_to(project.resolve()))
        except ValueError:
            return str(candidate)
    return str(candidate)


def _claim_mentions_path(claim: dict[str, Any], rel_path: str) -> bool:
    expected = claim.get("expected_files") or claim.get("files") or []
    if not isinstance(expected, list):
        return False
    return any(str(item) == rel_path for item in expected)


def _stash_mentions_path(stash: dict[str, Any], rel_path: str) -> bool:
    files = stash.get("files") or []
    if not isinstance(files, list):
        return False
    return any(str(item) == rel_path for item in files)


def _worktree_mentions_path(worktree: dict[str, Any], rel_path: str) -> bool:
    files = worktree.get("dirty_files") or []
    if not isinstance(files, list):
        return False
    return any(str(item) == rel_path for item in files)


def collect_path_ownership(project: Path, paths: list[str], payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Join WIP/liveness signals for selected paths.

    The result is intentionally conservative. Dirty linked worktrees, active
    claims, matching stashes, or live processes all require operator review.
    A preserved branch is evidence that a copy exists, not evidence that the
    original producer is inactive.
    """
    combined_worktrees: list[dict[str, Any]] = []
    seen_worktree_paths: set[str] = set()
    for key in ("worktrees", "worktrees_direct"):
        for worktree in payload.get(key, []):
            path = str(worktree.get("path") or "")
            if not path or path in seen_worktree_paths:
                continue
            seen_worktree_paths.add(path)
            combined_worktrees.append(worktree)

    claims = payload.get("claims") or collect_claims(project)
    stashes = payload.get("stashes_extended") or collect_stashes_extended(
        project,
        DEFAULT_STASH_WARN_TTL,
        DEFAULT_STASH_BLOCK_TTL,
    )

    rows: list[dict[str, Any]] = []
    for raw in paths:
        rel_path = _normalize_requested_path(project, raw)
        current_dirty = any(entry.get("path") == rel_path for entry in payload.get("status", {}).get("entries", []))
        dirty_worktrees: list[dict[str, Any]] = []
        for worktree in combined_worktrees:
            if not _worktree_mentions_path(worktree, rel_path):
                continue
            activity = process_activity_for_worktree(Path(worktree["path"]))
            dirty_worktrees.append(
                {
                    "path": worktree.get("path"),
                    "branch": worktree.get("branch"),
                    "is_current_project": worktree.get("is_current_project"),
                    "dirty_counts": worktree.get("dirty_counts"),
                    "process_activity": activity,
                }
            )

        matching_claims = [claim for claim in claims if _claim_mentions_path(claim, rel_path)]
        matching_stashes = [stash for stash in stashes if _stash_mentions_path(stash, rel_path)]
        for stash in matching_stashes:
            agent_id = _agent_id_from_stash(stash)
            stash["agent_id"] = agent_id
            stash["agent_heartbeat"] = collect_agent_heartbeat(project, agent_id) if agent_id else None
        edit_lock = collect_edit_lock_for_path(project, rel_path)
        preserve_branches = [
            branch["branch"]
            for branch in payload.get("preserve_branches", [])
            if rel_path in changed_files_between(project, payload.get("base_ref", "HEAD"), branch["branch"])
        ]

        has_noncurrent_dirty = any(not item.get("is_current_project") for item in dirty_worktrees)
        has_live_process = any((item.get("process_activity") or {}).get("count", 0) for item in dirty_worktrees)
        has_active_claim = any(str(claim.get("status", "active")) == "active" for claim in matching_claims)
        has_held_lock = edit_lock.get("state") in {"held", "own"}
        has_stash = bool(matching_stashes)
        has_preserve_copy = bool(preserve_branches)

        if has_noncurrent_dirty or has_live_process or has_active_claim or has_held_lock:
            status = "active_or_unknown"
            action = "Do not clean/drop/merge automatically; coordinate with the owning worktree/session or archive explicitly after liveness review."
        elif current_dirty:
            status = "current_wip"
            action = "Commit, preserve, or explicitly discard current worktree WIP before claiming closure."
        elif has_stash:
            status = "stashed_wip"
            action = "Inspect matching stashes and preserve/apply/drop only with operator intent."
        elif has_preserve_copy:
            status = "preserved_copy_only"
            action = "A review branch copy exists, but this alone does not prove the original agent is inactive."
        else:
            status = "clear"
            action = "No matching WIP signals found by this inventory."

        rows.append(
            {
                "path": rel_path,
                "status": status,
                "current_dirty": current_dirty,
                "dirty_worktrees": dirty_worktrees,
                "edit_lock": edit_lock,
                "claims": matching_claims,
                "stashes": matching_stashes,
                "preserve_branches": preserve_branches,
                "operator_review_required": status != "clear",
                "action": action,
            }
        )
    return rows


@dataclass
class RaceRisk:
    code: str
    description: str
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "description": self.description, "details": self.details}


def collect_race_risks(
    sessions: list[dict[str, Any]],
    worktrees: list[dict[str, Any]],
    stashes: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    session_fs_stats: dict[str, Any] | None = None,
    volume_alarm_threshold: int = 1000,
) -> list[dict[str, Any]]:
    """Heuristic race-condition detection.

    Flags:
      (a) >1 session has the same task in_progress
      (b) >1 worktree on the same branch
      (c) >1 hour-old stash from a session not currently active
      (d) Sessions in active registry but whose PID is not alive (zombie sessions)
      (e) Session filesystem artifact volume exceeds threshold
    """
    risks: list[RaceRisk] = []

    # (a) Multiple sessions with same current_task
    task_to_sessions: dict[str, list[str]] = {}
    for s in sessions:
        task = s.get("current_task")
        if task and s.get("alive"):
            task_to_sessions.setdefault(task, []).append(s["id"])
    for task, sids in task_to_sessions.items():
        if len(sids) > 1:
            risks.append(
                RaceRisk(
                    code="multi-session-same-task",
                    description="Multiple live sessions have the same task in_progress",
                    details=[f"task={task!r}", f"sessions={sids}"],
                )
            )

    # (b) Multiple worktrees on the same branch
    # ADR-121: deduplicate by canonical (realpath) so that the same physical
    # worktree appearing in both worktrees[] and worktrees_direct[] does not
    # trigger a false self-collision race risk.
    branch_to_worktrees: dict[str, list[str]] = {}
    seen_canonical: set[str] = set()
    for wt in worktrees:
        branch = wt.get("branch")
        canon = _canonical_path(wt.get("path", ""))
        if canon in seen_canonical:
            continue
        seen_canonical.add(canon)
        if branch:
            branch_to_worktrees.setdefault(branch, []).append(wt.get("path", "?"))
    for branch, paths in branch_to_worktrees.items():
        if len(paths) > 1:
            risks.append(
                RaceRisk(
                    code="multi-worktree-same-branch",
                    description="Multiple worktrees share the same branch",
                    details=[f"branch={branch!r}", f"paths={paths}"],
                )
            )

    # (c) >1 hour stash from a session no longer active
    active_session_ids: set[str] = {s["id"] for s in sessions if s.get("alive")}
    for stash in stashes:
        age = stash.get("age_seconds", 0) or 0
        subject = stash.get("subject", "")
        if age < RACE_RISK_STALE_STASH_THRESHOLD:
            continue
        # Try to match stash subject to a session ID prefix
        stash_from_dead_session = True
        for sid in active_session_ids:
            if sid[:8] in subject:
                stash_from_dead_session = False
                break
        if stash_from_dead_session:
            risks.append(
                RaceRisk(
                    code="stale-orphan-stash",
                    description="Stash older than 1 hour not linked to any active session",
                    details=[
                        f"ref={stash['ref']}",
                        f"age={age}s",
                        f"subject={subject!r}",
                    ],
                )
            )

    # (d) Sessions registered in active-sessions.json but PID no longer alive
    # These are "zombie" registry entries that can mislead other tools into
    # thinking more work is in flight than actually is.
    zombie_sessions = [
        s for s in sessions
        if s.get("in_active_registry") and not s.get("alive")
    ]
    if zombie_sessions:
        risks.append(
            RaceRisk(
                code="zombie-registry-sessions",
                description="Sessions in active-sessions.json whose PID is no longer alive",
                details=[f"count={len(zombie_sessions)}"]
                + [f"id={s['id']} pid={s.get('pid')}" for s in zombie_sessions[:5]],
            )
        )

    if session_fs_stats:
        total = int(session_fs_stats.get("total_artifact_count") or 0)
        if total > volume_alarm_threshold:
            risks.append(
                RaceRisk(
                    code="session-volume-exceeded",
                    description="Session filesystem artifact volume exceeds configured threshold",
                    details=[
                        f"total={total}",
                        f"threshold={volume_alarm_threshold}",
                        f"session_dirs={session_fs_stats.get('session_dir_count', 0)}",
                        f"marker_files={session_fs_stats.get('marker_file_count', 0)}",
                    ],
                )
            )

    return [r.to_dict() for r in risks]


# ---------------------------------------------------------------------------
# ADR-121: Branch-aware severity helper
# ---------------------------------------------------------------------------


def _classify_worktree_finding(
    worktree: dict[str, Any],
    current_branch: str | None,
    current_path: Path,
    allow_read_only: bool,
) -> str:
    """Return ``"BLOCK"`` or ``"WARN"`` for a dirty linked worktree.

    Rules (applied in order):
    1. If *allow_read_only* is True → WARN (read-only agents cannot mutate).
    2. If the worktree's branch matches *current_branch* (including detached
       HEAD identity ``detached@<sha12>``) → BLOCK (same-branch race risk).
    3. If the worktree path is under *current_path* target space → BLOCK.
    4. Otherwise → WARN (different branch, low risk of conflict).

    Detached HEAD identity uses the first 12 chars of the commit SHA so that
    two detached worktrees at the *same* commit count as colliding.
    """
    if allow_read_only:
        return "WARN"

    wt_branch: str | None = worktree.get("branch")
    wt_head: str | None = worktree.get("head")

    # Build comparable branch identity for the worktree
    if wt_branch:
        wt_identity = wt_branch
    elif wt_head:
        wt_identity = f"detached@{wt_head[:12]}"
    else:
        wt_identity = None

    # Build comparable branch identity for the current worktree
    if current_branch:
        cur_identity = current_branch
    else:
        # Derive detached identity from HEAD — best effort via git
        cur_identity = None

    if wt_identity and cur_identity and wt_identity == cur_identity:
        return "BLOCK"

    # Check if worktree path is under the current project path (sub-path)
    wt_path_str = worktree.get("path", "")
    if wt_path_str:
        try:
            Path(wt_path_str).resolve().relative_to(current_path.resolve())
            return "BLOCK"
        except ValueError:
            pass

    return "WARN"


# ---------------------------------------------------------------------------
# Findings builder (original + extended)
# ---------------------------------------------------------------------------


def build_findings(
    payload: dict[str, Any],
    allow_read_only: bool = False,
) -> list[Finding]:
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
    # ADR-121: derive current branch/path for branch-aware severity
    current_branch_val: str | None = payload.get("status", {}).get("branch")
    current_path_val = Path(payload.get("project", "."))

    worktrees_by_path: dict[str, dict[str, Any]] = {}
    for source_key in ("worktrees", "worktrees_direct"):
        for worktree in payload.get(source_key, []):
            path = worktree.get("path")
            if path and path not in worktrees_by_path:
                worktrees_by_path[path] = worktree
    for worktree in worktrees_by_path.values():
        if worktree.get("is_current_project"):
            continue
        if worktree.get("dirty"):
            level = _classify_worktree_finding(
                worktree,
                current_branch_val,
                current_path_val,
                allow_read_only,
            )
            findings.append(
                Finding(
                    level,
                    "linked-worktree-dirty",
                    worktree["path"],
                    f"branch={worktree.get('branch') or 'detached'} counts={worktree.get('dirty_counts')}",
                    "Inspect and commit, preserve, or discard linked worktree WIP before pruning, deleting branches, or claiming cleanup complete.",
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
    for group in payload.get("worktree_stashes", []):
        if group.get("is_current_project") or not group.get("stash_count"):
            continue
        findings.append(
            Finding(
                "BLOCK",
                "linked-worktree-stashes-present",
                group["worktree_path"],
                f"branch={group.get('worktree_branch') or 'detached'} stashes={group.get('stash_count')}",
                "Inspect linked worktree stashes before cleanup; use `git -C <worktree> stash list` and show/apply/drop only after review.",
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
    # ADR-121 kill-switch: COS_PREFLIGHT_STRICT=1 restores pre-refinement
    # conservative behavior. Log to stderr so the JSON payload is unaffected.
    _strict_env = os.environ.get("COS_PREFLIGHT_STRICT", "0")
    if _strict_env == "1":
        print(
            "COS_PREFLIGHT_STRICT=1: ADR-121 refinements bypassed; "
            "reverting to pre-refinement blocking behavior.",
            file=sys.stderr,
        )
        args.allow_read_only = False
        args._preflight_strict_override = True
    else:
        if not hasattr(args, "allow_read_only"):
            args.allow_read_only = False
        args._preflight_strict_override = False

    project = Path(args.project_dir).expanduser().resolve()
    if not is_git_repo(project):
        raise SystemExit(f"Not a git repository: {project}")
    # ADR-121: when strict override is active, disable ephemeral filter so that
    # all worktrees (including validation capsule paths) are included — this
    # restores the pre-refinement conservative behavior.
    _skip_eph = not getattr(args, "_preflight_strict_override", False)

    payload: dict[str, Any] = {
        "project": str(project),
        "base_ref": args.base_ref,
        "branch_pattern": args.branch_pattern,
        "status": collect_status(project),
        "preserve_branches": list_branches(project, args.branch_pattern, args.base_ref),
        "worktrees": collect_worktrees(project, skip_ephemeral=_skip_eph),
        "stashes": collect_stashes(project, args.stash_warn_ttl, args.stash_block_ttl),
        "session_fs_stats": collect_session_fs_stats(project),
    }
    payload["worktree_stashes"] = collect_stashes_by_worktree(
        project, payload["worktrees"], args.stash_warn_ttl, args.stash_block_ttl
    )

    # P3.3 dimensions
    want_sessions = getattr(args, "sessions", False) or getattr(args, "all", False)
    want_orphans = getattr(args, "orphans", False) or getattr(args, "all", False)
    want_worktrees_direct = getattr(args, "worktrees_direct", False) or getattr(args, "all", False)
    want_stashes_extended = getattr(args, "stashes_extended", False) or getattr(args, "all", False)
    want_claims = getattr(args, "claims", False) or getattr(args, "all", False)
    want_race_risks = getattr(args, "race_risks", False) or getattr(args, "all", False)

    if want_sessions:
        payload["sessions"] = collect_sessions(project)
    else:
        payload["sessions"] = []

    if want_orphans:
        payload["orphans"] = collect_orphans(project)
    else:
        payload["orphans"] = []

    if want_worktrees_direct:
        payload["worktrees_direct"] = collect_worktrees_direct(project, skip_ephemeral=_skip_eph)
        combined_worktrees = payload["worktrees"] + payload["worktrees_direct"]
        payload["worktree_stashes"] = collect_stashes_by_worktree(
            project, combined_worktrees, args.stash_warn_ttl, args.stash_block_ttl
        )
    else:
        payload["worktrees_direct"] = []

    # Stashes extended replaces/augments the base stashes list
    if want_stashes_extended:
        payload["stashes_extended"] = collect_stashes_extended(project, args.stash_warn_ttl, args.stash_block_ttl)
    else:
        payload["stashes_extended"] = []

    if want_claims:
        payload["claims"] = collect_claims(project)
    else:
        payload["claims"] = []

    if getattr(args, "paths", None):
        if not payload.get("worktrees_direct"):
            payload["worktrees_direct"] = collect_worktrees_direct(project, skip_ephemeral=_skip_eph)
            combined_worktrees = payload["worktrees"] + payload["worktrees_direct"]
            payload["worktree_stashes"] = collect_stashes_by_worktree(
                project, combined_worktrees, args.stash_warn_ttl, args.stash_block_ttl
            )
        if not payload.get("stashes_extended"):
            payload["stashes_extended"] = collect_stashes_extended(project, args.stash_warn_ttl, args.stash_block_ttl)
        if not payload.get("claims"):
            payload["claims"] = collect_claims(project)
        payload["path_ownership"] = collect_path_ownership(project, args.paths, payload)
    else:
        payload["path_ownership"] = []

    if want_race_risks:
        sessions_for_risk = payload.get("sessions") or collect_sessions(project)
        worktrees_for_risk = payload.get("worktrees_direct") or collect_worktrees_direct(project, skip_ephemeral=_skip_eph)
        stashes_for_risk = payload.get("stashes_extended") or collect_stashes_extended(
            project, args.stash_warn_ttl, args.stash_block_ttl
        )
        claims_for_risk = payload.get("claims") or collect_claims(project)
        payload["race_risks"] = collect_race_risks(
            sessions_for_risk,
            worktrees_for_risk,
            stashes_for_risk,
            claims_for_risk,
            payload.get("session_fs_stats"),
            args.volume_alarm_threshold,
        )
    else:
        payload["race_risks"] = []

    findings = build_findings(payload, allow_read_only=getattr(args, "allow_read_only", False))
    payload["findings"] = [finding.to_dict() for finding in findings]
    payload["summary"] = {
        "blockers": sum(1 for finding in findings if finding.level == "BLOCK"),
        "warnings": sum(1 for finding in findings if finding.level == "WARN"),
        "preserve_branch_count": len(payload["preserve_branches"]),
        "worktree_count": len(payload["worktrees"]),
        "stash_count": len(payload["stashes"]),
        "worktree_stash_count": sum(group.get("stash_count", 0) for group in payload["worktree_stashes"]),
        "session_count": len(payload["sessions"]),
        "session_fs_artifact_count": payload["session_fs_stats"].get("total_artifact_count", 0),
        "orphan_count": len(payload["orphans"]),
        "claim_count": len(payload["claims"]),
        "race_risk_count": len(payload["race_risks"]),
        "path_ownership_count": len(payload["path_ownership"]),
    }
    return payload


def print_text(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    status = payload["status"]
    print(f"Project: {payload['project']}")
    print(f"Base ref: {payload['base_ref']}")
    print(
        f"Branch: {status.get('branch') or 'detached'} "
        f"head={status.get('head') or '-'} "
        f"upstream={status.get('upstream') or '-'} "
        f"ahead={status.get('ahead')} behind={status.get('behind')}"
    )
    print("Checklist:")
    checks = [
        ("current worktree has no conflicts", status["counts"]["unmerged"] == 0),
        ("current worktree has no uncommitted/untracked WIP", not status["is_dirty"]),
        ("no unpushed commits", status.get("ahead", 0) == 0),
        ("preserve branches have manifests", all(b["manifest_exists"] for b in payload["preserve_branches"])),
        ("preserve branches are integrated/closed", all(b["candidate_delete"] for b in payload["preserve_branches"])),
        ("linked worktrees are clean", all((w.get("is_current_project") or not w.get("dirty")) for w in payload["worktrees"] + payload.get("worktrees_direct", []))),
        ("linked worktrees have no stashes", all((g.get("is_current_project") or not g.get("stash_count")) for g in payload["worktree_stashes"])),
        ("no stashes require review", not payload["stashes"]),
    ]
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'WARN'} {label}")

    # --- P3.3 dimensions output ---
    sessions = payload.get("sessions", [])
    if sessions:
        print(f"\nSessions ({len(sessions)}):")
        for s in sessions:
            alive_str = "alive" if s.get("alive") else "dead"
            age = s.get("age_seconds")
            age_str = f"{age}s" if age is not None else "?"
            task = s.get("current_task") or "-"
            registry = "registered" if s.get("in_active_registry") else "unregistered"
            print(f"  {s['id']} pid={s.get('pid')} [{alive_str}] age={age_str} [{registry}] task={task!r}")

    orphans = payload.get("orphans", [])
    if orphans:
        print(f"\nOrphan commits ({len(orphans)}):")
        for o in orphans[:20]:
            commit = o.get("commit") or o.get("full_hash", "?")[:12]
            subject = o.get("subject") or o.get("message", "?")
            print(f"  {commit} {subject}")
        if len(orphans) > 20:
            print(f"  ... and {len(orphans) - 20} more")

    worktrees_direct = payload.get("worktrees_direct", [])
    if worktrees_direct:
        print(f"\nWorktrees (direct, {len(worktrees_direct)}):")
        for wt in worktrees_direct:
            locked_str = " [locked]" if wt.get("locked") else ""
            prunable_str = " [PRUNABLE]" if wt.get("prunable") else ""
            print(f"  {wt.get('path', '?')} branch={wt.get('branch') or 'detached'}{locked_str}{prunable_str}")

    worktree_stashes = payload.get("worktree_stashes", [])
    if worktree_stashes:
        print(f"\nWorktree stashes ({len(worktree_stashes)} worktree(s) checked):")
        for group in worktree_stashes:
            print(
                f"  {group['worktree_path']} branch={group.get('worktree_branch') or 'detached'} "
                f"stashes={group.get('stash_count', 0)}"
            )

    stashes_extended = payload.get("stashes_extended", [])
    if stashes_extended:
        print(f"\nStashes extended ({len(stashes_extended)}):")
        for s in stashes_extended:
            tag = s.get("provenance_tag", "user")
            print(
                f"  {s['ref']} [{s['level']}] [{tag}] age={s['age_seconds']}s "
                f"branch={s.get('on_branch') or '?'} :: {s['subject']}"
            )

    claims = payload.get("claims", [])
    if claims:
        print(f"\nActive claims ({len(claims)}):")
        for c in claims:
            task_id = c.get("task_id") or c.get("id", "?")
            session = c.get("session_id", "?")
            desc = c.get("description") or c.get("task", "?")
            print(f"  {task_id} session={session} :: {desc}")

    race_risks = payload.get("race_risks", [])
    if race_risks:
        print(f"\nRace risks ({len(race_risks)}):")
        for r in race_risks:
            print(f"  RISK [{r['code']}] {r['description']}")
            for d in r.get("details", []):
                print(f"    {d}")
    elif "race_risks" in payload:
        print("\nRace risks: none detected")

    path_ownership = payload.get("path_ownership", [])
    if path_ownership:
        print(f"\nPath ownership ({len(path_ownership)} path(s)):")
        for item in path_ownership:
            print(f"  {item['status']} {item['path']}")
            if item.get("preserve_branches"):
                print(f"    preserved_on={item['preserve_branches']}")
            for wt in item.get("dirty_worktrees", []):
                activity = wt.get("process_activity") or {}
                print(
                    f"    dirty_worktree={wt.get('path')} branch={wt.get('branch') or 'detached'} "
                    f"processes={activity.get('count', 0)}"
                )
            edit_lock = item.get("edit_lock") or {}
            if edit_lock:
                print(f"    edit_lock={edit_lock.get('state')} :: {edit_lock.get('detail')}")
            if item.get("stashes"):
                print(
                    "    matching_stashes="
                    + str(
                        [
                            {
                                "ref": s.get("ref"),
                                "agent_id": s.get("agent_id"),
                                "heartbeat": s.get("agent_heartbeat"),
                            }
                            for s in item["stashes"]
                        ]
                    )
                )
            if item.get("claims"):
                print(f"    matching_claims={[c.get('task_id') or c.get('id') for c in item['claims']]}")
            print(f"    action: {item['action']}")

    if payload["findings"]:
        print("\nFindings:")
        for finding in payload["findings"]:
            print(f"  {finding['level']} {finding['code']} {finding['subject']} :: {finding['detail']}")
            print(f"    action: {finding['action']}")
    else:
        print("\nFindings: none")

    print(
        "Result: "
        + ("BLOCK" if summary["blockers"] else "WARN" if summary["warnings"] else "PASS")
        + f" ({summary['blockers']} blocker(s), {summary['warnings']} warning(s))"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        default=os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd(),
    )
    parser.add_argument("--branch-pattern", default=DEFAULT_BRANCH_PATTERN)
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument(
        "--stash-warn-ttl",
        type=int,
        default=int(os.environ.get("COS_STASH_LEAK_TTL", DEFAULT_STASH_WARN_TTL)),
    )
    parser.add_argument(
        "--stash-block-ttl",
        type=int,
        default=int(os.environ.get("COS_STASH_LEAK_BLOCK_TTL", DEFAULT_STASH_BLOCK_TTL)),
    )
    parser.add_argument("--volume-alarm-threshold", type=int, default=int(os.environ.get("COS_SESSION_VOLUME_ALARM_THRESHOLD", 1000)))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when warnings or blockers exist.")
    parser.add_argument(
        "--allow-read-only",
        dest="allow_read_only",
        action="store_true",
        default=False,
        help=(
            "Downgrade linked-worktree-dirty from BLOCK to WARN when the "
            "launching agent is structurally read-only (ADR-121). "
            "Ignored when COS_PREFLIGHT_STRICT=1."
        ),
    )

    # P3.3 dimension flags
    parser.add_argument("--sessions", action="store_true", help="Include active session metadata.")
    parser.add_argument("--orphans", action="store_true", help="Include orphan commit scan.")
    parser.add_argument("--worktrees", dest="worktrees_direct", action="store_true", help="Read .git/worktrees/ directly (no git worktree command).")
    parser.add_argument("--stashes", dest="stashes_extended", action="store_true", help="Include extended stash provenance.")
    parser.add_argument("--claims", action="store_true", help="Include active task claims.")
    parser.add_argument("--race-risks", dest="race_risks", action="store_true", help="Run race-condition heuristics.")
    parser.add_argument(
        "--paths",
        nargs="+",
        help="Join WIP ownership/liveness signals for selected paths before cleanup, merge, or closure claims.",
    )
    parser.add_argument("--all", dest="all", action="store_true", help="Enable all P3.3 dimensions.")

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
