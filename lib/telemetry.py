# SCOPE: both
"""Telemetry for COS observability (Capa-4).

Minimal, file-based telemetry that records runtime events to append-only JSONL
files under ``.cognitive-os/metrics/``. Four event classes are supported:

- Skill invocations   → ``skill-usage.jsonl``
- Hook firings        → ``hook-usage.jsonl``
- Agent launches      → ``agent-launches.jsonl``
- Rate-limit events   → ``rate-limit-events.jsonl``

Design constraints (HALT triggers from the sprint brief):

- No external DB. Pure stdlib, JSONL only.
- Each ``record_*`` call is fast (<5 ms typical) and best-effort (never raises).
- Auto-rotation at ``MAX_BYTES`` (10 MB default): the current file is renamed
  to ``<stem>.<UTC-timestamp>.jsonl`` and a fresh file is started.

This module is intentionally small so it can be imported cheaply from hooks
and scripts. See ``docs/04-Concepts/architecture/functional-audit/sprint-5-observability.md``
for the aggregation/analysis layer.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from lib.metric_event import MetricEvent, append_event as _me_append_event

# ─── Configuration ───────────────────────────────────────────────────────────

#: Default size threshold that triggers rotation (bytes). Override with env
#: ``COS_TELEMETRY_MAX_BYTES`` if you need to test rotation on a smaller file.
MAX_BYTES: int = int(os.environ.get("COS_TELEMETRY_MAX_BYTES", 10 * 1024 * 1024))

#: Subdirectory (relative to the project root) where JSONL files live.
_METRICS_SUBDIR = Path(".cognitive-os") / "metrics"

# Public filenames — referenced by the aggregator scripts.
SKILL_USAGE_FILE = "skill-usage.jsonl"
HOOK_USAGE_FILE = "hook-usage.jsonl"
AGENT_LAUNCHES_FILE = "agent-launches.jsonl"
RATE_LIMIT_FILE = "rate-limit-events.jsonl"


# ─── Core helpers ────────────────────────────────────────────────────────────


def _project_root() -> Path:
    """Resolve the project root.

    Priority: ``COGNITIVE_OS_PROJECT_DIR`` → ``CLAUDE_PROJECT_DIR`` → cwd.
    We deliberately do NOT call ``git rev-parse`` here — telemetry must remain
    cheap, and hooks already set one of the env vars.

    NOTE: custom resolution — differs from lib.paths.project_root() (Pattern D).
    See tests/unit/test_project_dir_resolution.py for rationale.
    """
    return Path(
        os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )


def _metrics_dir() -> Path:
    root = _project_root() / _METRICS_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utc_iso() -> str:
    """Return current UTC timestamp in ISO-8601 with trailing ``Z``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _rotate_if_needed(path: Path) -> None:
    """Rotate ``path`` if it exceeds ``MAX_BYTES``.

    Rotation renames to ``<stem>.<utc-ts-with-microseconds>.jsonl``. If that
    target already exists (e.g. two writers rotated in the same microsecond),
    a numeric suffix is appended. Failures are swallowed — telemetry must
    never break the caller.
    """
    try:
        if not path.exists():
            return
        if path.stat().st_size < MAX_BYTES:
            return
        # Microsecond precision prevents collisions on rapid rotations.
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        rotated = path.with_name(f"{path.stem}.{ts}{path.suffix}")
        # Collision-safe fallback: bump a counter until we find a free name.
        i = 0
        while rotated.exists():
            i += 1
            rotated = path.with_name(f"{path.stem}.{ts}-{i}{path.suffix}")
        path.rename(rotated)
    except Exception:
        # Best-effort — never raise from telemetry.
        pass


def _append(filename: str, payload: Dict[str, Any]) -> Optional[Path]:
    """Append one JSON object as a MetricEvent line. Returns the path written, or None on error."""
    try:
        target = _metrics_dir() / filename
        _rotate_if_needed(target)
        record = dict(payload)
        # Extract or generate timestamp (MetricEvent handles it if empty)
        timestamp = record.pop("timestamp", _utc_iso())
        # Use the 'event' field as event_type suffix; keep it in payload for readers
        event_label = record.get("event", filename.replace(".jsonl", ""))
        # Determine source from filename stem
        source = Path(filename).stem
        event = MetricEvent(
            source=source,
            event_type=f"telemetry.{event_label}",
            payload=record,
            timestamp=timestamp,
        )
        return target if _me_append_event(str(target), event) else None
    except Exception:
        return None


# ─── Public recording API ────────────────────────────────────────────────────


def record_skill_invocation(
    name: str,
    duration_ms: Optional[float] = None,
    tokens_estimated: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Record a single skill invocation.

    Parameters
    ----------
    name
        The skill's identifier (e.g. ``"compose-prompt"``). Required.
    duration_ms
        Wall-clock duration of the invocation, in milliseconds. Optional.
    tokens_estimated
        Rough token footprint of the invocation. Optional.
    extra
        Additional free-form fields merged into the JSONL record.
    """
    record: Dict[str, Any] = {
        "event": "skill_invocation",
        "name": str(name),
    }
    if duration_ms is not None:
        record["duration_ms"] = float(duration_ms)
    if tokens_estimated is not None:
        record["tokens_estimated"] = int(tokens_estimated)
    if extra:
        record.update(extra)
    return _append(SKILL_USAGE_FILE, record)


def record_hook_fired(
    name: str,
    event_type: str,
    duration_ms: Optional[float] = None,
    decision: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Record a hook firing.

    Parameters
    ----------
    name
        Hook identifier (usually the basename without ``.sh``).
    event_type
        Claude hook event (``PreToolUse``, ``PostToolUse``, ``Stop``, etc.).
    duration_ms
        Measured wall-clock duration, in milliseconds.
    decision
        Optional decision string (``allow``, ``block``, ``warn``, ``noop``).
    """
    record: Dict[str, Any] = {
        "event": "hook_fired",
        "name": str(name),
        "event_type": str(event_type),
    }
    if duration_ms is not None:
        record["duration_ms"] = float(duration_ms)
    if decision is not None:
        record["decision"] = str(decision)
    if extra:
        record.update(extra)
    return _append(HOOK_USAGE_FILE, record)


def record_agent_launch(
    description: str,
    model: str,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost_estimated: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Record an agent (sub-agent / delegate) launch.

    ``cost_estimated`` is in USD. ``tokens_in`` / ``tokens_out`` are raw counts.
    """
    record: Dict[str, Any] = {
        "event": "agent_launch",
        "description": str(description),
        "model": str(model),
    }
    if tokens_in is not None:
        record["tokens_in"] = int(tokens_in)
    if tokens_out is not None:
        record["tokens_out"] = int(tokens_out)
    if cost_estimated is not None:
        record["cost_estimated"] = float(cost_estimated)
    if extra:
        record.update(extra)
    return _append(AGENT_LAUNCHES_FILE, record)


def record_rate_limit_event(
    type: str,
    queue_depth: Optional[int] = None,
    delay_s: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """Record a rate-limit-adjacent event (queued, throttled, recovered).

    ``type`` is a short label like ``queued``, ``throttled``, ``rejected``,
    ``recovered``. ``queue_depth`` is the observed queue length. ``delay_s``
    is the delay in seconds experienced (or injected).
    """
    record: Dict[str, Any] = {
        "event": "rate_limit_event",
        "type": str(type),
    }
    if queue_depth is not None:
        record["queue_depth"] = int(queue_depth)
    if delay_s is not None:
        record["delay_s"] = float(delay_s)
    if extra:
        record.update(extra)
    return _append(RATE_LIMIT_FILE, record)


# ─── Minimal read API (used by the aggregator) ───────────────────────────────


def iter_records(filename: str):
    """Yield parsed JSON records from a telemetry file (and rotated siblings).

    Silently skips unparseable lines and missing files. The scan is limited to
    the metrics dir; rotated files are globbed by stem.

    MetricEvent-wrapped rows are transparently unwrapped so consumers receive
    the same flat dict shape as legacy rows.
    """
    directory = _metrics_dir()
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".jsonl"
    # Current file first, then rotated ones (stable sort by name → chronological).
    candidates = []
    current = directory / filename
    if current.exists():
        candidates.append(current)
    candidates.extend(sorted(directory.glob(f"{stem}.*{suffix}")))
    for path in candidates:
        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # Unwrap MetricEvent rows back to flat shape
                    if "schema_version" in row and "event_type" in row and "payload" in row:
                        flat = dict(row["payload"])
                        flat.setdefault("timestamp", row.get("timestamp", ""))
                        yield flat
                    else:
                        yield row
        except OSError:
            continue


def metrics_dir() -> Path:
    """Expose the current metrics directory (useful for scripts/tests)."""
    return _metrics_dir()


__all__ = [
    "MAX_BYTES",
    "SKILL_USAGE_FILE",
    "HOOK_USAGE_FILE",
    "AGENT_LAUNCHES_FILE",
    "RATE_LIMIT_FILE",
    "record_skill_invocation",
    "record_hook_fired",
    "record_agent_launch",
    "record_rate_limit_event",
    "iter_records",
    "metrics_dir",
]
