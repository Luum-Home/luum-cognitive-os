#!/usr/bin/env python3
# SCOPE: both
"""Task-claim ledger for cross-session pending-task coordination.

Stores advisory claims in .cognitive-os/tasks/active-claims.json and emits
append-only session events in .cognitive-os/sessions/events.jsonl.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


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
    claimed_epoch = parse_iso_epoch(claim.get("claimed_at"))
    if claimed_epoch is None:
        return False
    return now_epoch - claimed_epoch > claim_ttl_seconds()


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


def claim_task(project: Path, task: dict[str, Any], session: str | None = None, expected_files: Sequence[str] | None = None) -> tuple[bool, dict[str, Any]]:
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
                payload = {"task_id": task_id, "fingerprint": fingerprint, "held_by": existing.get("session_id"), "expected_files": expected}
                append_event(project, "conflict", session, payload)
                atomic_write_json(path, data)
                return False, {"status": "conflict", **payload}
        claim = {
            "task_id": task_id,
            "session_id": session,
            "claimed_at": now_iso(),
            "expected_files": expected,
            "fingerprint": fingerprint,
            "status": "active",
        }
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


def cmd_claim(args: argparse.Namespace) -> int:
    project = project_dir(args)
    task = read_json(Path(args.task_json), {}) if args.task_json else {"id": args.task_id, "description": args.description or "", "deliverable": args.deliverable or ""}
    ok, result = claim_task(project, task, args.session_id, args.expected_file)
    print(json.dumps(result, sort_keys=True))
    return 0 if ok else 2


def cmd_complete(args: argparse.Namespace) -> int:
    print(json.dumps(complete_task(project_dir(args), args.task_id, args.session_id), sort_keys=True))
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
    claim.set_defaults(func=cmd_claim)
    complete = sub.add_parser("complete")
    complete.add_argument("--task-id", required=True)
    complete.add_argument("--session-id")
    complete.set_defaults(func=cmd_complete)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
