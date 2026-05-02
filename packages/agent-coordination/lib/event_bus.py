# SCOPE: both
# scope: both
"""
Inter-session pub/sub event bus — P1.3 (ADR-116).

Append-only file-based event bus.  All agents read/write the same
``.cognitive-os/sessions/events.jsonl`` file.  Concurrency safety is
provided by ``fcntl.flock`` (LOCK_EX) which is correct for lines >4 KB
and, crucially, serialises the *read-append* cycle so no two writers
can interleave on the same line.

On POSIX, a single ``write(2)`` call smaller than PIPE_BUF (512 bytes
on Linux / macOS) is atomic, but JSON payloads can grow beyond that, so
we always hold LOCK_EX around the append.

Self-rotation: if the file exceeds the configured size threshold the bus
archives it to ``events-<YYYYMMDD>.jsonl.gz`` before the next emit.
Rotation is best-effort — a failure logs a warning and is never raised.

Schema (one JSON object per line):
    {
        "ts":         "<ISO-8601 with UTC offset>",
        "session_id": "<string>",
        "event_type": "<type from EVENT_TYPES>",
        "payload":    <dict>
    }

Public API
----------
emit(event_type, payload, session_id=None)
    Atomic append.

tail(since_ts=None, since_line=0, follow=False)
    Generator — yields parsed event dicts.

stats(window_seconds=3600)
    Returns Counter of event_type in the last ``window_seconds``.

EVENT_TYPES
    Closed set of allowed event type strings.

Python 3.9+ compatible.
"""

from __future__ import annotations

import fcntl
import gzip
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_TYPES: frozenset[str] = frozenset(
    {
        "claim_acquired",
        "claim_released",
        "task_completed",
        "commit_landed",
        "session_started",
        "session_ended",
        "conflict_detected",
        # P2.2 merge-queue events
        "merge_queued",
        "merge_completed",
        "merge_failed",
    }
)

# Default path relative to project root.  Callers may override via
# ``EVENTS_BUS_PATH`` env var or the ``bus_path`` kwarg.
_DEFAULT_BUS_PATH = ".cognitive-os/sessions/events.jsonl"

# Rotate when the file exceeds this many bytes (default 50 MiB).
_DEFAULT_ROTATION_BYTES: int = 50 * 1024 * 1024


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_bus_path(bus_path: Optional[str | Path] = None) -> Path:
    """Return the absolute path for the events file."""
    if bus_path is not None:
        return Path(bus_path).expanduser().resolve()
    env_path = os.environ.get("EVENTS_BUS_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    # Anchor at the repo root: walk up until we find a .cognitive-os dir or
    # fall back to cwd.
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".cognitive-os").is_dir():
            return candidate / _DEFAULT_BUS_PATH
    return cwd / _DEFAULT_BUS_PATH


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _now_ts() -> float:
    return time.time()


def _parse_ts(ts_str: str) -> float:
    """Parse an ISO-8601 string to a POSIX timestamp.  Returns 0.0 on error."""
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Rotation
# ---------------------------------------------------------------------------


def _rotate(bus_path: Path, rotation_bytes: int) -> None:
    """Archive the current events file if it exceeds the size threshold.

    Best-effort: any exception is logged and swallowed — emit must never block.
    """
    try:
        if not bus_path.exists():
            return
        if bus_path.stat().st_size < rotation_bytes:
            return
        date_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        archive_path = bus_path.with_name(f"events-{date_str}.jsonl.gz")
        # If today's archive already exists append a counter to avoid clobbering.
        counter = 0
        while archive_path.exists():
            counter += 1
            archive_path = bus_path.with_name(f"events-{date_str}-{counter}.jsonl.gz")
        with bus_path.open("rb") as src, gzip.open(archive_path, "wb") as dst:
            dst.write(src.read())
        # Truncate (don't unlink — that would break tailing file descriptors).
        bus_path.write_text("", encoding="utf-8")
        logger.info("event_bus: rotated to %s", archive_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("event_bus: rotation failed (best-effort): %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit(
    event_type: str,
    payload: dict,
    session_id: Optional[str] = None,
    *,
    bus_path: Optional[str | Path] = None,
    rotation_bytes: int = _DEFAULT_ROTATION_BYTES,
) -> None:
    """Append an event to the bus file atomically.

    Parameters
    ----------
    event_type:
        Must be in ``EVENT_TYPES``.
    payload:
        Arbitrary JSON-serialisable dict.
    session_id:
        Defaults to the ``COGNITIVE_OS_SESSION_ID`` env var or ``"unknown"``.
    bus_path:
        Override the bus file location (useful in tests).
    rotation_bytes:
        Rotate the file if it exceeds this size (bytes).  Pass 0 to disable.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(
            f"Unknown event_type {event_type!r}. "
            f"Allowed: {sorted(EVENT_TYPES)}"
        )
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    resolved_session_id = (
        session_id
        or os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("COS_SESSION_ID")
        or "unknown"
    )

    record = {
        "ts": _now_iso(),
        "session_id": resolved_session_id,
        "event_type": event_type,
        "payload": payload,
    }
    line = json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
    encoded = line.encode("utf-8")

    path = _resolve_bus_path(bus_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Rotation check before acquiring the write lock (no TOCTOU risk here
    # because we hold the lock during the actual append).
    if rotation_bytes > 0:
        _rotate(path, rotation_bytes)

    with path.open("ab") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def tail(
    since_ts: Optional[str] = None,
    since_line: int = 0,
    follow: bool = False,
    *,
    bus_path: Optional[str | Path] = None,
    poll_interval: float = 0.1,
) -> Generator[dict, None, None]:
    """Yield events from the bus.

    Parameters
    ----------
    since_ts:
        ISO-8601 timestamp.  Only events with ``ts >= since_ts`` are yielded.
    since_line:
        Skip the first ``since_line`` lines (0-based).  Useful for resuming.
    follow:
        If True, keep polling after the end of the file (like ``tail -f``).
    bus_path:
        Override the bus file location (useful in tests).
    poll_interval:
        Seconds between polls in follow mode.
    """
    since_epoch: float = _parse_ts(since_ts) if since_ts else 0.0
    path = _resolve_bus_path(bus_path)

    if not path.exists():
        if follow:
            while not path.exists():
                time.sleep(poll_interval)
        else:
            return

    line_num = 0
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        while True:
            raw = fh.readline()
            if raw == "":
                if not follow:
                    break
                time.sleep(poll_interval)
                continue

            line_num += 1
            if line_num <= since_line:
                continue

            raw = raw.strip()
            if not raw:
                continue

            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                logger.debug("event_bus: skipping corrupt line %d", line_num)
                continue

            if since_epoch > 0:
                event_ts = _parse_ts(event.get("ts", ""))
                if event_ts < since_epoch:
                    continue

            yield event


def stats(
    window_seconds: float = 3600,
    *,
    bus_path: Optional[str | Path] = None,
) -> Counter:
    """Return a Counter of event_type counts within the last ``window_seconds``.

    Parameters
    ----------
    window_seconds:
        Look-back window in seconds (default: 1 hour).
    bus_path:
        Override the bus file location (useful in tests).
    """
    cutoff = _now_ts() - window_seconds
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    counts: Counter = Counter()
    for event in tail(since_ts=cutoff_iso, bus_path=bus_path):
        et = event.get("event_type", "unknown")
        counts[et] += 1
    return counts
