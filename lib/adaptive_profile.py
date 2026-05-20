"""Adaptive risk profile resolver for ADR-123-S2."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASELINE_PROTECTIONS: tuple[dict[str, str], ...] = (
    {
        "risk": "secrets",
        "hook": "secret-detector",
        "reason": "credential leaks are never low-risk, even in lean profile",
    },
    {
        "risk": "destructive_git",
        "hook": "destructive-git-blocker",
        "reason": "destructive git can lose work or corrupt branch state",
    },
    {
        "risk": "destructive_rm",
        "hook": "destructive-rm-blocker",
        "reason": "recursive deletion can lose uncommitted work",
    },
    {
        "risk": "untracked_work_loss",
        "hook": "untracked-work-preservation-guard",
        "reason": "untracked files are operator work until proven disposable",
    },
)


_HIGH_RISK_SURFACE_PREFIXES: dict[str, tuple[str, ...]] = {
    "hooks": ("hooks/",),
    "scripts": ("scripts/",),
    "registry": ("manifests/", ".cognitive-os/", ".claude/", ".codex/"),
    "config": ("cognitive-os.yaml", "pyproject.toml", "Makefile"),
    "adrs": ("docs/02-Decisions/adrs/",),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_jsonl_append(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        pass


def high_risk_surfaces(files: list[str]) -> list[str]:
    """Return changed high-risk surfaces that justify strict profile."""
    surfaces: set[str] = set()
    for rel in files:
        for surface, prefixes in _HIGH_RISK_SURFACE_PREFIXES.items():
            if any(rel == prefix or rel.startswith(prefix) for prefix in prefixes):
                surfaces.add(surface)
    return sorted(surfaces)

_PROFILE_POLICIES: dict[str, dict[str, Any]] = {
    "lean": {
        "semantics": "low-friction profile for clean, low-risk feature work",
        "blocking_posture": "baseline-safety-only",
        "minimum_protections": list(_BASELINE_PROTECTIONS),
        "advisory_bias": "hygiene and process guards should observe/warn, not block",
    },
    "standard": {
        "semantics": "normal implementation profile for dirty worktrees or moderate coordination risk",
        "blocking_posture": "baseline-plus-coordination",
        "minimum_protections": list(_BASELINE_PROTECTIONS),
        "advisory_bias": "coordination and generated-state drift can warn or block by maturity metadata",
    },
    "strict": {
        "semantics": "landing, main-branch, validation, or multi-agent contention profile",
        "blocking_posture": "release-and-state-integrity",
        "minimum_protections": list(_BASELINE_PROTECTIONS),
        "advisory_bias": "contract, landing, runtime-state, and generated-artifact guards may block",
    },
}


def git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)


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




def active_resource_lease_count(project: Path) -> int:
    root = project / ".cognitive-os" / "runtime" / "resource-leases"
    if not root.exists():
        return 0
    now = time.time()
    count = 0
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            count += 1
            continue
        expires_at = data.get("expires_at") if isinstance(data, dict) else None
        if isinstance(expires_at, (int, float)) and now >= float(expires_at):
            continue
        count += 1
    return count


def stash_count(project: Path) -> int:
    result = git(project, "stash", "list")
    if result.returncode != 0:
        return 0
    return sum(1 for line in result.stdout.splitlines() if line.strip())


def pre_agent_marker_count(project: Path) -> int:
    roots = (
        project / ".cognitive-os" / "pre-agent-markers",
        project / ".cognitive-os" / "runtime" / "pre-agent-markers",
    )
    count = 0
    for root in roots:
        if root.exists():
            count += sum(1 for item in root.iterdir() if item.is_file())
    return count


def log_override(project: Path, payload: dict[str, Any]) -> None:
    _safe_jsonl_append(
        project / ".cognitive-os" / "metrics" / "adaptive-profile-overrides.jsonl",
        payload,
    )

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


def profile_policy(profile: str) -> dict[str, Any]:
    """Return executable semantics for an adaptive profile.

    Lean is intentionally not a bypass. It lowers hygiene/process friction, but
    it keeps the baseline protections that prevent secret leaks and destructive
    work loss.
    """
    return _PROFILE_POLICIES.get(profile, _PROFILE_POLICIES["standard"])


def resolve_profile(
    project: Path,
    *,
    landing_intent: bool = False,
    override: str | None = None,
    override_ttl_seconds: int | None = None,
) -> dict[str, Any]:
    project = project.resolve()
    signals = git_signals(project)
    claims = active_claim_count(project)
    leases = active_resource_lease_count(project)
    stashes = stash_count(project)
    markers = pre_agent_marker_count(project)
    wt_count = worktree_count(project)
    validation = validation_active(project)
    risky_surfaces = high_risk_surfaces(signals["files"])
    base_signals = {
        **signals,
        "active_claims": claims,
        "active_resource_leases": leases,
        "stash_count": stashes,
        "pre_agent_marker_count": markers,
        "worktree_count": wt_count,
        "validation_active": validation,
        "landing_intent": landing_intent,
        "high_risk_surfaces": risky_surfaces,
    }
    reasons: list[str] = []

    if override:
        expires_at = time.time() + override_ttl_seconds if override_ttl_seconds else None
        payload = {
            "ts": _now_iso(),
            "project_dir": str(project),
            "profile": override,
            "expires_at": expires_at,
            "signals": base_signals,
        }
        log_override(project, payload)
        return {
            "schema_version": "adaptive-profile.v1",
            "profile": override,
            "override": True,
            "override_scope": str(project),
            "override_expires_at": expires_at,
            "reasons": ["operator override"],
            "signals": base_signals,
            "guard_policy": profile_policy(override),
        }

    profile = "lean"
    if signals["dirty"] or stashes or signals["branch"] in {"main", "master"}:
        profile = "standard"
    if (
        landing_intent
        or signals["branch"] in {"main", "master"}
        or claims
        or leases
        or markers
        or wt_count > 1
        or validation
        or risky_surfaces
    ):
        profile = "strict"

    if signals["dirty"]:
        reasons.append("dirty worktree")
    if risky_surfaces:
        reasons.append("high-risk changed surfaces=" + ",".join(risky_surfaces))
    if signals["branch"] in {"main", "master"}:
        reasons.append("main/master branch")
    if claims:
        reasons.append(f"active claims={claims}")
    if leases:
        reasons.append(f"active resource leases={leases}")
    if stashes:
        reasons.append(f"stashes={stashes}")
    if markers:
        reasons.append(f"pre-agent markers={markers}")
    if wt_count > 1:
        reasons.append(f"worktrees={wt_count}")
    if validation:
        reasons.append("active validation capsule")
    if landing_intent:
        reasons.append("landing intent")
    if not reasons:
        reasons.append("clean low-risk feature work")

    return {
        "schema_version": "adaptive-profile.v1",
        "profile": profile,
        "override": False,
        "reasons": reasons,
        "signals": base_signals,
        "guard_policy": profile_policy(profile),
    }
