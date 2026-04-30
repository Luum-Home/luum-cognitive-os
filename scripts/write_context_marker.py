#!/usr/bin/env python3
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

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VALID_KINDS = ("orchestrator", "subagent", "cron", "hook", "human")
MAX_PARENT_DEPTH = 10


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
