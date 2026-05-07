# SCOPE: both
"""Append-only inter-session event bus for Cognitive OS coordination."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import fcntl


SESSION_EVENT_TAXONOMY: frozenset[str] = frozenset(
    {
        "session-start",
        "branch-acquire",
        "branch-release",
        "coordination-claim",
        "worktree-intake",
        "agent-message-sent",
        "agent-message-ack",
        "agent-spawn",
        "file-write-intent",
        "commit-intent",
        "commit-landed",
        "session-end",
    }
)
"""ADR-183 v1 cross-session event taxonomy.

This is an open taxonomy: producers may append future event types without
breaking the bus, but tests pin the v1 set so the current wiring cannot
silently regress.
"""


EVENT_STORE_SCHEMA_VERSION = "event-sourced-session-bus/v1"


class EventBusError(RuntimeError):
    """Base class for event-sourced session bus failures."""


class EventStreamGapDetected(EventBusError):
    """Raised when a per-session stream is not gap-free by seq."""


class EventStreamCorrupt(EventBusError):
    """Raised when a per-session event stream contains invalid JSON/schema."""


class UnsupportedEventBusPlatform(EventBusError):
    """Raised when the local filesystem/OS cannot safely support locking."""


@dataclass(frozen=True)
class PeerSummary:
    """Compact summary of one peer orchestrator session."""

    session_id: str
    branch: str
    last_seen: float
    pid: int
    project_dir: str
    topic_keywords: list[str]
    recent_writes: list[str]
    recent_events: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _root(project_dir: str | Path | None = None) -> Path:
    return Path(project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()


def events_path(project_dir: str | Path | None = None) -> Path:
    return _root(project_dir) / ".cognitive-os" / "sessions" / "events.jsonl"


def lock_path(project_dir: str | Path | None = None) -> Path:
    return _root(project_dir) / ".cognitive-os" / "sessions" / "events.lock"


def event_index_path(project_dir: str | Path | None = None) -> Path:
    """Return the ADR-226/ADR-205 fan-out event index path."""
    return _root(project_dir) / ".cognitive-os" / "coordination" / "event-index.jsonl"


def event_index_lock_path(project_dir: str | Path | None = None) -> Path:
    """Return the lock path for the fan-out event index."""
    return _root(project_dir) / ".cognitive-os" / "coordination" / "event-index.lock"


@contextmanager
def _locked(project_dir: str | Path | None = None) -> Iterator[None]:
    path = lock_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _session_id(default: str = "unknown") -> str:
    return (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or default
    )


def normalize_event_type(event_type: str) -> str:
    """Normalize an event type to ADR-183 wire format."""
    return event_type.strip().replace("_", "-")


def append_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    project_dir: str | Path | None = None,
    session_id: str | None = None,
    event_store: bool = False,
    strict_durability: bool = False,
    single_writer: bool = False,
) -> dict[str, Any]:
    """Append one coordination event and return the stored event.

    By default this preserves the ADR-027/ADR-205 v1 global JSONL behavior.
    Passing ``event_store=True`` opts into ADR-226 Slice A: per-session streams
    with monotonic ``seq`` and gap-detectable reads.
    """
    if event_store:
        return append_session_event(
            event_type,
            payload,
            project_dir=project_dir,
            session_id=session_id,
            strict_durability=strict_durability,
            single_writer=single_writer,
        )
    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")
    root = _root(project_dir)
    event = {
        "schema_version": 1,
        "timestamp_epoch": time.time(),
        "event_type": normalize_event_type(event_type),
        "session_id": session_id or _session_id(),
        "pid": os.getpid(),
        "project_dir": str(root),
        "payload": payload or {},
    }
    path = events_path(root)
    with _locked(root):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def read_events(
    *,
    project_dir: str | Path | None = None,
    limit: int | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Read recent coordination events from newest window preserving file order."""
    path = events_path(project_dir)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if limit is not None and limit > 0:
        lines = lines[-limit:]
    events: list[dict[str, Any]] = []
    normalized_type = event_type.replace("_", "-") if event_type else None
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if normalized_type and event.get("event_type") != normalized_type:
            continue
        events.append(event)
    return events



def _safe_session_id(session_id: str | None) -> str:
    sid = session_id or _session_id()
    if not sid or sid == "unknown":
        raise ValueError("session_id is required for event-sourced streams")
    if sid in {".", ".."} or "/" in sid or "\\" in sid:
        raise ValueError(f"unsafe session_id for path-backed stream: {sid!r}")
    return sid


def session_stream_path(project_dir: str | Path | None = None, session_id: str | None = None) -> Path:
    """Return the ADR-226 per-session stream path for ``session_id``."""
    sid = _safe_session_id(session_id)
    return _root(project_dir) / ".cognitive-os" / "sessions" / f"{sid}.events.jsonl"


def session_counter_path(project_dir: str | Path | None = None, session_id: str | None = None) -> Path:
    """Return the rebuildable per-session seq counter cache path."""
    sid = _safe_session_id(session_id)
    return _root(project_dir) / ".cognitive-os" / "sessions" / ".seq-counters" / f"{sid}.counter"


def session_lock_path(project_dir: str | Path | None = None, session_id: str | None = None) -> Path:
    """Return the per-session lock path used by ADR-226 writers."""
    sid = _safe_session_id(session_id)
    return _root(project_dir) / ".cognitive-os" / "sessions" / ".seq-counters" / f"{sid}.lock"


def _platform_supported(*, single_writer: bool = False, allow_network_fs: bool = False) -> None:
    """Refuse known-unsupported platforms before writing event-store data.

    Slice A intentionally keeps filesystem detection conservative and
    dependency-free. Tests can force the refusal path with
    ``COS_EVENT_BUS_FORCE_UNSUPPORTED_FS=1``; production can bypass locking only
    with explicit ``single_writer=True`` when the orchestrator guarantees one
    writer for the session.
    """
    if single_writer:
        return
    if os.environ.get("COS_EVENT_BUS_FORCE_UNSUPPORTED_FS") == "1" and not allow_network_fs:
        raise UnsupportedEventBusPlatform("event bus refuses forced unsupported filesystem")
    system = platform.system().lower()
    if system.startswith("windows"):
        raise UnsupportedEventBusPlatform("ADR-226 Slice A supports Linux/macOS local filesystems only")
    if system not in {"linux", "darwin"}:
        raise UnsupportedEventBusPlatform(f"unsupported event bus platform: {platform.system()}")


@contextmanager
def _session_locked(
    project_dir: str | Path | None = None,
    session_id: str | None = None,
    *,
    single_writer: bool = False,
) -> Iterator[None]:
    """Lock a per-session event stream unless single-writer mode is explicit."""
    if single_writer:
        yield
        return
    path = session_lock_path(project_dir, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _json_lines(path: Path) -> Iterable[tuple[int, str]]:
    if not path.is_file():
        return []
    return enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1)


def _max_seq_in_stream(path: Path) -> int:
    max_seq = 0
    for line_number, line in _json_lines(path):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventStreamCorrupt(f"corrupt JSON at {path}:{line_number}") from exc
        if not isinstance(event, dict):
            raise EventStreamCorrupt(f"non-object event at {path}:{line_number}")
        seq = event.get("seq")
        if not isinstance(seq, int) or seq < 1:
            raise EventStreamCorrupt(f"missing/invalid seq at {path}:{line_number}")
        max_seq = max(max_seq, seq)
    return max_seq


def _write_counter(path: Path, seq: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(seq) + "\n", encoding="utf-8")


@contextmanager
def _index_locked(project_dir: str | Path | None = None) -> Iterator[None]:
    path = event_index_lock_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _append_event_index(project_dir: Path, event: dict[str, Any], *, strict_durability: bool = False) -> None:
    record = {
        "schema_version": EVENT_STORE_SCHEMA_VERSION,
        "seq": event["seq"],
        "session_id": event["session_id"],
        "event_type": event["event_type"],
        "ts": event["ts"],
    }
    path = event_index_path(project_dir)
    with _index_locked(project_dir):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            if strict_durability:
                os.fsync(handle.fileno())


def read_event_index(*, project_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Read the fan-out event index and return valid records in file order."""
    path = event_index_path(project_dir)
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in _json_lines(path):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventStreamCorrupt(f"corrupt JSON at {path}:{line_number}") from exc
        if record.get("schema_version") != EVENT_STORE_SCHEMA_VERSION:
            raise EventStreamCorrupt(f"unexpected schema_version at {path}:{line_number}")
        records.append(record)
    return records


def assert_index_consistent(project_dir: str | Path | None, session_id: str) -> None:
    """Raise if a session stream event is missing from the fan-out index."""
    session_events = read_session_events(session_id, project_dir=project_dir)
    index_keys = {
        (record.get("session_id"), record.get("seq"), record.get("event_type"), record.get("ts"))
        for record in read_event_index(project_dir=project_dir)
    }
    for event in session_events:
        key = (event.get("session_id"), event.get("seq"), event.get("event_type"), event.get("ts"))
        if key not in index_keys:
            raise EventStreamGapDetected(f"missing event-index record for session={key[0]} seq={key[1]}")


def append_session_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    project_dir: str | Path | None = None,
    session_id: str | None = None,
    strict_durability: bool = False,
    single_writer: bool = False,
    allow_network_fs: bool = False,
    fan_out_index: bool = True,
) -> dict[str, Any]:
    """Append one ADR-226 v2 event to a per-session stream.

    Slice A implements the minimum substrate: monotonic per-session seq,
    path-safe session streams, default group-commit durability, strict fsync
    opt-in, and a rebuildable counter cache. Fan-out indexes and memoized
    replay are intentionally deferred to later ADR-226 slices.
    """
    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")
    _platform_supported(single_writer=single_writer, allow_network_fs=allow_network_fs)
    root = _root(project_dir)
    sid = _safe_session_id(session_id)
    stream_path = session_stream_path(root, sid)
    counter = session_counter_path(root, sid)

    with _session_locked(root, sid, single_writer=single_writer):
        stream_path.parent.mkdir(parents=True, exist_ok=True)
        next_seq = _max_seq_in_stream(stream_path) + 1
        event = {
            "schema_version": EVENT_STORE_SCHEMA_VERSION,
            "seq": next_seq,
            "session_id": sid,
            "event_type": normalize_event_type(event_type),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timestamp_epoch": time.time(),
            "producer": "orchestrator",
            "pid": os.getpid(),
            "project_dir": str(root),
            "payload": payload or {},
        }
        line = json.dumps(event, sort_keys=True) + "\n"
        try:
            with stream_path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                if strict_durability:
                    os.fsync(handle.fileno())
        except Exception:
            _write_counter(counter, next_seq - 1)
            raise
        _write_counter(counter, next_seq)
        if fan_out_index:
            _append_event_index(root, event, strict_durability=strict_durability)
        return event


def read_session_events(
    session_id: str,
    *,
    project_dir: str | Path | None = None,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Read one ADR-226 per-session stream and fail on schema/seq gaps."""
    path = session_stream_path(project_dir, session_id)
    if not path.is_file():
        return []
    normalized_type = event_type.replace("_", "-") if event_type else None
    events: list[dict[str, Any]] = []
    expected_seq = 1
    for line_number, line in _json_lines(path):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventStreamCorrupt(f"corrupt JSON at {path}:{line_number}") from exc
        if not isinstance(event, dict):
            raise EventStreamCorrupt(f"non-object event at {path}:{line_number}")
        if event.get("schema_version") != EVENT_STORE_SCHEMA_VERSION:
            raise EventStreamCorrupt(f"unexpected schema_version at {path}:{line_number}")
        seq = event.get("seq")
        if seq != expected_seq:
            raise EventStreamGapDetected(
                f"seq gap in {path}: expected {expected_seq}, got {seq!r} at line {line_number}"
            )
        expected_seq += 1
        if normalized_type and event.get("event_type") != normalized_type:
            continue
        events.append(event)
    return events


def recover_session_counter(
    session_id: str,
    *,
    project_dir: str | Path | None = None,
) -> int:
    """Rebuild the counter cache from the stream and return max(seq)."""
    path = session_stream_path(project_dir, session_id)
    max_seq = _max_seq_in_stream(path)
    _write_counter(session_counter_path(project_dir, session_id), max_seq)
    return max_seq


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _current_branch(project_dir: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=str(project_dir),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=1,
        ).strip()
    except Exception:
        return ""


def _dedupe(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def peers(
    *,
    project_dir: str | Path | None = None,
    within_seconds: int = 1800,
    alive_only: bool = True,
    current_session_id: str | None = None,
    limit: int = 200,
) -> list[PeerSummary]:
    """Summarize recently active peer sessions from the append-only event log."""
    root = _root(project_dir)
    now = time.time()
    current = current_session_id or _session_id()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in read_events(project_dir=root, limit=limit):
        sid = str(event.get("session_id") or "unknown")
        if sid in {"", "unknown", current}:
            continue
        ts = float(event.get("timestamp_epoch") or 0)
        if within_seconds > 0 and now - ts > within_seconds:
            continue
        grouped.setdefault(sid, []).append(event)

    summaries: list[PeerSummary] = []
    for sid, events in grouped.items():
        events.sort(key=lambda row: float(row.get("timestamp_epoch") or 0))
        last = events[-1]
        pid = int(last.get("pid") or 0)
        if alive_only and not _pid_alive(pid):
            continue
        branch = ""
        topics: list[str] = []
        writes: list[str] = []
        event_types: list[str] = []
        for event in events:
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            event_types.append(str(event.get("event_type") or ""))
            branch = str(payload.get("branch") or branch)
            if isinstance(payload.get("topic_keywords"), list):
                topics.extend(str(item) for item in payload.get("topic_keywords") if item)
            elif payload.get("topic"):
                topics.append(str(payload.get("topic")))
            path = payload.get("path") or payload.get("file_path") or payload.get("target")
            if path and event.get("event_type") in {"file-write-intent", "commit-intent", "commit-landed"}:
                writes.append(str(path))
        if not branch:
            branch = _current_branch(root)
        summaries.append(
            PeerSummary(
                session_id=sid,
                branch=branch,
                last_seen=float(last.get("timestamp_epoch") or 0),
                pid=pid,
                project_dir=str(last.get("project_dir") or root),
                topic_keywords=_dedupe(list(reversed(topics)), limit=5),
                recent_writes=_dedupe(list(reversed(writes)), limit=5),
                recent_events=_dedupe(list(reversed(event_types)), limit=8),
            )
        )
    summaries.sort(key=lambda item: item.last_seen, reverse=True)
    return summaries
