#!/usr/bin/env python3
# SCOPE: os-only
"""Branch writer lease primitive for same-branch multi-agent safety.

ADR-116 protects main/master with a merge queue, but multiple agents can still
collide on any shared branch. This script provides a small file-backed lease so
an agent/session can claim write ownership for a branch before mutating it.

State path: .cognitive-os/runtime/branch-writer-leases.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VALID_ACTIONS = {"acquire", "release", "status", "check"}
DEFAULT_TTL_SECONDS = 4 * 60 * 60
STATE_RELATIVE_PATH = Path(".cognitive-os/runtime/branch-writer-leases.json")


@dataclass(frozen=True)
class Lease:
    branch: str
    owner: str
    session_id: str
    acquired_at: float
    expires_at: float
    worktree: str | None = None
    task_id: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Lease":
        return cls(
            branch=str(raw["branch"]),
            owner=str(raw["owner"]),
            session_id=str(raw["session_id"]),
            acquired_at=float(raw["acquired_at"]),
            expires_at=float(raw["expires_at"]),
            worktree=raw.get("worktree"),
            task_id=raw.get("task_id"),
        )

    def expired(self, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) >= self.expires_at


def state_path(project_dir: Path) -> Path:
    return project_dir / STATE_RELATIVE_PATH


def normalize_branch(branch: str) -> str:
    normalized = branch.strip()
    if normalized.startswith("refs/heads/"):
        normalized = normalized.removeprefix("refs/heads/")
    if not normalized:
        raise ValueError("branch must not be empty")
    if ".." in normalized or normalized.startswith("/") or normalized.endswith("/"):
        raise ValueError(f"unsafe branch name: {branch!r}")
    return normalized


def load_state(path: Path) -> dict[str, Lease]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"branch lease state is malformed: {path}: {exc}") from exc
    leases = raw.get("leases", raw)
    if not isinstance(leases, dict):
        raise RuntimeError(f"branch lease state has invalid shape: {path}")
    return {branch: Lease.from_dict(value) for branch, value in leases.items()}


def save_state(path: Path, leases: dict[str, Lease]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"leases": {branch: asdict(lease) for branch, lease in sorted(leases.items())}}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def prune_expired(leases: dict[str, Lease], now: float | None = None) -> dict[str, Lease]:
    current = now if now is not None else time.time()
    return {branch: lease for branch, lease in leases.items() if not lease.expired(current)}


def same_owner(lease: Lease, owner: str, session_id: str) -> bool:
    return lease.owner == owner and lease.session_id == session_id


def acquire(
    project_dir: Path,
    *,
    branch: str,
    owner: str,
    session_id: str,
    ttl_seconds: int,
    worktree: str | None,
    task_id: str | None,
    now: float | None = None,
) -> dict[str, Any]:
    branch = normalize_branch(branch)
    current_time = now if now is not None else time.time()
    path = state_path(project_dir)
    leases = prune_expired(load_state(path), current_time)
    existing = leases.get(branch)
    if existing and not same_owner(existing, owner, session_id):
        save_state(path, leases)
        return {
            "ok": False,
            "action": "acquire",
            "status": "blocked",
            "branch": branch,
            "reason": "branch already has an active writer lease",
            "lease": asdict(existing),
        }
    lease = Lease(
        branch=branch,
        owner=owner,
        session_id=session_id,
        acquired_at=current_time if existing is None else existing.acquired_at,
        expires_at=current_time + ttl_seconds,
        worktree=worktree,
        task_id=task_id,
    )
    leases[branch] = lease
    save_state(path, leases)
    return {"ok": True, "action": "acquire", "status": "acquired", "branch": branch, "lease": asdict(lease)}


def release(project_dir: Path, *, branch: str, owner: str, session_id: str) -> dict[str, Any]:
    branch = normalize_branch(branch)
    path = state_path(project_dir)
    leases = prune_expired(load_state(path))
    existing = leases.get(branch)
    if existing is None:
        save_state(path, leases)
        return {"ok": True, "action": "release", "status": "absent", "branch": branch}
    if not same_owner(existing, owner, session_id):
        save_state(path, leases)
        return {
            "ok": False,
            "action": "release",
            "status": "blocked",
            "branch": branch,
            "reason": "only the lease owner can release this branch lease",
            "lease": asdict(existing),
        }
    del leases[branch]
    save_state(path, leases)
    return {"ok": True, "action": "release", "status": "released", "branch": branch}


def status(project_dir: Path, *, branch: str | None = None) -> dict[str, Any]:
    path = state_path(project_dir)
    leases = prune_expired(load_state(path))
    save_state(path, leases)
    if branch:
        normalized = normalize_branch(branch)
        lease = leases.get(normalized)
        return {
            "ok": True,
            "action": "status",
            "branch": normalized,
            "leased": lease is not None,
            "lease": asdict(lease) if lease else None,
        }
    return {
        "ok": True,
        "action": "status",
        "leases": {name: asdict(lease) for name, lease in sorted(leases.items())},
    }


def check(project_dir: Path, *, branch: str, owner: str, session_id: str) -> dict[str, Any]:
    branch = normalize_branch(branch)
    path = state_path(project_dir)
    leases = prune_expired(load_state(path))
    existing = leases.get(branch)
    save_state(path, leases)
    if existing is None or same_owner(existing, owner, session_id):
        return {"ok": True, "action": "check", "status": "allowed", "branch": branch, "lease": asdict(existing) if existing else None}
    return {
        "ok": False,
        "action": "check",
        "status": "blocked",
        "branch": branch,
        "reason": "branch is leased by another writer",
        "lease": asdict(existing),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire/check/release branch writer leases")
    parser.add_argument("action", choices=sorted(VALID_ACTIONS))
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--branch")
    parser.add_argument("--owner", default=os.environ.get("COS_AGENT_ID") or os.environ.get("USER") or "unknown")
    parser.add_argument("--session-id", default=os.environ.get("COS_SESSION_ID") or "default-session")
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    parser.add_argument("--worktree")
    parser.add_argument("--task-id")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    try:
        if args.action == "acquire":
            if not args.branch:
                raise ValueError("--branch is required for acquire")
            result = acquire(
                project_dir,
                branch=args.branch,
                owner=args.owner,
                session_id=args.session_id,
                ttl_seconds=args.ttl_seconds,
                worktree=args.worktree,
                task_id=args.task_id,
            )
        elif args.action == "release":
            if not args.branch:
                raise ValueError("--branch is required for release")
            result = release(project_dir, branch=args.branch, owner=args.owner, session_id=args.session_id)
        elif args.action == "check":
            if not args.branch:
                raise ValueError("--branch is required for check")
            result = check(project_dir, branch=args.branch, owner=args.owner, session_id=args.session_id)
        else:
            result = status(project_dir, branch=args.branch)
    except Exception as exc:  # noqa: BLE001 - CLI should return structured errors.
        result = {"ok": False, "action": args.action, "status": "error", "error": str(exc)}

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result.get("ok"):
            print(f"branch-lease: {result.get('status', 'ok')} {result.get('branch', '')}".rstrip())
        else:
            print(f"branch-lease: BLOCK — {result.get('reason') or result.get('error')}", file=sys.stderr)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
