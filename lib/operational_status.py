"""Unified operational status for ADR-123-S4."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)


def git_status(project: Path) -> dict[str, Any]:
    result = git(project, "status", "--porcelain=v2", "--branch", "--untracked-files=all")
    dirty = False
    unmerged = 0
    ahead = 0
    behind = 0
    branch = None
    upstream = None
    changed: list[str] = []
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
            changed.append(line.rsplit(" ", 1)[-1])
        elif line and not line.startswith("#"):
            dirty = True
            changed.append(line.rsplit(" ", 1)[-1])
    return {"branch": branch, "upstream": upstream, "ahead": ahead, "behind": behind, "dirty": dirty, "unmerged": unmerged, "changed": sorted(set(changed))}


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


def decision(name: str, safe: bool, *, reason: str, severity: str, primitive: str, repair: str, risk_class: str) -> dict[str, Any]:
    return {"name": name, "safe": safe, "reason": reason, "severity": severity, "owning_primitive": primitive, "repair": repair, "risk_class": risk_class}


def build_status(project: Path) -> dict[str, Any]:
    project = project.resolve()
    status = git_status(project)
    claims = load_claims(project)
    capsules = validation_capsules(project)
    dirty = status["dirty"]
    main = status["branch"] in {"main", "master"}
    unmerged = status["unmerged"] > 0
    active_claims = [claim for claim in claims if claim.get("status") not in {"released", "completed", "expired"}]

    safe_to_work = not unmerged
    safe_to_launch = safe_to_work and len(active_claims) == 0
    safe_to_validate = safe_to_work and not capsules
    safe_to_push = safe_to_work and not dirty and status["ahead"] >= 0 and not main

    decisions = [
        decision(
            "safe_to_work",
            safe_to_work,
            reason="merge conflicts present" if unmerged else "no unmerged paths detected",
            severity="block" if unmerged else "ok",
            primitive="work-inventory",
            repair="resolve conflicts before continuing" if unmerged else "none",
            risk_class="corruption" if unmerged else "hygiene",
        ),
        decision(
            "safe_to_launch_agent",
            safe_to_launch,
            reason="active task claims exist" if active_claims else "no active task claims block launch",
            severity="warn" if active_claims else "ok",
            primitive="task-claim-ledger",
            repair="inspect scripts/claim_task.py status --include-expired" if active_claims else "none",
            risk_class="contention" if active_claims else "hygiene",
        ),
        decision(
            "safe_to_validate",
            safe_to_validate,
            reason="active validation capsules exist" if capsules else "no active validation capsules detected",
            severity="warn" if capsules else "ok",
            primitive="validation-capsule",
            repair="wait for validation or run validation status/cleanup after liveness proof" if capsules else "none",
            risk_class="contention" if capsules else "hygiene",
        ),
        decision(
            "safe_to_push",
            safe_to_push,
            reason="main/master must land through protected path" if main else "dirty worktree" if dirty else "feature branch push allowed by status",
            severity="block" if main else "warn" if dirty else "ok",
            primitive="protected-landing",
            repair="use merge queue/protected landing path" if main else "commit or park WIP before push" if dirty else "none",
            risk_class="main-corruption" if main else "wip-loss" if dirty else "hygiene",
        ),
    ]
    return {"schema_version": "operational-status.v1", "project": str(project), "git": status, "active_claim_count": len(active_claims), "validation_capsules": capsules, "decisions": decisions}
