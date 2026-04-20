"""Process registry — ADR-028 D1.B.

Tracks PIDs spawned by hooks/skills so the reaper can distinguish registered
processes (safe to terminate after TTL) from orphans (logged but not killed
in Phase A).
"""
from __future__ import annotations

import json
import os
import signal
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.metric_event import MetricEvent, append_event

VALID_KINDS = {"short_lived", "detached_daemon"}


def _project_root() -> Path:
    return Path(
        os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR",
            os.environ.get(
                "CLAUDE_PROJECT_DIR",
                str(Path(__file__).resolve().parent.parent),
            ),
        )
    )


def _runtime_dir() -> Path:
    d = _project_root() / ".cognitive-os" / "runtime"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _processes_jsonl() -> Path:
    return _runtime_dir() / "processes.jsonl"


def _processes_live_json() -> Path:
    return _runtime_dir() / "processes-live.json"


@dataclass
class ProcessRecord:
    pid: int
    owner: str
    ttl_seconds: int
    kind: str
    registered_at: float = field(default_factory=time.time)

    def expires_at(self) -> float:
        return self.registered_at + self.ttl_seconds

    def is_expired(self, now: Optional[float] = None) -> bool:
        return (now if now is not None else time.time()) >= self.expires_at()


def _load_live() -> List[ProcessRecord]:
    p = _processes_live_json()
    if not p.is_file():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [ProcessRecord(**r) for r in raw if isinstance(r, dict)]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def _save_live(records: List[ProcessRecord]) -> None:
    """Atomic overwrite: write to .tmp, fsync fd, os.replace."""
    p = _processes_live_json()
    tmp = p.with_suffix(".json.tmp")
    data = [asdict(r) for r in records]
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # fsync the tmp file before rename so the data survives a crash
    fd = os.open(str(tmp), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(p))


def _append_process_event(event_type: str, record: ProcessRecord) -> None:
    event = MetricEvent(
        source="process_registry",
        event_type=event_type,
        payload=asdict(record),
    )
    append_event(str(_processes_jsonl()), event)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register(pid: int, owner: str, ttl_seconds: int, kind: str) -> ProcessRecord:
    """Register a PID in the live registry.

    Raises ValueError if *kind* is not in VALID_KINDS.
    Deduplicates: if the same PID is already registered, the previous record
    is replaced.
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}; got {kind!r}")
    rec = ProcessRecord(
        pid=int(pid),
        owner=str(owner),
        ttl_seconds=int(ttl_seconds),
        kind=kind,
    )
    live = _load_live()
    # Replace any existing record for this PID
    live = [r for r in live if r.pid != rec.pid]
    live.append(rec)
    _save_live(live)
    _append_process_event("process.registered", rec)
    return rec


def deregister(pid: int) -> bool:
    """Remove a PID from the live registry.  Returns True if it was present."""
    live = _load_live()
    before = len(live)
    kept = [r for r in live if r.pid != pid]
    if len(kept) == before:
        return False
    _save_live(kept)
    # Emit a minimal deregistered event (we may no longer have the full record)
    synth = ProcessRecord(pid=int(pid), owner="", ttl_seconds=0, kind="short_lived")
    _append_process_event("process.deregistered", synth)
    return True


def list_live() -> List[ProcessRecord]:
    """Return the current snapshot of registered processes."""
    return _load_live()


def cleanup_expired(dry_run: bool = False) -> List[ProcessRecord]:
    """Return and (unless *dry_run*) terminate expired short_lived records.

    Policy:
      - Only ``short_lived`` records are eligible — ``detached_daemon`` is
        never auto-killed.
      - SIGTERM first; 10 s grace; SIGKILL survivors.
      - Refuses to signal anything not in the registry (safe-kill).
    """
    live = _load_live()
    now = time.time()
    # detached_daemon processes are whitelisted — never auto-killed
    expired = [r for r in live if r.kind == "short_lived" and r.is_expired(now)]

    if dry_run:
        return expired

    survivors: List[ProcessRecord] = []
    for rec in expired:
        _terminate_with_grace(rec.pid)
        if _is_alive(rec.pid):
            survivors.append(rec)

    # Remove all expired records from registry regardless of kill outcome;
    # surviving processes will re-surface as orphans on the next reaper run.
    kept = [r for r in live if r not in expired]
    _save_live(kept)

    for rec in expired:
        _append_process_event("process.reaped", rec)

    for rec in survivors:
        event = MetricEvent(
            source="process_registry",
            event_type="process.reap_failed",
            severity="warn",
            payload=asdict(rec),
        )
        append_event(str(_processes_jsonl()), event)

    return expired


def detect_orphans(hook_basenames: List[str]) -> List[Dict[str, Any]]:
    """Scan ``ps`` output for hook processes that are NOT in the live registry.

    Phase A policy: logs ``orphan_detected`` MetricEvents but does NOT kill.
    Auto-kill is gated behind ``runtime.reaper.autokill_orphans: true``.

    Args:
        hook_basenames: Substrings to match against process command strings
            (typically hook filenames, e.g. ``["session-end-reap.sh"]``).

    Returns:
        List of ``{pid, ppid, command}`` dicts for every detected orphan.
    """
    import subprocess  # noqa: PLC0415 — lazy import to keep module light

    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,ppid,command"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    registered_pids = {r.pid for r in _load_live()}
    orphans: List[Dict[str, Any]] = []

    for line in result.stdout.splitlines()[1:]:
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        command = parts[2]

        if any(b in command for b in hook_basenames) and pid not in registered_pids:
            orphans.append({"pid": pid, "ppid": ppid, "command": command})
            event = MetricEvent(
                source="process_registry",
                event_type="orphan_detected",
                severity="warn",
                payload={"pid": pid, "ppid": ppid, "command": command[:200]},
            )
            append_event(str(_processes_jsonl()), event)

    return orphans


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _terminate_with_grace(pid: int, grace_seconds: float = 10.0) -> None:
    """Send SIGTERM; wait up to *grace_seconds*; SIGKILL if still alive."""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return

    deadline = time.time() + grace_seconds
    while time.time() < deadline:
        if not _is_alive(pid):
            return
        time.sleep(0.5)

    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _is_alive(pid: int) -> bool:
    """Return True if the process exists (signal 0 probe)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — treat as alive.
        return True
    return True
