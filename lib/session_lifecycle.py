"""Filesystem session lifecycle reaper.

Read/inspect session directories before archiving or deleting them. This module
complements the process-registry reaper: it acts on filesystem artifacts under
.cognitive-os/sessions and .cognitive-os/archive/sessions, never on live PIDs.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

DecisionCode = Literal[
    "KEEP_ACTIVE",
    "KEEP_PENDING_CONTENT",
    "KEEP_RECENT_GRACE",
    "ARCHIVE",
    "RM_ARCHIVED",
    "ERROR_UNREADABLE",
]

TERMINAL_TASK_STATUSES = {
    "completed",
    "done",
    "cancelled",
    "cancelled-zombie",
    "cancelled-stale",
    "completed-by-watermark",
    "failed-terminal",
}
PENDING_REQUEST_STATUSES = {"pending", "in_progress", "queued", "open", "todo", "blocked"}


@dataclass(frozen=True)
class PendingInspection:
    has_pending: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReapDecision:
    session_id: str
    path: str
    decision: DecisionCode
    reason: str
    age_seconds: int | None = None
    pending_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReapResult:
    decisions: list[ReapDecision]
    archived: list[str]
    removed: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [d.to_dict() for d in self.decisions],
            "archived": self.archived,
            "removed": self.removed,
            "errors": self.errors,
        }


def pid_alive(pid: int | str | None) -> bool:
    if pid in (None, ""):
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
        return False


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            rows.append({"_corrupt": True, "raw": line})
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def session_id_for(session_dir: Path) -> str:
    return session_dir.name


def session_age_seconds(session_dir: Path, now: float | None = None) -> int | None:
    now = time.time() if now is None else now
    meta = session_dir / "meta.json"
    if meta.exists():
        try:
            data = _read_json(meta)
            start_epoch = data.get("start_epoch") or data.get("started_at_epoch")
            if start_epoch:
                return max(0, int(now - float(start_epoch)))
        except Exception:
            return None
    try:
        return max(0, int(now - session_dir.stat().st_mtime))
    except OSError:
        return None


def session_pid(session_dir: Path) -> int | None:
    meta = session_dir / "meta.json"
    if not meta.exists():
        return None
    try:
        data = _read_json(meta)
        pid = data.get("pid")
        return int(pid) if pid not in (None, "") else None
    except Exception:
        return None


def _task_unresolved(task: dict[str, Any]) -> bool:
    status = str(task.get("status") or "").lower()
    if not status:
        return False
    return status not in TERMINAL_TASK_STATUSES


def inspect_pending(session_dir: Path) -> PendingInspection:
    reasons: list[str] = []

    requests = session_dir / "user-requests.jsonl"
    for idx, row in enumerate(_iter_jsonl(requests), start=1):
        if row.get("_corrupt"):
            reasons.append(f"user-requests.jsonl:{idx}:corrupt")
            continue
        status = str(row.get("status") or "").lower()
        if status in PENDING_REQUEST_STATUSES:
            reasons.append(f"user-requests.jsonl:{idx}:status={status}")

    tasks_file = session_dir / "tasks.json"
    if tasks_file.exists():
        try:
            raw = _read_json(tasks_file)
            tasks = raw if isinstance(raw, list) else raw.get("tasks", []) if isinstance(raw, dict) else []
            for idx, task in enumerate(tasks, start=1):
                if isinstance(task, dict) and _task_unresolved(task):
                    reasons.append(f"tasks.json:{idx}:status={task.get('status')}")
        except Exception:
            reasons.append("tasks.json:unreadable")

    for name in ("handoff.md", "backlog.md", "summary.md"):
        marker = session_dir / name
        if marker.exists() and marker.stat().st_size > 0:
            # Durable summaries are valuable but not necessarily pending. Keep only
            # if they explicitly advertise unfinished work.
            text = marker.read_text(encoding="utf-8", errors="replace").lower()
            if any(token in text for token in ("pending", "todo", "next steps", "blocked", "in progress")):
                reasons.append(f"{name}:pending-marker")

    parked = session_dir / "parked-edits"
    if parked.exists() and any(parked.iterdir()):
        reasons.append("parked-edits:non-empty")

    return PendingInspection(has_pending=bool(reasons), reasons=reasons)


def reap_decision(
    session_dir: Path,
    *,
    now: float | None = None,
    grace_seconds: int = 24 * 3600,
    archived: bool = False,
    archive_retention_days: int = 90,
) -> ReapDecision:
    now = time.time() if now is None else now
    sid = session_id_for(session_dir)
    if not session_dir.exists() or not session_dir.is_dir():
        return ReapDecision(sid, str(session_dir), "ERROR_UNREADABLE", "not a directory")

    age = session_age_seconds(session_dir, now=now)
    if archived:
        if age is not None and age >= archive_retention_days * 24 * 3600:
            return ReapDecision(sid, str(session_dir), "RM_ARCHIVED", "archive retention exceeded", age)
        return ReapDecision(sid, str(session_dir), "KEEP_RECENT_GRACE", "archive retention grace", age)

    pid = session_pid(session_dir)
    if pid_alive(pid):
        return ReapDecision(sid, str(session_dir), "KEEP_ACTIVE", f"pid {pid} alive", age)

    pending = inspect_pending(session_dir)
    if pending.has_pending:
        return ReapDecision(sid, str(session_dir), "KEEP_PENDING_CONTENT", "pending content present", age, pending.reasons)

    if age is None:
        return ReapDecision(sid, str(session_dir), "ERROR_UNREADABLE", "cannot determine age", None)
    if age < grace_seconds:
        return ReapDecision(sid, str(session_dir), "KEEP_RECENT_GRACE", f"age {age}s below grace {grace_seconds}s", age)
    return ReapDecision(sid, str(session_dir), "ARCHIVE", "dead, content-clean, beyond grace", age)


def sessions_root(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "sessions"


def archive_root(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "archive" / "sessions"


def marker_archive_root(project_dir: Path) -> Path:
    return archive_root(project_dir) / "_markers"


def is_session_marker(path: Path) -> bool:
    """Return true for per-session marker files that are safe to reap.

    Runtime coordination files such as active-sessions.json, lock files, and
    event streams are intentionally excluded. The marker files below are
    per-PID breadcrumbs created by session startup and are the source of the
    high-volume filesystem accumulation reported by cos_work_inventory.py.
    """
    return path.is_file() and (
        path.name.startswith(".current-session-")
        or (path.name.startswith(".context-") and path.suffix == ".json")
    )


def marker_pid(path: Path) -> int | None:
    for prefix in (".current-session-", ".context-"):
        if path.name.startswith(prefix):
            raw = path.name[len(prefix) :]
            if raw.endswith(".json"):
                raw = raw[: -len(".json")]
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def marker_age_seconds(path: Path, now: float | None = None) -> int | None:
    now = time.time() if now is None else now
    try:
        return max(0, int(now - path.stat().st_mtime))
    except OSError:
        return None


def marker_reap_decision(path: Path, *, now: float | None = None, grace_seconds: int = 24 * 3600) -> ReapDecision:
    sid = path.name
    if not is_session_marker(path):
        return ReapDecision(sid, str(path), "ERROR_UNREADABLE", "not a reapable session marker")
    age = marker_age_seconds(path, now=now)
    pid = marker_pid(path)
    if pid_alive(pid):
        return ReapDecision(sid, str(path), "KEEP_ACTIVE", f"pid {pid} alive", age)
    if age is None:
        return ReapDecision(sid, str(path), "ERROR_UNREADABLE", "cannot determine age", None)
    if age < grace_seconds:
        return ReapDecision(sid, str(path), "KEEP_RECENT_GRACE", f"age {age}s below grace {grace_seconds}s", age)
    return ReapDecision(sid, str(path), "ARCHIVE", "dead marker beyond grace", age)


def archive_session(session_dir: Path, archive_dir: Path, *, now: float | None = None) -> str:
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / session_dir.name
    if target.exists():
        suffix = int(time.time() if now is None else now)
        target = archive_dir / f"{session_dir.name}.{suffix}"
    shutil.move(str(session_dir), str(target))
    marker = target / "archived.json"
    marker.write_text(
        json.dumps({"archived_at_epoch": int(time.time() if now is None else now), "source": "session-fs-reap"}, indent=2),
        encoding="utf-8",
    )
    return str(target)


def archive_marker(marker: Path, project_dir: Path, *, now: float | None = None) -> str:
    archive_dir = marker_archive_root(project_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / marker.name
    if target.exists():
        suffix = int(time.time() if now is None else now)
        target = archive_dir / f"{marker.name}.{suffix}"
    shutil.move(str(marker), str(target))
    return str(target)


def reap_archived_sessions(project_dir: Path, *, now: float | None = None, archive_retention_days: int = 90, dry_run: bool = False) -> list[ReapDecision]:
    root = archive_root(project_dir)
    if not root.exists():
        return []
    decisions: list[ReapDecision] = []
    for session_dir in sorted(root.iterdir()):
        if not session_dir.is_dir():
            continue
        decision = reap_decision(session_dir, now=now, archived=True, archive_retention_days=archive_retention_days)
        decisions.append(decision)
        if decision.decision == "RM_ARCHIVED" and not dry_run:
            shutil.rmtree(session_dir)
    return decisions


def reap_archived_markers(project_dir: Path, *, now: float | None = None, archive_retention_days: int = 90, dry_run: bool = False) -> list[ReapDecision]:
    root = marker_archive_root(project_dir)
    if not root.exists():
        return []
    now = time.time() if now is None else now
    decisions: list[ReapDecision] = []
    for marker in sorted(root.iterdir()):
        if not marker.is_file():
            continue
        age = marker_age_seconds(marker, now=now)
        if age is not None and age >= archive_retention_days * 24 * 3600:
            decision = ReapDecision(marker.name, str(marker), "RM_ARCHIVED", "marker archive retention exceeded", age)
            if not dry_run:
                marker.unlink()
        else:
            decision = ReapDecision(marker.name, str(marker), "KEEP_RECENT_GRACE", "marker archive retention grace", age)
        decisions.append(decision)
    return decisions


def reap_sessions(
    project_dir: Path,
    *,
    now: float | None = None,
    grace_seconds: int = 24 * 3600,
    archive_retention_days: int = 90,
    dry_run: bool = False,
) -> ReapResult:
    root = sessions_root(project_dir)
    archive_dir = archive_root(project_dir)
    decisions: list[ReapDecision] = []
    archived: list[str] = []
    removed: list[str] = []
    errors: list[str] = []

    if root.exists():
        for session_dir in sorted(root.iterdir()):
            if not session_dir.is_dir():
                continue
            decision = reap_decision(session_dir, now=now, grace_seconds=grace_seconds)
            decisions.append(decision)
            if decision.decision == "ARCHIVE" and not dry_run:
                try:
                    archived.append(archive_session(session_dir, archive_dir, now=now))
                except Exception as exc:  # keep going; reaper must degrade safely
                    errors.append(f"archive {session_dir}: {exc}")

        for marker in sorted(root.iterdir()):
            if not is_session_marker(marker):
                continue
            decision = marker_reap_decision(marker, now=now, grace_seconds=grace_seconds)
            decisions.append(decision)
            if decision.decision == "ARCHIVE" and not dry_run:
                try:
                    archived.append(archive_marker(marker, project_dir, now=now))
                except Exception as exc:  # keep going; reaper must degrade safely
                    errors.append(f"archive marker {marker}: {exc}")

    for decision in reap_archived_sessions(project_dir, now=now, archive_retention_days=archive_retention_days, dry_run=dry_run):
        decisions.append(decision)
        if decision.decision == "RM_ARCHIVED" and not dry_run:
            removed.append(decision.path)

    for decision in reap_archived_markers(project_dir, now=now, archive_retention_days=archive_retention_days, dry_run=dry_run):
        decisions.append(decision)
        if decision.decision == "RM_ARCHIVED" and not dry_run:
            removed.append(decision.path)

    return ReapResult(decisions=decisions, archived=archived, removed=removed, errors=errors)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--grace-seconds", type=int, default=int(os.environ.get("COS_SESSION_FS_REAP_GRACE_SECONDS", 24 * 3600)))
    parser.add_argument("--archive-retention-days", type=int, default=int(os.environ.get("COS_SESSION_FS_REAP_ARCHIVE_DAYS", 90)))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = reap_sessions(
        Path(args.project_dir).resolve(),
        grace_seconds=args.grace_seconds,
        archive_retention_days=args.archive_retention_days,
        dry_run=args.dry_run,
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"[session-fs-reap] decisions={len(result.decisions)} "
            f"archived={len(result.archived)} removed={len(result.removed)} errors={len(result.errors)}"
        )
        for decision in result.decisions[:40]:
            print(f"  {decision.decision} {decision.session_id}: {decision.reason}")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
