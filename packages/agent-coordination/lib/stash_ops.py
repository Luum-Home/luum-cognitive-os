"""ADR-117 compliant stash operations library.

Provides governed push/apply/drop with:
  - Named stashes (Invariant 1)
  - Apply-by-name, never pop (Invariant 2)
  - JSONL audit log to .cognitive-os/metrics/stash-ops.jsonl (Invariant 3)
  - Budget enforcement: max 5 unrestored stashes per session (Invariant 4)
  - Coordinated via stash.lock (Invariant 5, reusing _locked from stash_provenance)

Schema for stash-ops.jsonl (ADR-117 §3):
  {"ts":"<ISO-8601>","hook":"<str>","name":"<stash-label>","action":"push|apply|drop|budget-warn","status":"ok|fail|skip"}

Stdlib-only. No third-party dependencies.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _project_dir() -> Path:
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(env_var)
        if val:
            return Path(val).resolve()
    return Path.cwd().resolve()


def _runtime_dir(project_dir: Optional[Path] = None) -> Path:
    p = (project_dir or _project_dir()) / ".cognitive-os" / "runtime"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _metrics_dir(project_dir: Optional[Path] = None) -> Path:
    p = (project_dir or _project_dir()) / ".cognitive-os" / "metrics"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _stash_ops_file(project_dir: Optional[Path] = None) -> Path:
    return _metrics_dir(project_dir) / "stash-ops.jsonl"


def _stash_lock_file(project_dir: Optional[Path] = None) -> Path:
    return _runtime_dir(project_dir) / "stash.lock"


# ---------------------------------------------------------------------------
# Stash lock — flock preferred, mkdir-CAS fallback (mirrors stash_provenance)
# ---------------------------------------------------------------------------

@contextmanager
def _stash_locked(project_dir: Optional[Path] = None) -> Iterator[None]:
    """Acquire .cognitive-os/runtime/stash.lock before any stash mutation."""
    lf = _stash_lock_file(project_dir)
    lf.parent.mkdir(parents=True, exist_ok=True)
    try:
        with lf.open("a", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except (OSError, AttributeError):
        # Fallback: mkdir-based CAS lock
        lock_dir = Path(str(lf) + ".d")
        deadline = time.monotonic() + 10
        acquired = False
        while time.monotonic() < deadline:
            try:
                lock_dir.mkdir()
                acquired = True
                break
            except FileExistsError:
                time.sleep(0.05)
        if not acquired:
            raise TimeoutError(f"Could not acquire stash lock: {lock_dir}")
        try:
            yield
        finally:
            try:
                lock_dir.rmdir()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Session ID
# ---------------------------------------------------------------------------

def _session_id() -> str:
    """Return current session ID from env, or a stable fallback."""
    for var in ("COS_SESSION_ID", "CLAUDE_SESSION_ID", "SESSION_ID"):
        val = os.environ.get(var)
        if val:
            return val
    # Stable per-process fallback (not per-session; good enough for tests)
    return f"pid-{os.getpid()}"


# ---------------------------------------------------------------------------
# Audit log — Invariant 3
# ---------------------------------------------------------------------------

def audit_append(
    hook: str,
    name: str,
    action: str,
    status: str,
    extra: Optional[dict] = None,
    *,
    project_dir: Optional[Path] = None,
) -> None:
    """Append one record to .cognitive-os/metrics/stash-ops.jsonl.

    Schema (ADR-117 §3): {ts, hook, name, action, status}
    Failure is non-fatal — emits a stderr warning and returns.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record: dict = {"ts": ts, "hook": hook, "name": name, "action": action, "status": status}
    if extra:
        record.update(extra)
    line = json.dumps(record) + "\n"
    try:
        ops_file = _stash_ops_file(project_dir)
        # Atomic append: open with O_APPEND so concurrent writers don't interleave
        with ops_file.open("a", encoding="utf-8") as fh:
            # Additionally grab a shared flock so the line is atomic at the OS level
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            except (OSError, AttributeError):
                pass
            fh.write(line)
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except (OSError, AttributeError):
                pass
    except Exception as exc:  # non-fatal per ADR-117 §3
        print(f"WARN stash_ops.audit_append: could not write stash-ops.jsonl: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Budget check — Invariant 4
# ---------------------------------------------------------------------------

def budget_check(
    session_id: Optional[str] = None,
    *,
    project_dir: Optional[Path] = None,
) -> Tuple[bool, int]:
    """Check whether the session is within the stash budget.

    Returns (within_budget, unrestored_count).
    Budget = 5 unrestored stashes per session (ADR-117 §4).

    Counts stash entries whose message contains the session_id substring.
    """
    sid = session_id or _session_id()
    try:
        result = subprocess.run(
            ["git", "stash", "list"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(project_dir or _project_dir()),
            timeout=60,
        )
        lines = result.stdout.strip().splitlines() if result.stdout.strip() else []
        unrestored = sum(1 for line in lines if sid in line)
    except Exception:
        unrestored = 0
    within = unrestored < 5
    return (within, unrestored)


# ---------------------------------------------------------------------------
# Named push — Invariant 1 + 3 + 4 + 5
# ---------------------------------------------------------------------------

def push_named(
    message: str,
    *,
    hook: str,
    files: Optional[List[str]] = None,
    budget_check: bool = True,
    session_id: Optional[str] = None,
    project_dir: Optional[Path] = None,
) -> str:
    """Push a named stash, audit-log, enforce budget.

    The stash label is: {session_id}:{hook}:{epoch}-{uuid4_short}
    The caller-supplied `message` is appended after a space for human context.

    Returns the stash ref (e.g. "stash@{0}") on success.
    Raises RuntimeError if budget is exceeded (when budget_check=True).
    Raises subprocess.CalledProcessError on git failure.
    """
    sid = session_id or _session_id()
    epoch = int(time.time())
    uid = uuid.uuid4().hex[:8]
    label = f"{sid}:{hook}:{epoch}-{uid}"
    if message:
        full_label = f"{label} {message}"
    else:
        full_label = label

    with _stash_locked(project_dir):
        # Invariant 4: budget check
        if budget_check:
            within, count = globals()["budget_check"](sid, project_dir=project_dir)
            if not within:
                audit_append(hook, full_label, "budget-warn", "skip", project_dir=project_dir)
                raise RuntimeError(
                    f"stash budget exhausted: {count} unrestored stashes for session '{sid}' "
                    f"(max 5 per ADR-117 §4)"
                )

        # Build git command
        cmd = ["git", "stash", "push", "-m", full_label]
        if files:
            cmd += ["--"] + files

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=str(project_dir or _project_dir()),
                timeout=30,  # timeout per ADR-278 (default - review)
            )
        except subprocess.CalledProcessError:
            audit_append(hook, full_label, "push", "fail", project_dir=project_dir)
            raise

        # Resolve the stash ref by label
        stash_ref = _resolve_ref_by_label(full_label, project_dir=project_dir)
        audit_append(hook, full_label, "push", "ok", project_dir=project_dir)

        # Best-effort provenance integration
        _try_record_provenance(
            stash_ref=stash_ref or full_label,
            session_id=sid,
            hook=hook,
            files=files or [],
            project_dir=project_dir,
        )

    return stash_ref or full_label


# ---------------------------------------------------------------------------
# Apply by name — Invariant 2 + 3 + 5
# ---------------------------------------------------------------------------

def apply_by_name(
    name: str,
    *,
    hook: str,
    project_dir: Optional[Path] = None,
) -> bool:
    """Apply a named stash by its label (NEVER pop).

    Resolves label → stash ref via `git stash list`, then applies.
    Returns True on success, False on failure (stash entry is preserved on failure).
    """
    with _stash_locked(project_dir):
        ref = _resolve_ref_by_label(name, project_dir=project_dir)
        if ref is None:
            audit_append(hook, name, "apply", "skip",
                         {"reason": "ref_not_found"}, project_dir=project_dir)
            return False

        try:
            subprocess.run(
                ["git", "stash", "apply", ref],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(project_dir or _project_dir()),
                timeout=60,
            )
            audit_append(hook, name, "apply", "ok", project_dir=project_dir)
            return True
        except subprocess.CalledProcessError:
            # apply failed — stash entry is still intact (not dropped)
            audit_append(hook, name, "apply", "fail", project_dir=project_dir)
            return False


# ---------------------------------------------------------------------------
# Drop by ref — Invariant 3 + 5
# ---------------------------------------------------------------------------

def drop_by_ref(
    ref: str,
    *,
    hook: str,
    project_dir: Optional[Path] = None,
) -> bool:
    """Drop a stash entry by ref. Audit-log result.

    Returns True on success, False if ref was not found or drop failed.
    """
    with _stash_locked(project_dir):
        # Resolve name for logging — ref may be "stash@{N}" or a label string
        name = _label_for_ref(ref, project_dir=project_dir) or ref
        try:
            subprocess.run(
                ["git", "stash", "drop", ref],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(project_dir or _project_dir()),
                timeout=60,
            )
            audit_append(hook, name, "drop", "ok", project_dir=project_dir)
            return True
        except subprocess.CalledProcessError:
            audit_append(hook, name, "drop", "fail", project_dir=project_dir)
            return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_ref_by_label(
    label: str,
    *,
    project_dir: Optional[Path] = None,
) -> Optional[str]:
    """Return the first stash ref (e.g. 'stash@{0}') whose message contains label."""
    try:
        result = subprocess.run(
            ["git", "stash", "list"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(project_dir or _project_dir()),
            timeout=60,
        )
        for line in result.stdout.splitlines():
            if label in line:
                # Format: "stash@{N}: On branch: message" or "stash@{N}: WIP on ..."
                ref = line.split(":")[0].strip()
                return ref
    except Exception:
        pass
    return None


def _label_for_ref(
    ref: str,
    *,
    project_dir: Optional[Path] = None,
) -> Optional[str]:
    """Return the stash message for a given stash ref."""
    try:
        result = subprocess.run(
            ["git", "stash", "list"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(project_dir or _project_dir()),
            timeout=60,
        )
        for line in result.stdout.splitlines():
            if line.startswith(ref + ":"):
                # Strip leading "stash@{N}: [On branch: ]"
                parts = line.split(":", 2)
                return parts[-1].strip() if len(parts) >= 2 else line
    except Exception:
        pass
    return None


def _try_record_provenance(
    stash_ref: str,
    session_id: str,
    hook: str,
    files: List[str],
    project_dir: Optional[Path],
) -> None:
    """Best-effort provenance registration. Swallows all errors."""
    try:
        # Import lazily to avoid circular dependency at module load time
        from stash_provenance import record_provenance  # type: ignore[import]
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record_provenance(
            stash_ref=stash_ref,
            session_id=session_id,
            agent_id=hook,
            original_files=files,
            created_at=ts,
            project_dir=project_dir,
        )
    except Exception:
        pass  # provenance is best-effort; stash_ops is the authority here
