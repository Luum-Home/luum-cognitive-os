"""retry_tracker.py — Retry diversity enforcement helper (ADR-038 Gap #7).

Tracks approach hashes per agent to enforce the RETRY DIVERSITY protocol:
each retry attempt must use a different strategy than all previous attempts
for the same agent_id.

All state is persisted to ``.cognitive-os/metrics/retry-tracker.jsonl`` so the
history survives across tool calls within a session.

Thread-safety: file appends are atomic on POSIX (write < PIPE_BUF). Concurrent
reads use a snapshot read; no locking is required for the append-only pattern.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Optional

# Default metrics path resolved relative to project dir or cwd.
_DEFAULT_RELATIVE = ".cognitive-os/metrics/retry-tracker.jsonl"


def _metrics_path(project_dir: Optional[str] = None) -> Path:
    base = Path(
        project_dir
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or Path.cwd()
    )
    return base / _DEFAULT_RELATIVE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_attempt(
    agent_id: str,
    approach_hash: str,
    project_dir: Optional[str] = None,
) -> None:
    """Append an attempt record to the retry-tracker JSONL.

    Parameters
    ----------
    agent_id:
        Stable identifier for the agent / task (e.g. ``tool_use_id``).
    approach_hash:
        One-line summary of the approach used on this attempt (acts as a
        discriminator so repeated strategies can be detected).
    project_dir:
        Override for the project root. Falls back to env vars then ``cwd``.
    """
    path = _metrics_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "agent_id": agent_id,
        "approach_hash": approach_hash,
        "timestamp_epoch": time.time(),
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def approach_seen(
    agent_id: str,
    approach_hash: str,
    project_dir: Optional[str] = None,
) -> bool:
    """Return True if ``approach_hash`` has already been used for ``agent_id``.

    Reads the current snapshot of the JSONL; does not mutate state.
    """
    for seen in approaches_tried(agent_id, project_dir=project_dir):
        if seen == approach_hash:
            return True
    return False


def approaches_tried(
    agent_id: str,
    project_dir: Optional[str] = None,
) -> List[str]:
    """Return ordered list of approach hashes tried so far for ``agent_id``.

    Useful for including escalation context so the human can see what was
    attempted before the agent gave up.
    """
    path = _metrics_path(project_dir)
    if not path.exists():
        return []

    results: List[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("agent_id") == agent_id:
                results.append(record.get("approach_hash", ""))
    except OSError:
        return []
    return results
