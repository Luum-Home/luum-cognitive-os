"""session_watchdog_lib.py — shared utilities for so-session-watchdog.py.

Extracted here so the daemon script stays thin and so tests can import
logic without spawning a subprocess.

SCOPE: both
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Command-line signature fragments that identify a Claude Code main process.
# Matches the heuristic in scripts/session-leak-diagnostic.sh.
SESSION_SIGNATURE_REQUIRED = ["--output-format stream-json", "--input-format stream-json"]
SESSION_SIGNATURE_EXCLUDE = ["disclaimer"]

ENGRAM_MCP_SIGNATURE = "engram mcp --tools=agent"

# Classification buckets
CLASS_HEALTHY = "HEALTHY"
CLASS_IDLE_OVER_TTL = "IDLE_OVER_TTL"
CLASS_ORPHANED = "ORPHANED"
CLASS_RESUMED_RECENTLY = "RESUMED_RECENTLY"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProcessInfo:
    """Minimal cross-platform process snapshot."""
    pid: int
    ppid: int
    etime_sec: int          # elapsed wall-clock seconds
    cpu_percent: float
    command: str            # full argv string, may be truncated
    start_time_epoch: float = 0.0  # best-effort; 0 if unavailable


@dataclass
class SessionRecord:
    """Enriched snapshot of one candidate Claude session."""
    pid: int
    ppid: int
    etime_sec: int
    cpu_percent: float
    command: str
    start_time_epoch: float
    resume_id: Optional[str]
    engram_mcp_children: List[int]


@dataclass
class WatchdogRecord:
    """One JSONL row written to session-watchdog.jsonl."""
    timestamp: str
    scan_id: str
    session_pid: int
    session_etime_sec: int
    classification: str
    would_kill: bool
    reason: str
    resume_id: Optional[str]
    engram_mcp_children: List[int]
    cpu_percent: float
    ttl_hours_configured: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Process enumeration — psutil path
# ---------------------------------------------------------------------------

def _try_import_psutil() -> Any:
    try:
        import psutil  # type: ignore
        return psutil
    except ImportError:
        return None


def _enumerate_via_psutil(psutil: Any) -> Tuple[List[ProcessInfo], List[ProcessInfo]]:
    """Return (claude_sessions, engram_mcp_procs) using psutil."""
    sessions: List[ProcessInfo] = []
    engram_procs: List[ProcessInfo] = []
    now = time.time()

    for proc in psutil.process_iter(["pid", "ppid", "create_time", "cpu_percent", "cmdline"]):
        try:
            info = proc.info
            cmdline = info.get("cmdline") or []
            cmd_str = " ".join(cmdline)
            pid = info["pid"]
            ppid = info.get("ppid", 0) or 0
            create_time = info.get("create_time", 0) or 0.0
            etime_sec = max(0, int(now - create_time)) if create_time else 0
            # psutil cpu_percent on first call returns 0.0 per process — acceptable
            cpu = info.get("cpu_percent") or 0.0

            proc_info = ProcessInfo(
                pid=pid,
                ppid=ppid,
                etime_sec=etime_sec,
                cpu_percent=cpu,
                command=cmd_str[:512],
                start_time_epoch=create_time,
            )

            if _is_claude_session(cmd_str):
                sessions.append(proc_info)
            elif ENGRAM_MCP_SIGNATURE in cmd_str:
                engram_procs.append(proc_info)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return sessions, engram_procs


# ---------------------------------------------------------------------------
# Process enumeration — ps fallback
# ---------------------------------------------------------------------------

def _etime_to_seconds(etime: str) -> int:
    """Parse ps etime field: [[DD-]HH:]MM:SS → seconds."""
    try:
        s = etime.strip()
        days = 0
        if "-" in s:
            d, s = s.split("-", 1)
            days = int(d)
        parts = [int(p) for p in s.split(":")]
        while len(parts) < 3:
            parts = [0] + parts
        h, m, sec = parts
        return days * 86400 + h * 3600 + m * 60 + sec
    except (ValueError, AttributeError):
        return 0


def _enumerate_via_ps() -> Tuple[List[ProcessInfo], List[ProcessInfo]]:
    """Return (claude_sessions, engram_mcp_procs) using ps -eo (POSIX)."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,ppid,etime,pcpu,command"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return [], []

    if result.returncode != 0:
        return [], []

    sessions: List[ProcessInfo] = []
    engram_procs: List[ProcessInfo] = []

    for line in result.stdout.splitlines()[1:]:  # skip header
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            etime_str = parts[2]
            cpu = float(parts[3])
            cmd_str = parts[4]
        except (ValueError, IndexError):
            continue

        etime_sec = _etime_to_seconds(etime_str)
        proc_info = ProcessInfo(
            pid=pid,
            ppid=ppid,
            etime_sec=etime_sec,
            cpu_percent=cpu,
            command=cmd_str[:512],
            start_time_epoch=0.0,  # not available from ps etime alone
        )

        if _is_claude_session(cmd_str):
            sessions.append(proc_info)
        elif ENGRAM_MCP_SIGNATURE in cmd_str:
            engram_procs.append(proc_info)

    return sessions, engram_procs


# ---------------------------------------------------------------------------
# Signature matching
# ---------------------------------------------------------------------------

def _is_claude_session(cmd_str: str) -> bool:
    """True iff the command looks like a Claude Code main process."""
    for sig in SESSION_SIGNATURE_REQUIRED:
        if sig not in cmd_str:
            return False
    for excl in SESSION_SIGNATURE_EXCLUDE:
        if excl in cmd_str:
            return False
    return True


def _extract_resume_id(cmd_str: str) -> Optional[str]:
    """Extract --resume <uuid> from a command string, or None."""
    import re
    m = re.search(r"--resume\s+([a-f0-9-]{32,})", cmd_str)
    return m.group(1) if m else None


def _pid_exists(pid: int) -> bool:
    """Return True if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but we can't signal


# ---------------------------------------------------------------------------
# Session enrichment
# ---------------------------------------------------------------------------

def enrich_session(
    proc: ProcessInfo,
    engram_procs: List[ProcessInfo],
) -> SessionRecord:
    """Add resume_id and engram_mcp_children to a raw ProcessInfo."""
    resume_id = _extract_resume_id(proc.command)
    children = [e.pid for e in engram_procs if e.ppid == proc.pid]
    return SessionRecord(
        pid=proc.pid,
        ppid=proc.ppid,
        etime_sec=proc.etime_sec,
        cpu_percent=proc.cpu_percent,
        command=proc.command,
        start_time_epoch=proc.start_time_epoch,
        resume_id=resume_id,
        engram_mcp_children=children,
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_session(
    session: SessionRecord,
    ttl_sec: int,
    idle_cpu_threshold: float,
    # idle_samples_required is not enforced per-call (daemon handles samples);
    # here we treat cpu_percent as the single-sample proxy for one-shot mode.
) -> Tuple[str, str, bool]:
    """Return (classification, reason, would_kill).

    Rules (evaluated in order, matching ADR-047):
      ORPHANED       — ppid dead (parent process gone)
      RESUMED_RECENTLY — has --resume flag (higher TTL tolerance; never kill)
      IDLE_OVER_TTL  — etime > ttl AND cpu below threshold
      HEALTHY        — everything else
    """
    # R4: orphaned parent
    if not _pid_exists(session.ppid):
        return (
            CLASS_ORPHANED,
            f"parent_pid_{session.ppid}_dead",
            False,  # Phase A: never kill
        )

    # RESUMED_RECENTLY: has resume flag — treat with higher TTL tolerance
    if session.resume_id is not None:
        # Resumed sessions get 2× TTL tolerance per ADR-047
        effective_ttl = ttl_sec * 2
        if session.etime_sec > effective_ttl and session.cpu_percent < idle_cpu_threshold:
            return (
                CLASS_RESUMED_RECENTLY,
                f"resumed_session_over_2x_ttl_etime={session.etime_sec}s",
                False,
            )
        return (CLASS_HEALTHY, "resumed_session_within_extended_ttl", False)

    # R1+R2: idle over TTL
    if session.etime_sec > ttl_sec and session.cpu_percent < idle_cpu_threshold:
        return (
            CLASS_IDLE_OVER_TTL,
            f"etime={session.etime_sec}s_exceeds_ttl={ttl_sec}s_cpu={session.cpu_percent:.1f}%",
            True,  # would_kill=True in Phase B; Phase A still logs only
        )

    return (CLASS_HEALTHY, f"etime={session.etime_sec}s_ttl={ttl_sec}s_cpu={session.cpu_percent:.1f}%", False)


# ---------------------------------------------------------------------------
# ADR-047 Phase B: Layered liveness predicate
# ---------------------------------------------------------------------------

# Default dry-run: SO_WATCHDOG_DRY_RUN=1 (true by default in Phase A).
# Set SO_WATCHDOG_DRY_RUN=0 to enable actual kills in Phase B.
_DRY_RUN_DEFAULT = "1"

# Thresholds (seconds)
_HEARTBEAT_STALE_THRESHOLD_S = 15 * 60   # 15 minutes
_METRIC_STALE_THRESHOLD_S = 5 * 60       # 5 minutes
_CPU_SAMPLE_COUNT = 3
_CPU_SAMPLE_WINDOW_S = 30
_CPU_IDLE_THRESHOLD_PCT = 5.0


def _heartbeat_stale(session_dir: Path, threshold_s: int = _HEARTBEAT_STALE_THRESHOLD_S) -> bool:
    """Return True if the heartbeat file is older than threshold_s, or does not exist.

    The heartbeat file is written by hooks/session-heartbeat.sh on every
    UserPromptSubmit and PreToolUse event.
    """
    hb_file = session_dir / "heartbeat"
    if not hb_file.exists():
        return True  # Missing file = treated as stale (ADR-047 spec)
    try:
        age_s = time.time() - hb_file.stat().st_mtime
        return age_s > threshold_s
    except OSError:
        return True


def _metric_writes_stale(threshold_s: int = _METRIC_STALE_THRESHOLD_S) -> bool:
    """Return True if no metrics JSONL was written recently.

    Looks at all .cognitive-os/metrics/*.jsonl files relative to CWD.
    Defense-in-depth: if heartbeat hook fails, other hooks still write metrics.
    """
    pattern = ".cognitive-os/metrics/*.jsonl"
    files = glob.glob(pattern)
    if not files:
        return True
    try:
        newest_mtime = max(os.path.getmtime(f) for f in files)
        age_s = time.time() - newest_mtime
        return age_s > threshold_s
    except OSError:
        return True


def _cpu_idle_sustained(
    pid: int,
    samples: int = _CPU_SAMPLE_COUNT,
    window_s: float = _CPU_SAMPLE_WINDOW_S,
    threshold_pct: float = _CPU_IDLE_THRESHOLD_PCT,
) -> bool:
    """Return True only if all CPU samples are below threshold_pct.

    Critical guard: an Opus reasoning loop may go minutes without tool calls
    but still burn CPU. If ANY sample is above threshold, bail early (not idle).

    Falls back gracefully if psutil is unavailable — returns False (assume active).
    """
    psutil = _try_import_psutil()
    if psutil is None:
        return False  # Can't measure → assume active → do NOT kill

    try:
        proc = psutil.Process(pid)
        interval = window_s / max(samples, 1)
        for i in range(samples):
            cpu = proc.cpu_percent(interval=interval)
            if cpu > threshold_pct:
                return False  # Bail early — session is active
        return True  # All samples below threshold
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        return False  # Can't measure → assume active → do NOT kill


def _append_decision_jsonl(
    decisions_path: Path,
    session_id: str,
    check: str,
    value: Any,
    verdict: str,
) -> None:
    """Emit one debug line to watchdog-decisions.jsonl."""
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": session_id,
        "check": check,
        "value": value,
        "verdict": verdict,
    }
    try:
        append_jsonl(decisions_path, record)
    except Exception:  # noqa: BLE001
        pass  # Decision logging must never block


def should_kill(
    session_dir: Path,
    ttl_seconds: int,
    pid: Optional[int] = None,
    ppid: Optional[int] = None,
    dry_run: Optional[bool] = None,
    decisions_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """ADR-047 Phase B layered kill predicate.

    Evaluates the AND/OR predicate:

        should_kill(session) =
          parent_dead_or_orphaned(session)
          OR
          (ttl_exceeded(session) AND all_activity_stale(session))

        all_activity_stale(session) =
            heartbeat_stale(session, threshold=15min)
          AND metric_writes_stale(threshold=5min)
          AND cpu_idle_sustained(samples=3, window_s=30, threshold_pct=5.0)

    Parameters
    ----------
    session_dir:
        Path to .cognitive-os/sessions/{session_id}/. Used to find heartbeat file.
    ttl_seconds:
        Session age in seconds beyond which TTL is exceeded.
    pid:
        Main claude process PID (for CPU sampling).
    ppid:
        Parent PID (for orphan check). If None, orphan check is skipped.
    dry_run:
        If True (default from SO_WATCHDOG_DRY_RUN env var), never actually kills.
        Caller is responsible for acting on the returned bool.
    decisions_path:
        Optional path for per-check JSONL debug logging.

    Returns
    -------
    (kill_verdict: bool, reason: str)
        kill_verdict is True when the predicate says the session should be killed.
        In Phase A / dry_run=True, the CALLER must not act on kill_verdict=True.
    """
    if dry_run is None:
        dry_run = os.environ.get("SO_WATCHDOG_DRY_RUN", _DRY_RUN_DEFAULT).strip() != "0"

    session_id = session_dir.name if session_dir else "unknown"

    def _log(check: str, value: Any, verdict: str) -> None:
        if decisions_path:
            _append_decision_jsonl(decisions_path, session_id, check, value, verdict)

    # ── Check 1: parent_dead_or_orphaned ──────────────────────────────────────
    # POSIX kill -0: ProcessLookupError → dead; PermissionError → alive.
    # Short-circuit: if parent is dead, the session is orphaned regardless of TTL.
    if ppid is not None:
        parent_alive = _pid_exists(ppid)
        verdict_1 = "alive" if parent_alive else "dead"
        _log("parent_dead_or_orphaned", ppid, verdict_1)
        if not parent_alive:
            return (True, f"parent_pid_{ppid}_dead_orphaned")

    # ── Check 2: TTL exceeded ─────────────────────────────────────────────────
    session_age_s = 0.0
    hb_file = session_dir / "heartbeat" if session_dir else None
    # Derive session age from heartbeat file creation time or directory mtime as proxy.
    # If we have a start_time passed externally we'd use it; here we approximate.
    # TTL check: we need start time. Best proxy is session dir creation time.
    if session_dir and session_dir.exists():
        try:
            # Use directory mtime as a proxy for session start if no better signal
            session_age_s = time.time() - session_dir.stat().st_ctime
        except OSError:
            session_age_s = 0.0

    ttl_exceeded = session_age_s > ttl_seconds
    _log("ttl_exceeded", {"age_s": round(session_age_s, 1), "ttl_s": ttl_seconds}, "exceeded" if ttl_exceeded else "within")

    if not ttl_exceeded:
        return (False, f"ttl_within_budget_age={round(session_age_s)}s")

    # ── Check 3: all_activity_stale ───────────────────────────────────────────
    # Only evaluated if TTL exceeded.

    # Check 3a: heartbeat freshness (PRIMARY)
    hb_stale = _heartbeat_stale(session_dir) if session_dir else True
    _log("heartbeat_stale", str(hb_file), "stale" if hb_stale else "fresh")
    if not hb_stale:
        return (False, "heartbeat_fresh_session_active")

    # Check 3b: metric writes freshness (SECONDARY)
    metrics_stale = _metric_writes_stale()
    _log("metric_writes_stale", ".cognitive-os/metrics/*.jsonl", "stale" if metrics_stale else "fresh")
    if not metrics_stale:
        return (False, "metric_writes_fresh_session_active")

    # Check 3c: CPU idle (TERTIARY) — only if PID provided
    if pid is not None:
        cpu_idle = _cpu_idle_sustained(pid)
        _log("cpu_idle_sustained", pid, "idle" if cpu_idle else "active")
        if not cpu_idle:
            return (False, "cpu_active_reasoning_loop_protected")

    # All checks pass → session should be killed
    return (True, f"ttl_exceeded_age={round(session_age_s)}s_all_activity_stale")


# ---------------------------------------------------------------------------
# JSONL writer
# ---------------------------------------------------------------------------

def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    """Append one JSON line to a JSONL file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# ADR-047 Phase B gate metric — false-positive rate computation
# ---------------------------------------------------------------------------

# Gate thresholds (from ADR-047 §"Gate threshold")
GATE_FP_RATE_MAX = 0.01        # < 1 %
GATE_MIN_SAMPLE = 50           # minimum flagged detections (distinct events)
GATE_MIN_OBSERVATION_HOURS = 336  # 2 weeks, per ADR-047 Phase A window


@dataclass
class GateMetric:
    """Result of computing the Phase A → Phase B gate metric."""
    total_records: int
    distinct_flagged_pids: int
    flagged_records: int
    resumed_within_24h: int      # false positives — sessions that showed recovery
    stayed_idle: int             # true positives — would have been killed cleanly
    fp_rate: float               # resumed_within_24h / flagged_records
    observation_span_hours: float
    sample_size_ok: bool
    fp_rate_ok: bool
    observation_span_ok: bool
    gate_passes: bool            # ALL three must be True
    evidence_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _parse_watchdog_ts(s: str) -> float:
    """Parse ISO-8601 Z timestamp → epoch seconds. Returns 0 on failure."""
    try:
        import datetime
        dt = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=datetime.timezone.utc).timestamp()
    except (ValueError, TypeError):
        return 0.0


def compute_gate_metric(records: List[Dict[str, Any]]) -> GateMetric:
    """Compute Phase A → Phase B gate per ADR-047.

    A session flagged with would_kill=True is considered a FALSE POSITIVE if,
    within 24h after the flag, that PID re-appears with classification=HEALTHY
    or cpu_percent > 0 (i.e. the session was actually alive/resumed — the
    Phase A classifier mis-flagged it).

    Returns a GateMetric. gate_passes is True only if:
      - fp_rate < GATE_FP_RATE_MAX
      - distinct flagged records >= GATE_MIN_SAMPLE
      - observation span covers >= GATE_MIN_OBSERVATION_HOURS

    This function is pure — no I/O. Caller is responsible for loading JSONL.
    """
    if not records:
        return GateMetric(
            total_records=0,
            distinct_flagged_pids=0,
            flagged_records=0,
            resumed_within_24h=0,
            stayed_idle=0,
            fp_rate=0.0,
            observation_span_hours=0.0,
            sample_size_ok=False,
            fp_rate_ok=False,
            observation_span_ok=False,
            gate_passes=False,
            evidence_summary="no_records",
        )

    # Group by PID
    by_pid: Dict[int, List[Dict[str, Any]]] = {}
    for r in records:
        pid = r.get("session_pid")
        if pid is None:
            continue
        by_pid.setdefault(pid, []).append(r)

    flagged_pids: List[int] = []
    for pid, events in by_pid.items():
        if any(e.get("would_kill") for e in events):
            flagged_pids.append(pid)

    flagged_records = sum(1 for r in records if r.get("would_kill"))

    fp = 0
    tp = 0
    for pid in flagged_pids:
        events = sorted(by_pid[pid], key=lambda r: r.get("timestamp", ""))
        first_flag = next(e for e in events if e.get("would_kill"))
        flag_ts = _parse_watchdog_ts(first_flag.get("timestamp", ""))
        if flag_ts == 0.0:
            continue
        resumed = False
        for e in events:
            ts = _parse_watchdog_ts(e.get("timestamp", ""))
            if ts <= flag_ts:
                continue
            if ts - flag_ts > 86400:
                break
            # Recovery = HEALTHY classification OR measurable CPU activity
            if e.get("classification") == "HEALTHY" or (e.get("cpu_percent") or 0) > 0:
                resumed = True
                break
        if resumed:
            fp += 1
        else:
            tp += 1

    total_flag = fp + tp
    fp_rate = (fp / total_flag) if total_flag else 0.0

    # Observation span
    stamps = sorted(_parse_watchdog_ts(r.get("timestamp", "")) for r in records)
    stamps = [s for s in stamps if s > 0]
    span_hours = ((stamps[-1] - stamps[0]) / 3600.0) if len(stamps) >= 2 else 0.0

    sample_size_ok = total_flag >= GATE_MIN_SAMPLE
    fp_rate_ok = (total_flag > 0) and (fp_rate < GATE_FP_RATE_MAX)
    span_ok = span_hours >= GATE_MIN_OBSERVATION_HOURS
    gate_passes = sample_size_ok and fp_rate_ok and span_ok

    if gate_passes:
        summary = f"GATE_PASS: fp_rate={fp_rate*100:.2f}% sample={total_flag} span={span_hours:.1f}h"
    else:
        reasons = []
        if not sample_size_ok:
            reasons.append(f"sample={total_flag}<{GATE_MIN_SAMPLE}")
        if not fp_rate_ok:
            reasons.append(f"fp_rate={fp_rate*100:.2f}%>={GATE_FP_RATE_MAX*100:.2f}%")
        if not span_ok:
            reasons.append(f"span={span_hours:.1f}h<{GATE_MIN_OBSERVATION_HOURS}h")
        summary = "GATE_FAIL: " + ", ".join(reasons)

    return GateMetric(
        total_records=len(records),
        distinct_flagged_pids=len(flagged_pids),
        flagged_records=flagged_records,
        resumed_within_24h=fp,
        stayed_idle=tp,
        fp_rate=fp_rate,
        observation_span_hours=span_hours,
        sample_size_ok=sample_size_ok,
        fp_rate_ok=fp_rate_ok,
        observation_span_ok=span_ok,
        gate_passes=gate_passes,
        evidence_summary=summary,
    )


def load_watchdog_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load a session-watchdog.jsonl file, ignoring malformed lines."""
    if not path.is_file():
        return []
    records: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return records


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_watchdog_config(project_root: Path) -> Dict[str, Any]:
    """Read runtime.session_watchdog section from cognitive-os.yaml.

    Returns a dict with all keys guaranteed present (defaults applied).
    Never raises — returns defaults on any parse error.
    """
    defaults: Dict[str, Any] = {
        "enabled": True,
        "mode": "log-only",
        "ttl_hours": 6.0,
        # Unified with Phase B kill-guard (_CPU_IDLE_THRESHOLD_PCT). Invariant:
        # Phase A classifier threshold MUST be >= Phase B kill threshold, so the
        # set of sessions Phase A logs as would_kill is a SUPERSET of the set
        # Phase B will actually kill. Tested by test_phase_a_threshold_superset_of_phase_b.
        "idle_cpu_threshold": 5.0,
        "idle_samples_required": 3,
    }

    yaml_path = project_root / "cognitive-os.yaml"
    if not yaml_path.is_file():
        return defaults

    try:
        # Avoid full PyYAML dependency; use a simple key-path extractor.
        import yaml  # type: ignore
        with yaml_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        section = data.get("runtime", {}).get("session_watchdog", {}) or {}
        for k, v in defaults.items():
            if k not in section:
                section[k] = v
        return section
    except Exception:
        # yaml not installed or parse error — fall back to defaults
        pass

    # Manual fallback: grep for the keys we need
    try:
        text = yaml_path.read_text(encoding="utf-8")
        result = dict(defaults)
        for line in text.splitlines():
            stripped = line.strip()
            for key in defaults:
                if stripped.startswith(key + ":"):
                    raw = stripped[len(key) + 1:].strip().strip('"').strip("'")
                    if raw in ("true", "True"):
                        result[key] = True
                    elif raw in ("false", "False"):
                        result[key] = False
                    else:
                        try:
                            result[key] = float(raw)
                        except ValueError:
                            result[key] = raw
        return result
    except Exception:
        return defaults
