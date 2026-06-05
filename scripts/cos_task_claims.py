#!/usr/bin/env python3
# SCOPE: both
"""Task-claim ledger for cross-session pending-task coordination.

Stores advisory claims in .cognitive-os/tasks/active-claims.json and emits
append-only session events in .cognitive-os/sessions/events.jsonl.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import read_json_or as read_json

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.time_utils import now_iso as now_iso


def project_dir(args: argparse.Namespace | None = None) -> Path:
    value = None if args is None else getattr(args, "project_dir", None)
    value = value or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).resolve()


def tasks_dir(project: Path) -> Path:
    return project / ".cognitive-os" / "tasks"


def sessions_dir(project: Path) -> Path:
    return project / ".cognitive-os" / "sessions"


def claims_path(project: Path) -> Path:
    return tasks_dir(project) / "active-claims.json"


def events_path(project: Path) -> Path:
    return sessions_dir(project) / "events.jsonl"


def active_sessions_path(project: Path) -> Path:
    return sessions_dir(project) / "active-sessions.json"


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def pid_alive(pid: Any) -> bool:
    try:
        parsed = int(pid)
    except Exception:
        return False
    if parsed <= 0:
        return False
    try:
        os.kill(parsed, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def claim_ttl_seconds() -> int:
    try:
        return max(60, int(os.environ.get("COS_TASK_CLAIM_TTL_SECONDS", "14400")))
    except ValueError:
        return 14400


def parse_iso_epoch(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def active_session_liveness(project: Path) -> dict[str, bool]:
    data = read_json(active_sessions_path(project), {"sessions": []})
    sessions = data.get("sessions", []) if isinstance(data, dict) else []
    liveness: dict[str, bool] = {}
    for session in sessions:
        if not isinstance(session, dict):
            continue
        sid = str(session.get("id") or session.get("session_id") or "")
        if not sid:
            continue
        alive = pid_alive(session.get("pid"))
        liveness[sid] = liveness.get(sid, False) or alive
    return liveness


def task_fingerprint(task: dict[str, Any], expected_files: Sequence[str] | None = None) -> str:
    parts = {
        "title": task.get("title") or task.get("name") or "",
        "description": task.get("description") or task.get("task") or task.get("prompt") or "",
        "deliverable": task.get("deliverable") or task.get("expected_output") or task.get("expected_outputs") or "",
        "verify": task.get("verify") or task.get("acceptance_criteria") or task.get("success_criteria") or "",
        "expected_files": sorted(expected_files or extract_expected_files(task)),
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]


def extract_expected_files(task: dict[str, Any]) -> list[str]:
    for key in ("expected_files", "files", "target_files"):
        value = task.get(key)
        if isinstance(value, list):
            return sorted(str(item) for item in value if str(item).strip())
    deliverable = task.get("deliverable") or task.get("expected_output") or ""
    if isinstance(deliverable, str):
        candidates = []
        for token in deliverable.replace("`", " ").replace(",", " ").split():
            cleaned = token.strip(" .;:()[]{}")
            if "/" in cleaned or cleaned.endswith((".py", ".sh", ".md", ".json", ".yaml", ".yml", ".toml")):
                candidates.append(cleaned)
        return sorted(set(candidates))
    return []


def session_id(default: str = "unknown") -> str:
    return os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or default


def append_event(project: Path, event: str, session: str, payload: dict[str, Any]) -> None:
    path = events_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": now_iso(), "session": session, "event": event, "payload": payload}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def normalize_claims(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("claims"), list):
        return data
    return {"claims": []}


def claim_is_stale(claim: dict[str, Any], liveness: dict[str, bool], now_epoch: float) -> bool:
    sid = str(claim.get("session_id") or "")
    if sid in liveness:
        return not liveness[sid]
    expires_at = claim.get("expires_at")
    if isinstance(expires_at, (int, float)):
        return float(expires_at) <= now_epoch
    if isinstance(expires_at, str):
        expires_epoch = parse_iso_epoch(expires_at)
        if expires_epoch is not None:
            return expires_epoch <= now_epoch
    claimed_epoch = parse_iso_epoch(claim.get("claimed_at"))
    if claimed_epoch is None:
        return False
    ttl = claim.get("ttl_seconds")
    try:
        ttl_seconds = int(ttl)
    except (TypeError, ValueError):
        ttl_seconds = claim_ttl_seconds()
    return now_epoch - claimed_epoch > max(1, ttl_seconds)


def prune_claims(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    liveness = active_session_liveness(project)
    now_epoch = datetime.now(timezone.utc).timestamp()
    claims = []
    for claim in data.get("claims", []):
        if not isinstance(claim, dict):
            continue
        status = claim.get("status", "active")
        if status == "active" and claim_is_stale(claim, liveness, now_epoch):
            claim = {**claim, "status": "stale", "stale_at": now_iso()}
        claims.append(claim)
    return {**data, "claims": claims, "updated_at": now_iso()}


def claim_task(
    project: Path,
    task: dict[str, Any],
    session: str | None = None,
    expected_files: Sequence[str] | None = None,
    *,
    agent_id: str | None = None,
    scope: str | None = None,
    ttl_seconds: int | None = None,
    pid: int | None = None,
    host: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    import socket as _socket
    import time as _time

    session = session or session_id()
    task_id = str(task.get("id") or task.get("task_id") or task.get("toolUseId") or "unknown")
    fingerprint = task_fingerprint(task, expected_files)
    expected = sorted(expected_files or extract_expected_files(task))
    path = claims_path(project)
    lock = path.parent / ".active-claims.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        data = prune_claims(project, normalize_claims(read_json(path, {"claims": []})))
        for existing in data["claims"]:
            if existing.get("status", "active") != "active":
                continue
            same_work = existing.get("fingerprint") == fingerprint or existing.get("task_id") == task_id
            if same_work and existing.get("session_id") != session:
                payload = {
                    "task_id": task_id,
                    "fingerprint": fingerprint,
                    "held_by": existing.get("session_id"),
                    "held_by_task_id": existing.get("task_id"),
                    "expected_files": expected,
                }
                append_event(project, "conflict", session, payload)
                atomic_write_json(path, data)
                return False, {"status": "conflict", **payload}
        ttl = ttl_seconds if ttl_seconds and ttl_seconds > 0 else claim_ttl_seconds()
        now_epoch = _time.time()
        claim: dict[str, Any] = {
            "task_id": task_id,
            "session_id": session,
            "claimed_at": now_iso(),
            "expected_files": expected,
            "fingerprint": fingerprint,
            "status": "active",
            # Extended fields for TCL-compatible consumers
            "expires_at": now_epoch + ttl,
            "ttl_seconds": ttl,
            "pid": pid if pid is not None else os.getpid(),
            "host": host or _socket.gethostname(),
        }
        if agent_id is not None:
            claim["agent_id"] = agent_id
        if scope is not None:
            claim["scope"] = scope
        data["claims"] = [c for c in data["claims"] if not (c.get("task_id") == task_id and c.get("session_id") == session and c.get("status") == "active")]
        data["claims"].append(claim)
        atomic_write_json(path, data)
        append_event(project, "claim", session, claim)
        return True, {"status": "claimed", **claim}


def complete_task(project: Path, task_id: str, session: str | None = None) -> dict[str, Any]:
    session = session or session_id()
    path = claims_path(project)
    lock = path.parent / ".active-claims.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        data = normalize_claims(read_json(path, {"claims": []}))
        updated = False
        for claim in data["claims"]:
            if claim.get("task_id") == task_id and (claim.get("session_id") == session or session == "*") and claim.get("status") == "active":
                claim["status"] = "completed"
                claim["completed_at"] = now_iso()
                updated = True
        data["updated_at"] = now_iso()
        atomic_write_json(path, data)
    payload = {"task_id": task_id, "updated": updated}
    append_event(project, "complete", session, payload)
    return payload


def release_task(project: Path, task_id: str, session: str | None = None) -> dict[str, Any]:
    """Release an active claim without marking the task completed."""
    session = session or session_id()
    path = claims_path(project)
    lock = path.parent / ".active-claims.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        data = normalize_claims(read_json(path, {"claims": []}))
        updated = False
        for claim in data["claims"]:
            if (
                claim.get("task_id") == task_id
                and (claim.get("session_id") == session or session == "*")
                and claim.get("status") == "active"
            ):
                claim["status"] = "released"
                claim["released_at"] = now_iso()
                updated = True
        data["updated_at"] = now_iso()
        atomic_write_json(path, data)
    payload = {"task_id": task_id, "updated": updated}
    append_event(project, "release", session, payload)
    return payload


def list_claims(project: Path, *, include_stale: bool = False) -> list[dict[str, Any]]:
    """Return claims from the canonical store.

    By default only active claims are returned.  Pass ``include_stale=True``
    to include stale/completed/released entries as well.
    """
    data = prune_claims(project, normalize_claims(read_json(claims_path(project), {"claims": []})))
    all_claims = [c for c in data.get("claims", []) if isinstance(c, dict)]
    if include_stale:
        return sorted(all_claims, key=lambda c: str(c.get("task_id", "")))
    return sorted(
        (c for c in all_claims if c.get("status") == "active"),
        key=lambda c: str(c.get("task_id", "")),
    )



def git_ref_has_path(project: Path, ref: str, rel_path: str) -> bool:
    if not rel_path or rel_path.startswith("/") or ".." in Path(rel_path).parts:
        return False
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{rel_path}"],
        cwd=str(project),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    return proc.returncode == 0


def watermark_landed_claims(project: Path, ref: str = "main", session: str | None = None) -> dict[str, Any]:
    """Mark active claims completed when all declared outputs already exist in ref.

    This is a recovery primitive for duplicate multi-session work: if another
    session landed the declared outputs in main, the local pending claim is
    completed by watermark instead of deleting evidence from the ledger.
    """
    session = session or session_id("watermark")
    path = claims_path(project)
    lock = path.parent / ".active-claims.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    marked: list[dict[str, Any]] = []
    with lock.open("w", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        data = normalize_claims(read_json(path, {"claims": []}))
        for claim in data.get("claims", []):
            if not isinstance(claim, dict) or claim.get("status", "active") != "active":
                continue
            expected = [str(p) for p in (claim.get("expected_files") or []) if str(p).strip()]
            if not expected:
                continue
            matched = [p for p in expected if git_ref_has_path(project, ref, p)]
            if len(matched) != len(expected):
                continue
            claim["status"] = "completed-by-watermark"
            claim["completed_at"] = now_iso()
            claim["watermark_evidence"] = {"mode": "landed-ref", "ref": ref, "matched_paths": matched}
            marked.append({"task_id": claim.get("task_id"), "session_id": claim.get("session_id"), "expected_files": matched})
        data["updated_at"] = now_iso()
        atomic_write_json(path, data)
    for row in marked:
        append_event(project, "complete", session, {**row, "watermark": True, "ref": ref})
    return {"marked": marked, "count": len(marked), "ref": ref}

def cmd_claim(args: argparse.Namespace) -> int:
    project = project_dir(args)
    task = read_json(Path(args.task_json), {}) if args.task_json else {"id": args.task_id, "description": args.description or "", "deliverable": args.deliverable or ""}
    ok, result = claim_task(
        project,
        task,
        args.session_id,
        args.expected_file,
        agent_id=getattr(args, "agent_id", None),
        scope=getattr(args, "scope", None),
        ttl_seconds=getattr(args, "ttl_seconds", None),
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if ok else 2


def cmd_complete(args: argparse.Namespace) -> int:
    print(json.dumps(complete_task(project_dir(args), args.task_id, args.session_id), sort_keys=True))
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    print(json.dumps(release_task(project_dir(args), args.task_id, args.session_id), sort_keys=True))
    return 0


def cmd_watermark(args: argparse.Namespace) -> int:
    print(json.dumps(watermark_landed_claims(project_dir(args), args.ref, args.session_id), sort_keys=True))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project = project_dir(args)
    data = prune_claims(project, normalize_claims(read_json(claims_path(project), {"claims": []})))
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        active = [c for c in data.get("claims", []) if c.get("status") == "active"]
        print(f"Task claims: {len(active)} active / {len(data.get('claims', []))} total")
        for claim in active:
            print(f"- {claim.get('task_id')} session={claim.get('session_id')} files={','.join(claim.get('expected_files') or []) or '-'}")
    if data != normalize_claims(read_json(claims_path(project), {"claims": []})):
        atomic_write_json(claims_path(project), data)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir")
    sub = parser.add_subparsers(dest="command", required=True)
    claim = sub.add_parser("claim")
    claim.add_argument("--task-json")
    claim.add_argument("--task-id", default="unknown")
    claim.add_argument("--description")
    claim.add_argument("--deliverable")
    claim.add_argument("--expected-file", action="append")
    claim.add_argument("--session-id")
    claim.add_argument("--agent-id", dest="agent_id", default=None)
    claim.add_argument("--scope", default=None)
    claim.add_argument("--ttl-seconds", dest="ttl_seconds", type=int, default=None)
    claim.set_defaults(func=cmd_claim)
    complete = sub.add_parser("complete")
    complete.add_argument("--task-id", required=True)
    complete.add_argument("--session-id")
    complete.set_defaults(func=cmd_complete)
    release = sub.add_parser("release")
    release.add_argument("--task-id", required=True)
    release.add_argument("--session-id")
    release.set_defaults(func=cmd_release)
    watermark = sub.add_parser("watermark")
    watermark.add_argument("--ref", default="main")
    watermark.add_argument("--session-id")
    watermark.set_defaults(func=cmd_watermark)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
