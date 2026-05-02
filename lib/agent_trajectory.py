# SCOPE: os-only
"""Agent trajectory event schema for Cognitive OS."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrajectoryEvent:
    """One normalized tool event in an agent trajectory."""

    session_id: str
    task_id: str
    tool: str
    command_class: str
    status: str
    exit_code: int
    summary: str
    risk_tags: list[str] = field(default_factory=list)
    artifact_path: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["timestamp"] = self.timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
        return row


def append_trajectory(path: str | Path, event: TrajectoryEvent) -> None:
    """Append one trajectory event as JSONL."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")


def event_from_aci(observation: dict[str, Any], *, session_id: str, task_id: str) -> TrajectoryEvent:
    """Build a trajectory event from an ACI observation dict."""
    return TrajectoryEvent(
        session_id=session_id,
        task_id=task_id,
        tool=str(observation.get("tool", "unknown")),
        command_class=str(observation.get("command_class", "unknown")),
        status=str(observation.get("status", "unknown")),
        exit_code=int(observation.get("exit_code", 0) or 0),
        summary=str(observation.get("summary", "")),
        risk_tags=list(observation.get("risk_tags", []) or []),
        artifact_path=str(observation.get("artifact_path", "")),
    )
