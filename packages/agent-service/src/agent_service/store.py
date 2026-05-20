"""File-backed session store for ADR-291 Phase 2."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from agent_service.models.session import (
    SessionDetails,
    SessionEvent,
    SessionEventsPage,
    SessionLatestEvent,
    SessionStatusResponse,
    SessionSummary,
)


class SessionNotFoundError(KeyError):
    """Raised when a requested session id is not present in the store."""


class InvalidSessionPatchError(ValueError):
    """Raised when a session update patch contains unsupported fields."""


class StoredSession(BaseModel):
    """Internal durable representation for a session."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    status: str = Field(default="active")
    workspace: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    events: list[SessionEvent] = Field(default_factory=list)


class SessionStoreSnapshot(BaseModel):
    """Versioned JSON file format for the session store."""

    version: int = 1
    sessions: dict[str, StoredSession] = Field(default_factory=dict)


class JsonSessionStore:
    """Small atomic JSON session store.

    The store is intentionally simple for the ADR-291 Phase 2 slice: each
    mutation reads, changes, and atomically rewrites one JSON file. This keeps
    durability understandable and leaves the SQLite migration path open.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def create(self, *, workspace: str | None, metadata: dict[str, Any]) -> StoredSession:
        with self._lock:
            snapshot = self._read()
            now = _now()
            session_id = uuid.uuid4().hex
            session = StoredSession(
                session_id=session_id,
                created_at=now,
                updated_at=now,
                workspace=workspace,
                metadata=dict(metadata),
                events=[
                    SessionEvent(
                        event_id=uuid.uuid4().hex,
                        session_id=session_id,
                        timestamp=now,
                        type="session.created",
                        payload={"workspace": workspace, "metadata": dict(metadata)},
                    )
                ],
            )
            snapshot.sessions[session_id] = session
            self._write(snapshot)
            return session

    def list(self, *, page: int, page_size: int) -> tuple[list[SessionSummary], int]:
        with self._lock:
            sessions = sorted(
                self._read().sessions.values(),
                key=lambda item: item.updated_at,
                reverse=True,
            )
            total = len(sessions)
            start = (page - 1) * page_size
            page_items = sessions[start : start + page_size]
            return [self._summary(item) for item in page_items], total

    def details(self, session_id: str) -> SessionDetails:
        with self._lock:
            return self._details(self._get(self._read(), session_id))

    def status(self, session_id: str) -> SessionStatusResponse:
        with self._lock:
            session = self._get(self._read(), session_id)
            return SessionStatusResponse(
                session_id=session.session_id,
                status=session.status,
                last_activity_at=session.updated_at,
            )

    def events(self, *, session_id: str, page: int, page_size: int) -> SessionEventsPage:
        with self._lock:
            session = self._get(self._read(), session_id)
            total = len(session.events)
            start = (page - 1) * page_size
            return SessionEventsPage(
                session_id=session_id,
                events=session.events[start : start + page_size],
                page=page,
                page_size=page_size,
                total=total,
            )

    def latest_event(self, session_id: str) -> SessionLatestEvent:
        with self._lock:
            session = self._get(self._read(), session_id)
            event = session.events[-1] if session.events else None
            return SessionLatestEvent(session_id=session_id, event=event)

    def update(self, *, session_id: str, patch: dict[str, Any]) -> SessionDetails:
        with self._lock:
            snapshot = self._read()
            session = self._get(snapshot, session_id)
            allowed = {"status", "workspace", "metadata"}
            unsupported = sorted(set(patch) - allowed)
            if unsupported:
                raise InvalidSessionPatchError(
                    "unsupported session patch fields: " + ", ".join(unsupported)
                )
            if "status" in patch:
                status = patch["status"]
                if not isinstance(status, str) or not status.strip():
                    raise InvalidSessionPatchError("status must be a non-empty string")
                session.status = status.strip()
            if "workspace" in patch:
                workspace = patch["workspace"]
                if workspace is not None and not isinstance(workspace, str):
                    raise InvalidSessionPatchError("workspace must be a string or null")
                session.workspace = workspace
            if "metadata" in patch:
                metadata = patch["metadata"]
                if not isinstance(metadata, dict):
                    raise InvalidSessionPatchError("metadata must be an object")
                session.metadata.update(metadata)
            session.updated_at = _now()
            session.events.append(
                SessionEvent(
                    event_id=uuid.uuid4().hex,
                    session_id=session_id,
                    timestamp=session.updated_at,
                    type="session.updated",
                    payload={"patch": patch},
                )
            )
            snapshot.sessions[session_id] = session
            self._write(snapshot)
            return self._details(session)


    def append_event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> SessionEvent:
        with self._lock:
            snapshot = self._read()
            session = self._get(snapshot, session_id)
            now = _now()
            event = SessionEvent(
                event_id=uuid.uuid4().hex,
                session_id=session_id,
                timestamp=now,
                type=event_type,
                payload=dict(payload),
            )
            session.events.append(event)
            session.updated_at = now
            snapshot.sessions[session_id] = session
            self._write(snapshot)
            return event

    def delete(self, session_id: str) -> None:
        with self._lock:
            snapshot = self._read()
            self._get(snapshot, session_id)
            del snapshot.sessions[session_id]
            self._write(snapshot)

    def _get(self, snapshot: SessionStoreSnapshot, session_id: str) -> StoredSession:
        try:
            return snapshot.sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def _read(self) -> SessionStoreSnapshot:
        if not self.path.exists():
            return SessionStoreSnapshot()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return SessionStoreSnapshot.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise RuntimeError(f"invalid agent session store: {self.path}") from exc

    def _write(self, snapshot: SessionStoreSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps(snapshot.model_dump(mode="json"), sort_keys=True, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def _summary(self, session: StoredSession) -> SessionSummary:
        title = session.metadata.get("title")
        return SessionSummary(
            session_id=session.session_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            title=title if isinstance(title, str) else None,
            status=session.status,
        )

    def _details(self, session: StoredSession) -> SessionDetails:
        return SessionDetails(
            session_id=session.session_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            status=session.status,
            workspace=session.workspace,
            metadata=session.metadata,
            message_count=len(session.events),
        )


def _now() -> datetime:
    return datetime.now(tz=UTC)
