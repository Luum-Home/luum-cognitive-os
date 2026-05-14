#!/usr/bin/env python3
# SCOPE: os-only
"""Write a JSON context marker for the current process.

Used by session-init.sh (kind=orchestrator) and agent preamble paths (kind=subagent)
so that commit_provenance.py can resolve accurate session/kind/harness attribution via
PPID-chain lookup instead of env-var guessing.

Usage:
  python3 scripts/write_context_marker.py <kind>

  kind: orchestrator | subagent | cron | hook | human

Output:
  .cognitive-os/sessions/.context-<pid>.json  (atomic temp+rename)

Backwards compat:
  Old .current-session-<pid> plain-text markers are NOT removed by this script.
  The reader (commit_provenance.py) handles both formats.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import tempfile

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.time_utils import now_iso as _now_iso

from scripts.cos_task_claims import claim_task

VALID_KINDS = ("orchestrator", "subagent", "cron", "hook", "human")
MAX_PARENT_DEPTH = 10


# ---------------------------------------------------------------------------
# Fix 2 (ADR-097): PID capture — update active-tasks.json when subagent starts
# ---------------------------------------------------------------------------

def _active_tasks_path(repo: Path) -> Path:
    return repo / ".cognitive-os" / "tasks" / "active-tasks.json"



def _is_claimable_pending(task: dict) -> bool:
    return task.get("status") == "pending" and not task.get("claim_conflict")


def _write_tasks_file(tasks_path: Path, data: dict) -> None:
    tmp_fd, tmp_str = tempfile.mkstemp(
        dir=tasks_path.parent, prefix=".active-tasks-tmp-", suffix=".json"
    )
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_str, tasks_path)
    except Exception:
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise


def _claim_pending_task(repo: Path, pid: int, tool_use_id: str | None) -> bool:
    """Find the most recent 'pending' task in active-tasks.json and claim it.

    Sets status='in_progress', pid=<pid>, started_at=now on the matched record.
    Matching priority:
      1. If tool_use_id is provided: match by toolUseId (most reliable).
      2. Otherwise: take the most recently created 'pending' record (best-effort).

    Uses fcntl exclusive lock for concurrent-safe writes.
    Returns True if a record was updated, False otherwise.
    Intentionally swallows all errors — this is best-effort.
    """
    tasks_path = _active_tasks_path(repo)
    if not tasks_path.is_file():
        return False

    lock_path = tasks_path.parent / ".active-tasks.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(lock_path, "w") as lock_fh:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
            try:
                data = json.loads(tasks_path.read_text())
                tasks = data.get("tasks", [])

                matched_idx: int | None = None

                if tool_use_id:
                    # Prefer exact toolUseId match in any pending record
                    for idx, t in enumerate(tasks):
                        if (
                            t.get("toolUseId") == tool_use_id
                            and _is_claimable_pending(t)
                        ):
                            matched_idx = idx
                            break

                if matched_idx is None:
                    # Fall back to most recently created pending record
                    # (heuristic: highest launchedAt or last in list)
                    pending = [
                        (idx, t)
                        for idx, t in enumerate(tasks)
                        if _is_claimable_pending(t)
                    ]
                    if pending:
                        # Sort by launchedAt descending (latest first)
                        pending.sort(
                            key=lambda x: x[1].get("launchedAt", ""),
                            reverse=True,
                        )
                        matched_idx = pending[0][0]

                if matched_idx is None:
                    return False

                # Cross-session claim ledger (P1.1): do not take a pending task
                # if another live session already claimed the same task/work fingerprint.
                claimed, claim_result = claim_task(repo, tasks[matched_idx])
                if not claimed:
                    tasks[matched_idx]["claim_conflict"] = claim_result
                    data["lastUpdated"] = _now_iso()
                    tasks[matched_idx]["status"] = "blocked_by_claim"
                    _write_tasks_file(tasks_path, data)
                    return False

                now = _now_iso()
                tasks[matched_idx]["status"] = "in_progress"
                tasks[matched_idx]["pid"] = pid
                tasks[matched_idx]["started_at"] = now
                tasks[matched_idx]["claim_fingerprint"] = claim_result.get("fingerprint")
                data["lastUpdated"] = now

                # Atomic write: temp + rename
                _write_tasks_file(tasks_path, data)

                return True
            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)
    except Exception:
        return False


def detect_harness() -> str:
    if os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    if os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_PROJECT_DIR"):
        return "codex"
    explicit = os.environ.get("COS_COMMIT_HARNESS") or os.environ.get("COGNITIVE_OS_HARNESS")
    if explicit:
        return explicit
    return "unknown"


def detect_session() -> str:
    return (
        os.environ.get("COS_COMMIT_SESSION_ID")
        or os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or "unknown"
    )


def walk_parents(pid: int, max_depth: int = MAX_PARENT_DEPTH) -> list[int]:
    """Walk the PPID chain from pid upward. Returns list [pid, ppid, ppid-of-ppid, ...]."""
    chain: list[int] = []
    current = pid
    for _ in range(max_depth):
        chain.append(current)
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(current)],
                capture_output=True,
                text=True,
                timeout=2,
            )
            ppid_str = result.stdout.strip()
            if not ppid_str:
                break
            ppid = int(ppid_str)
            if ppid <= 1 or ppid == current:
                break
            current = ppid
        except (subprocess.SubprocessError, ValueError, OSError):
            break
    return chain


def resolve_repo() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        top = result.stdout.strip()
        if top:
            return Path(top)
    except Exception:
        pass
    return Path.cwd()


def write_context_marker(kind: str) -> Path:
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind {kind!r}. Must be one of {VALID_KINDS}")

    repo = resolve_repo()
    sessions_dir = repo / ".cognitive-os" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    pid = os.getpid()
    ppid_chain = walk_parents(pid)

    marker_data = {
        "session": detect_session(),
        "kind": kind,
        "harness": detect_harness(),
        "pid": pid,
        "ppid": ppid_chain[1] if len(ppid_chain) > 1 else None,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_chain": ppid_chain,
    }

    target_path = sessions_dir / f".context-{pid}.json"
    # Atomic write: write to temp file then rename to avoid partial reads
    fd, tmp_path = tempfile.mkstemp(dir=sessions_dir, prefix=".context-tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(marker_data, f)
            f.write("\n")
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Fix 2 (ADR-097): when running as subagent, claim the pending task record
    # in active-tasks.json — set status=in_progress and capture our PID.
    # We read CLAUDE_TOOL_USE_ID from env if the harness injects it; otherwise
    # fall back to best-effort (most recent pending record).
    if kind == "subagent":
        tool_use_id = os.environ.get("CLAUDE_TOOL_USE_ID") or os.environ.get(
            "COS_TOOL_USE_ID"
        )
        _claim_pending_task(repo, pid, tool_use_id)

    return target_path


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <kind>", file=sys.stderr)
        print(f"  kind: one of {VALID_KINDS}", file=sys.stderr)
        return 1

    kind = sys.argv[1]
    try:
        path = write_context_marker(kind)
        print(f"Context marker written: {path}", file=sys.stderr)
        return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR writing context marker: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
