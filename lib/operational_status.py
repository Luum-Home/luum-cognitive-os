"""Unified operational status for ADR-123-S4."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

HYGIENE_PATH_PARTS = {
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".coverage",
    ".DS_Store",
}
HYGIENE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".swp"}


def git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)


def _is_hygiene_path(path: str) -> bool:
    normalized = path.strip().strip('"')
    parts = set(Path(normalized).parts)
    if parts & HYGIENE_PATH_PARTS:
        return True
    return any(normalized.endswith(suffix) for suffix in HYGIENE_SUFFIXES)


def git_status(project: Path) -> dict[str, Any]:
    result = git(project, "status", "--porcelain=v2", "--branch", "--untracked-files=all")
    dirty = False
    unmerged = 0
    ahead = 0
    behind = 0
    branch = None
    upstream = None
    changed: list[str] = []
    tracked_changes: list[str] = []
    untracked: list[str] = []
    hygiene: list[str] = []
    blocker_paths: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("# branch.head "):
            branch = line.removeprefix("# branch.head ").strip()
        elif line.startswith("# branch.upstream "):
            upstream = line.removeprefix("# branch.upstream ").strip()
        elif line.startswith("# branch.ab "):
            for part in line.split():
                if part.startswith("+"):
                    ahead = int(part[1:])
                elif part.startswith("-"):
                    behind = int(part[1:])
        elif line.startswith("u "):
            dirty = True
            unmerged += 1
            path = line.rsplit(" ", 1)[-1]
            changed.append(path)
            tracked_changes.append(path)
            blocker_paths.append(path)
        elif line.startswith("1 ") or line.startswith("2 "):
            dirty = True
            path = line.rsplit(" ", 1)[-1]
            changed.append(path)
            tracked_changes.append(path)
            blocker_paths.append(path)
        elif line.startswith("? "):
            dirty = True
            path = line[2:].strip()
            changed.append(path)
            untracked.append(path)
            if _is_hygiene_path(path):
                hygiene.append(path)
            else:
                blocker_paths.append(path)
        elif line and not line.startswith("#"):
            dirty = True
            path = line.rsplit(" ", 1)[-1]
            changed.append(path)
            blocker_paths.append(path)
    return {
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "unmerged": unmerged,
        "changed": sorted(set(changed)),
        "tracked_changes": sorted(set(tracked_changes)),
        "untracked": sorted(set(untracked)),
        "hygiene_paths": sorted(set(hygiene)),
        "blocker_paths": sorted(set(blocker_paths)),
    }


def load_claims(project: Path) -> list[dict[str, Any]]:
    claims_file = project / ".cognitive-os" / "tasks" / "active-claims.json"
    if not claims_file.exists():
        return []
    try:
        data = json.loads(claims_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [{"id": "corrupt-claims", "status": "corrupt", "path": str(claims_file)}]
    rows = data.get("claims", []) if isinstance(data, dict) else []
    return rows if isinstance(rows, list) else []


def validation_capsules(project: Path) -> list[str]:
    roots = [project / ".cognitive-os" / "validation", project / ".cognitive-os" / "validation-capsules"]
    out: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        out.extend(str(path) for path in root.iterdir())
    return sorted(out)


def finding(code: str, *, message: str, severity: str, risk_class: str, primitive: str, paths: list[str] | None = None, repair: str = "none") -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "severity": severity,
        "risk_class": risk_class,
        "owning_primitive": primitive,
        "paths": paths or [],
        "repair": repair,
    }


def decision(name: str, safe: bool, *, reason: str, severity: str, primitive: str, repair: str, risk_class: str) -> dict[str, Any]:
    return {"name": name, "safe": safe, "reason": reason, "severity": severity, "owning_primitive": primitive, "repair": repair, "risk_class": risk_class}


def build_status(project: Path) -> dict[str, Any]:
    project = project.resolve()
    status = git_status(project)
    claims = load_claims(project)
    capsules = validation_capsules(project)
    blocker_paths = status["blocker_paths"]
    hygiene_paths = status["hygiene_paths"]
    main = status["branch"] in {"main", "master"}
    unmerged = status["unmerged"] > 0
    active_claims = [claim for claim in claims if claim.get("status") not in {"released", "completed", "expired"}]

    blockers: list[dict[str, Any]] = []
    hygiene: list[dict[str, Any]] = []
    if unmerged:
        blockers.append(finding("merge-conflicts", message="merge conflicts present", severity="block", risk_class="corruption", primitive="work-inventory", paths=blocker_paths, repair="resolve conflicts before continuing"))
    elif blocker_paths:
        blockers.append(finding("worktree-user-changes", message="tracked or non-hygiene untracked work exists", severity="warn", risk_class="wip-loss", primitive="work-inventory", paths=blocker_paths, repair="commit, stash, or park WIP before launch/push"))
    if hygiene_paths:
        hygiene.append(finding("generated-hygiene-artifacts", message="only generated/cache artifacts detected", severity="info", risk_class="hygiene", primitive="session-hygiene", paths=hygiene_paths, repair="run safe cleanup if desired"))
    if active_claims:
        blockers.append(finding("active-task-claims", message="active task claims exist", severity="warn", risk_class="contention", primitive="task-claim-ledger", repair="inspect scripts/claim_task.py status --include-expired"))
    if capsules:
        blockers.append(finding("active-validation-capsules", message="active validation capsules exist", severity="warn", risk_class="contention", primitive="validation-capsule", paths=capsules, repair="wait for validation or run validation status/cleanup after liveness proof"))
    if main:
        hygiene.append(finding("main-branch", message="current branch is protected/shared", severity="warn", risk_class="protected-branch", primitive="protected-landing", repair="use a session branch and merge queue for landing"))
    if status["ahead"] > 0 and not blocker_paths:
        hygiene.append(finding("branch-ahead", message="branch is ahead of upstream", severity="info", risk_class="hygiene", primitive="git-status", repair="push or merge when ready"))

    safe_to_work = not unmerged
    safe_to_launch = safe_to_work and not blocker_paths and len(active_claims) == 0
    safe_to_validate = safe_to_work and not capsules
    safe_to_push = safe_to_work and not blocker_paths and not main

    decisions = [
        decision(
            "safe_to_work",
            safe_to_work,
            reason="merge conflicts present" if unmerged else "no corruption blockers detected",
            severity="block" if unmerged else "ok",
            primitive="work-inventory",
            repair="resolve conflicts before continuing" if unmerged else "none",
            risk_class="corruption" if unmerged else "hygiene",
        ),
        decision(
            "safe_to_launch_agent",
            safe_to_launch,
            reason="contention or user-change blockers exist" if not safe_to_launch else "no launch blockers; hygiene warnings are advisory",
            severity="warn" if not safe_to_launch else "ok",
            primitive="task-claim-ledger",
            repair="clear active claims or park WIP before launching agents" if not safe_to_launch else "none",
            risk_class="contention" if active_claims else "wip-loss" if blocker_paths else "hygiene",
        ),
        decision(
            "safe_to_validate",
            safe_to_validate,
            reason="active validation capsules exist" if capsules else "validation safe; hygiene warnings are advisory",
            severity="warn" if capsules else "ok",
            primitive="validation-capsule",
            repair="wait for validation or run validation status/cleanup after liveness proof" if capsules else "none",
            risk_class="contention" if capsules else "hygiene",
        ),
        decision(
            "safe_to_push",
            safe_to_push,
            reason="main/master must land through protected path" if main else "user-change blockers exist" if blocker_paths else "feature branch push allowed by status",
            severity="block" if main else "warn" if blocker_paths else "ok",
            primitive="protected-landing",
            repair="use merge queue/protected landing path" if main else "commit or park WIP before push" if blocker_paths else "none",
            risk_class="main-corruption" if main else "wip-loss" if blocker_paths else "hygiene",
        ),
    ]
    return {
        "schema_version": "operational-status.v1",
        "project": str(project),
        "git": status,
        "active_claim_count": len(active_claims),
        "validation_capsules": capsules,
        "risk_summary": {"blockers": len(blockers), "hygiene_warnings": len(hygiene)},
        "blockers": blockers,
        "hygiene_warnings": hygiene,
        "decisions": decisions,
    }
