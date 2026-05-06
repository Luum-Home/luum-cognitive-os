# SCOPE: both
"""Directed inter-agent message bus with inbox and acknowledgement semantics."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

try:
    from lib.session_bus import append_event
except Exception:  # pragma: no cover - portable fallback for projected copies
    append_event = None


SEVERITIES = {"info", "warn", "block"}
MESSAGE_TYPES = {"audit_finding", "implementation_request", "question", "reply", "status"}
ACK_STATUSES = {"accepted", "applied", "rejected", "needs-clarification", "seen"}


@dataclass(frozen=True)
class MessageFinding:
    """Finding emitted by message-bus gates."""

    status: str
    source: str
    message: str
    evidence: str = ""


def current_session(default: str = "unknown") -> str:
    return os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or default


def coordination_dir(project_dir: str | Path) -> Path:
    path = Path(project_dir) / ".cognitive-os" / "coordination"
    path.mkdir(parents=True, exist_ok=True)
    return path


def messages_path(project_dir: str | Path) -> Path:
    return coordination_dir(project_dir) / "agent-messages.jsonl"


def lock_path(project_dir: str | Path) -> Path:
    return coordination_dir(project_dir) / "agent-messages.lock"


def now_epoch() -> float:
    return time.time()


def message_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def send_message(
    project_dir: str | Path,
    *,
    from_session: str,
    to_session: str,
    message_type: str,
    body: str,
    severity: str = "info",
    role: str = "auditor",
    target: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a directed message to another session."""

    if message_type not in MESSAGE_TYPES:
        raise ValueError(f"unknown message type: {message_type}")
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity: {severity}")
    if not to_session:
        raise ValueError("to_session is required")
    base = {
        "schema_version": 1,
        "kind": "message",
        "timestamp_epoch": now_epoch(),
        "from_session": from_session,
        "to_session": to_session,
        "role": role,
        "message_type": message_type,
        "severity": severity,
        "target": target,
        "body": body,
        "metadata": metadata or {},
    }
    row = {"message_id": message_id(base), **base}
    with lock_path(project_dir).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        _append_jsonl(messages_path(project_dir), row)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    if append_event is not None:
        try:
            append_event("agent_message_sent", {"message_id": row["message_id"], "to_session": to_session, "severity": severity}, project_dir=project_dir, session_id=from_session)
        except Exception:
            pass
    return row


def ack_message(
    project_dir: str | Path,
    *,
    message_id_value: str,
    session_id: str,
    status: str,
    note: str = "",
) -> dict[str, Any]:
    """Acknowledge a directed message."""

    if status not in ACK_STATUSES:
        raise ValueError(f"unknown ack status: {status}")
    row = {
        "schema_version": 1,
        "kind": "ack",
        "timestamp_epoch": now_epoch(),
        "message_id": message_id_value,
        "session_id": session_id,
        "status": status,
        "note": note,
    }
    with lock_path(project_dir).open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        _append_jsonl(messages_path(project_dir), row)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    if append_event is not None:
        try:
            append_event("agent_message_ack", {"message_id": message_id_value, "status": status}, project_dir=project_dir, session_id=session_id)
        except Exception:
            pass
    return row


def read_messages(project_dir: str | Path) -> list[dict[str, Any]]:
    return _read_rows(messages_path(project_dir))


def latest_acks(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    acks: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("kind") == "ack" and row.get("message_id"):
            acks[str(row["message_id"])] = row
    return acks


def inbox(project_dir: str | Path, *, session_id: str, include_acked: bool = False) -> list[dict[str, Any]]:
    """Return directed messages for a session."""

    rows = read_messages(project_dir)
    acks = latest_acks(rows)
    messages = [row for row in rows if row.get("kind") == "message" and row.get("to_session") in {session_id, "*"}]
    if include_acked:
        return [{**row, "ack": acks.get(str(row.get("message_id")))} for row in messages]
    return [row for row in messages if str(row.get("message_id")) not in acks]


def unacked_blockers(project_dir: str | Path, *, session_id: str | None = None) -> list[dict[str, Any]]:
    """Return unacknowledged blocking findings for a session or all sessions."""

    rows = read_messages(project_dir)
    acks = latest_acks(rows)
    blockers = []
    for row in rows:
        if row.get("kind") != "message" or row.get("severity") != "block":
            continue
        if session_id and row.get("to_session") not in {session_id, "*"}:
            continue
        if str(row.get("message_id")) not in acks:
            blockers.append(row)
    return blockers


def blocker_findings(project_dir: str | Path, *, session_id: str | None = None) -> list[MessageFinding]:
    """Return gate findings for unacknowledged blocking messages."""

    return [
        MessageFinding(
            status="FAIL",
            source=str(row.get("message_id")),
            message=f"unacknowledged blocking agent message for {row.get('to_session')}: {row.get('body')}",
            evidence=f"from={row.get('from_session')} target={row.get('target')} type={row.get('message_type')}",
        )
        for row in unacked_blockers(project_dir, session_id=session_id)
    ]


def rewrite_without_messages(project_dir: str | Path, message_ids: set[str]) -> None:
    """Test/maintenance helper: rewrite the log excluding message ids."""

    path = messages_path(project_dir)
    rows = [row for row in read_messages(project_dir) if str(row.get("message_id")) not in message_ids]
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def findings_to_dict(findings: Sequence[MessageFinding]) -> list[dict[str, str]]:
    return [asdict(finding) for finding in findings]
