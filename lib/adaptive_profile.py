"""Adaptive risk profile resolver for ADR-123-S2."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def git_signals(project: Path) -> dict[str, Any]:
    branch = git(project, "branch", "--show-current").stdout.strip() or "detached"
    status = git(project, "status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines()
    staged = sum(1 for line in status if line[:1].strip())
    unstaged = sum(1 for line in status if line[1:2].strip())
    untracked = sum(1 for line in status if line.startswith("??"))
    files = [line[3:] if not line.startswith("??") else line[3:] for line in status]
    return {"branch": branch, "dirty": bool(status), "staged": staged, "unstaged": unstaged, "untracked": untracked, "files": sorted(set(files))}


def active_claim_count(project: Path) -> int:
    path = project / ".cognitive-os" / "tasks" / "active-claims.json"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 1
    claims = data.get("claims", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    return sum(1 for claim in claims if claim.get("status") not in {"released", "completed", "expired"})


def worktree_count(project: Path) -> int:
    result = git(project, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        return 1
    return max(1, sum(1 for line in result.stdout.splitlines() if line.startswith("worktree ")))


def validation_active(project: Path) -> bool:
    for root in (project / ".cognitive-os" / "validation", project / ".cognitive-os" / "validation-capsules"):
        if root.exists() and any(root.iterdir()):
            return True
    return False


def resolve_profile(project: Path, *, landing_intent: bool = False, override: str | None = None) -> dict[str, Any]:
    project = project.resolve()
    signals = git_signals(project)
    claims = active_claim_count(project)
    wt_count = worktree_count(project)
    validation = validation_active(project)
    reasons: list[str] = []

    if override:
        return {"schema_version": "adaptive-profile.v1", "profile": override, "override": True, "reasons": ["operator override"], "signals": {**signals, "active_claims": claims, "worktree_count": wt_count, "validation_active": validation, "landing_intent": landing_intent}}

    profile = "lean"
    if signals["dirty"] or signals["branch"] in {"main", "master"} or claims or wt_count > 1:
        profile = "standard"
    if landing_intent or signals["branch"] in {"main", "master"} or claims or wt_count > 1 or validation:
        profile = "strict"

    if signals["dirty"]:
        reasons.append("dirty worktree")
    if signals["branch"] in {"main", "master"}:
        reasons.append("main/master branch")
    if claims:
        reasons.append(f"active claims={claims}")
    if wt_count > 1:
        reasons.append(f"worktrees={wt_count}")
    if validation:
        reasons.append("active validation capsule")
    if landing_intent:
        reasons.append("landing intent")
    if not reasons:
        reasons.append("clean low-risk feature work")

    return {"schema_version": "adaptive-profile.v1", "profile": profile, "override": False, "reasons": reasons, "signals": {**signals, "active_claims": claims, "worktree_count": wt_count, "validation_active": validation, "landing_intent": landing_intent}}
