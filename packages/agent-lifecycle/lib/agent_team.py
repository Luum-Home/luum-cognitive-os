# SCOPE: both
"""ADR-233 file-IPC substrate for cross-session agent teams."""
from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = "agent-team-file-ipc/v1"


class AgentTeamError(RuntimeError):
    """Base class for file-IPC team errors."""


@dataclass(frozen=True)
class TeamMember:
    session_id: str
    role: str
    worktree_path: str
    status: str = "active"
    started_at: float = 0.0

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["schema_version"] = SCHEMA_VERSION
        record["started_at"] = self.started_at or time.time()
        return record


@dataclass(frozen=True)
class TeamTask:
    task_id: str
    title: str
    status: str = "pending"
    depends_on: tuple[str, ...] = ()
    claimed_by: str | None = None
    output_summary: str = ""
    updated_at: float = 0.0


@dataclass(frozen=True)
class InboxMessage:
    message_id: str
    sender: str
    recipient: str
    text: str
    timestamp: float
    read: bool = False


class AgentTeam:
    """File-backed same-machine team coordination with advisory locks."""

    def __init__(self, team_name: str, *, project_dir: str | Path | None = None) -> None:
        if not team_name or "/" in team_name or "\\" in team_name or team_name in {".", ".."}:
            raise ValueError(f"unsafe team_name: {team_name!r}")
        self.team_name = team_name
        self.project_dir = Path(project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()
        self.root = self.project_dir / ".cognitive-os" / "teams" / team_name
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "inbox").mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _locked(self, name: str) -> Iterator[None]:
        lock = self.root / f"{name}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)
        return records

    @property
    def members_path(self) -> Path:
        return self.root / "members.jsonl"

    @property
    def tasks_path(self) -> Path:
        return self.root / "tasks.jsonl"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    def join(self, *, session_id: str, role: str, worktree_path: str, status: str = "active") -> TeamMember:
        member = TeamMember(session_id=session_id, role=role, worktree_path=worktree_path, status=status)
        with self._locked("members"):
            self._append_jsonl(self.members_path, {"event": "member_joined", **member.to_record()})
        self.emit_event("member_joined", session_id=session_id, role=role)
        return member

    def members(self) -> list[TeamMember]:
        latest: dict[str, dict[str, Any]] = {}
        for record in self._read_jsonl(self.members_path):
            sid = str(record.get("session_id") or "")
            if sid:
                latest[sid] = record
        return [
            TeamMember(
                session_id=str(record["session_id"]),
                role=str(record.get("role") or "teammate"),
                worktree_path=str(record.get("worktree_path") or ""),
                status=str(record.get("status") or "active"),
                started_at=float(record.get("started_at") or 0.0),
            )
            for record in latest.values()
        ]

    def create_task(self, title: str, *, task_id: str | None = None, depends_on: list[str] | None = None) -> TeamTask:
        tid = task_id or f"task-{uuid.uuid4().hex[:12]}"
        task = TeamTask(task_id=tid, title=title, depends_on=tuple(depends_on or ()), updated_at=time.time())
        record = {
            "schema_version": SCHEMA_VERSION,
            "event": "task_created",
            "task_id": task.task_id,
            "title": task.title,
            "status": task.status,
            "depends_on": list(task.depends_on),
            "updated_at": task.updated_at,
        }
        with self._locked("tasks"):
            self._append_jsonl(self.tasks_path, record)
        self.emit_event("task_created", task_id=tid, title=title)
        return task

    def tasks(self) -> list[TeamTask]:
        state: dict[str, dict[str, Any]] = {}
        for record in self._read_jsonl(self.tasks_path):
            tid = str(record.get("task_id") or "")
            if not tid:
                continue
            base = state.setdefault(tid, {})
            base.update(record)
        return [
            TeamTask(
                task_id=str(record["task_id"]),
                title=str(record.get("title") or ""),
                status=str(record.get("status") or "pending"),
                depends_on=tuple(str(dep) for dep in record.get("depends_on") or ()),
                claimed_by=record.get("claimed_by"),
                output_summary=str(record.get("output_summary") or ""),
                updated_at=float(record.get("updated_at") or 0.0),
            )
            for record in state.values()
        ]

    def claim_next(self, *, session_id: str) -> TeamTask | None:
        with self._locked("tasks"):
            tasks = self.tasks()
            completed = {task.task_id for task in tasks if task.status == "completed"}
            for task in tasks:
                if task.status != "pending":
                    continue
                if any(dep not in completed for dep in task.depends_on):
                    continue
                record = {
                    "schema_version": SCHEMA_VERSION,
                    "event": "task_claimed",
                    "task_id": task.task_id,
                    "title": task.title,
                    "status": "in_progress",
                    "depends_on": list(task.depends_on),
                    "claimed_by": session_id,
                    "updated_at": time.time(),
                }
                self._append_jsonl(self.tasks_path, record)
                self.emit_event("task_claimed", task_id=task.task_id, session_id=session_id)
                return TeamTask(
                    task_id=task.task_id,
                    title=task.title,
                    status="in_progress",
                    depends_on=task.depends_on,
                    claimed_by=session_id,
                    updated_at=record["updated_at"],
                )
        return None

    def complete_task(self, task_id: str, *, session_id: str, output_summary: str = "") -> TeamTask:
        with self._locked("tasks"):
            current = {task.task_id: task for task in self.tasks()}.get(task_id)
            if current is None:
                raise AgentTeamError(f"unknown task: {task_id}")
            record = {
                "schema_version": SCHEMA_VERSION,
                "event": "task_completed",
                "task_id": task_id,
                "title": current.title,
                "status": "completed",
                "depends_on": list(current.depends_on),
                "claimed_by": session_id,
                "output_summary": output_summary,
                "updated_at": time.time(),
            }
            self._append_jsonl(self.tasks_path, record)
        self.emit_event("task_completed", task_id=task_id, session_id=session_id)
        return TeamTask(
            task_id=task_id,
            title=current.title,
            status="completed",
            depends_on=current.depends_on,
            claimed_by=session_id,
            output_summary=output_summary,
            updated_at=record["updated_at"],
        )

    def send_message(self, *, sender: str, recipient: str, text: str, message_id: str | None = None) -> InboxMessage:
        message = InboxMessage(
            message_id=message_id or f"msg-{uuid.uuid4().hex[:12]}",
            sender=sender,
            recipient=recipient,
            text=text,
            timestamp=time.time(),
        )
        with self._locked(f"inbox-{recipient}"):
            self._append_jsonl(self.root / "inbox" / f"{recipient}.jsonl", {"schema_version": SCHEMA_VERSION, **asdict(message)})
        self.emit_event("message_sent", sender=sender, recipient=recipient, message_id=message.message_id)
        return message

    def inbox(self, session_id: str) -> list[InboxMessage]:
        messages = []
        for record in self._read_jsonl(self.root / "inbox" / f"{session_id}.jsonl"):
            messages.append(
                InboxMessage(
                    message_id=str(record.get("message_id") or ""),
                    sender=str(record.get("sender") or ""),
                    recipient=str(record.get("recipient") or session_id),
                    text=str(record.get("text") or ""),
                    timestamp=float(record.get("timestamp") or 0.0),
                    read=bool(record.get("read") or False),
                )
            )
        return messages

    def emit_event(self, event_type: str, **payload: Any) -> dict[str, Any]:
        record = {
            "schema_version": SCHEMA_VERSION,
            "event": event_type,
            "team_name": self.team_name,
            "timestamp": time.time(),
            **payload,
        }
        with self._locked("events"):
            self._append_jsonl(self.events_path, record)
        return record

    def events(self) -> list[dict[str, Any]]:
        return self._read_jsonl(self.events_path)
