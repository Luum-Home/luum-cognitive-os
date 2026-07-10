# SCOPE: os-only
"""Single-writer enforcement metric recorder (ADR-121 Phase 2).

Appends one JSON line per push attempt to
``.cognitive-os/metrics/single-writer-enforcement.jsonl`` so the governance
layer has an auditable record of every attempt to land on main, its outcome,
and why it was allowed or blocked.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

METRIC_FILE = Path(".cognitive-os/metrics/single-writer-enforcement.jsonl")

Outcome = Literal["allowed", "blocked", "bypassed", "queued"]
VALID_OUTCOMES = {"allowed", "blocked", "bypassed", "queued"}


def record_push_attempt(
    session_id: str,
    branch: str,
    outcome: Outcome,
    reason: str | None = None,
    actor: str = "agent",
    *,
    metric_file: Path | None = None,
) -> dict:
    """Append one push-attempt record and return the written dict.

    Parameters
    ----------
    session_id:
        Identifier for the calling session (used for correlation).
    branch:
        Target branch of the push attempt (typically ``main``).
    outcome:
        One of ``allowed``, ``blocked``, ``bypassed``, or ``queued``.
    reason:
        Human-readable explanation (optional, shown in audit reports).
    actor:
        ``"agent"`` (default) or ``"operator"``.
    metric_file:
        Override the default path (useful in tests).
    """
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"invalid single-writer outcome: {outcome!r}")

    target = metric_file or _resolve_metric_file()
    target.parent.mkdir(parents=True, exist_ok=True)

    record: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "branch": branch,
        "actor": actor,
        "outcome": outcome,
    }
    if reason is not None:
        record["reason"] = reason

    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    return record


def _resolve_metric_file() -> Path:
    """Return the metric path, anchored to the repo root when determinable."""
    # Walk up from cwd looking for the .cognitive-os sentinel.
    cwd = Path(os.getcwd())
    for parent in [cwd, *cwd.parents]:
        if (parent / ".cognitive-os").is_dir():
            return parent / METRIC_FILE
    # Fallback: relative to cwd (e.g. tests outside repo).
    return METRIC_FILE
