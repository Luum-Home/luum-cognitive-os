# SCOPE: both
"""Portable inbound agent-control policy for harnesses without process handles.

This module turns Agent Bus fallback artifacts into a deterministic hook/runtime
verdict.  Runtime loops that own a child process can enforce controls directly
(e.g. ``ClaudeExecutor``). Harnesses that only expose hook boundaries can call
``evaluate_control`` before each tool/action and block when the latest inbound
control says ``stop`` or an unresolved ``pause`` is active.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

CONTROL_COMMANDS = {"stop", "pause", "resume"}
BLOCKING_COMMANDS = {"stop", "pause"}


@dataclass(frozen=True)
class ControlDecision:
    """Decision returned by the portable inbound-control policy."""

    action: str = "allow"  # allow | block
    command: str = ""
    target_id: str = ""
    reason: str = ""
    source_path: str = ""
    timestamp_epoch: float = 0.0

    @property
    def should_block(self) -> bool:
        return self.action == "block"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "command": self.command,
            "target_id": self.target_id,
            "reason": self.reason,
            "source_path": self.source_path,
            "timestamp_epoch": self.timestamp_epoch,
            "should_block": self.should_block,
        }


def project_dir_from_env(default: str | Path | None = None) -> Path:
    """Resolve project dir using the cross-harness portability precedence."""

    return Path(
        os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or default
        or os.getcwd()
    )


def session_id_from_env() -> str:
    """Resolve session id using the cross-harness portability precedence."""

    return (
        os.environ.get("COGNITIVE_OS_SESSION_ID")
        or os.environ.get("CODEX_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("CODEX_THREAD_ID")
        or ""
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except OSError:
        return []
    return rows


def _timestamp(row: dict[str, Any], fallback: float = 0.0) -> float:
    raw = row.get("timestamp_epoch", fallback)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return fallback


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = str(value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def target_ids_from_payload(payload: dict[str, Any] | None = None) -> list[str]:
    """Return possible target ids for inbound control lookup."""

    payload = payload or {}
    candidates = [
        payload.get("agent_id"),
        payload.get("tool_use_id"),
        payload.get("session_id"),
        payload.get("codex_session_id"),
        payload.get("codex_thread_id"),
        session_id_from_env(),
        os.environ.get("CODEX_THREAD_ID"),
    ]
    return _unique(str(v) for v in candidates if v)


def _events_for_target(project_dir: Path, target_id: str) -> list[dict[str, Any]]:
    agent_dir = project_dir / ".cognitive-os" / "agent-bus" / target_id
    events: list[dict[str, Any]] = []

    interrupt = agent_dir / "interrupt"
    if interrupt.exists():
        row = _read_json(interrupt) or {}
        command = str(row.get("command") or "stop")
        if command in CONTROL_COMMANDS:
            events.append(
                {
                    **row,
                    "command": command,
                    "source_path": str(interrupt),
                    "timestamp_epoch": _timestamp(row, interrupt.stat().st_mtime),
                }
            )

    control = agent_dir / "control.jsonl"
    for index, row in enumerate(_read_jsonl(control)):
        command = str(row.get("command") or "")
        if command not in CONTROL_COMMANDS:
            continue
        events.append(
            {
                **row,
                "command": command,
                "source_path": str(control),
                "timestamp_epoch": _timestamp(row, float(index)),
            }
        )
    return events


def evaluate_control(
    project_dir: str | Path,
    *,
    payload: dict[str, Any] | None = None,
    target_ids: Iterable[str] | None = None,
) -> ControlDecision:
    """Evaluate whether the latest inbound control should block execution.

    Semantics:
    - latest ``stop`` blocks permanently until a newer control supersedes it;
    - latest ``pause`` blocks at hook/runtime boundaries;
    - latest ``resume`` allows execution again;
    - no control allows execution.
    """

    root = Path(project_dir)
    ids = _unique(target_ids or target_ids_from_payload(payload))
    latest: tuple[str, dict[str, Any]] | None = None
    for target_id in ids:
        for event in _events_for_target(root, target_id):
            if latest is None or _timestamp(event) >= _timestamp(latest[1]):
                latest = (target_id, event)

    if latest is None:
        return ControlDecision()

    target_id, event = latest
    command = str(event.get("command") or "")
    ts = _timestamp(event)
    source = str(event.get("source_path") or "")
    if command in BLOCKING_COMMANDS:
        reason = (
            "Agent execution stopped by orchestrator control signal."
            if command == "stop"
            else "Agent execution paused by orchestrator control signal; send resume to continue."
        )
        return ControlDecision(
            action="block",
            command=command,
            target_id=target_id,
            reason=reason,
            source_path=source,
            timestamp_epoch=ts,
        )

    return ControlDecision(
        action="allow",
        command=command,
        target_id=target_id,
        reason="Latest inbound control allows execution.",
        source_path=source,
        timestamp_epoch=ts,
    )


def append_policy_event(project_dir: str | Path, decision: ControlDecision) -> Path:
    """Append a control-policy metric for auditability."""

    path = Path(project_dir) / ".cognitive-os" / "metrics" / "agent-control-policy.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp_epoch": time.time(), **decision.to_dict()}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return path
