"""Task completion reconciliation for concurrent sessions.

The helper is intentionally filesystem-only and scratch-repo friendly: it reads
per-session task ledgers and a completion watermark, then reports pending tasks
that another session already completed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

TERMINAL_BY_OTHER = {"completed-by-watermark", "done-by-other-session"}


@dataclass(frozen=True)
class Reconciliation:
    task_id: str
    pending_session: str
    completing_session: str
    status: str
    evidence_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _task_rows(session_dir: Path) -> Iterable[dict[str, Any]]:
    tasks = session_dir / "tasks.json"
    if not tasks.exists():
        return []
    raw = _read_json(tasks)
    if isinstance(raw, dict):
        rows = raw.get("tasks", [])
    else:
        rows = raw
    return [row for row in rows if isinstance(row, dict)]


def _watermark_rows(project_dir: Path) -> list[dict[str, Any]]:
    candidates = [
        project_dir / ".cognitive-os" / "tasks" / "completion-watermark.jsonl",
        project_dir / ".cognitive-os" / "sessions" / "completion-watermark.jsonl",
    ]
    rows: list[dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            if isinstance(data, dict):
                data.setdefault("_evidence_path", str(path))
                rows.append(data)
    return rows


def reconcile_completed_by_other_session(project_dir: Path) -> list[Reconciliation]:
    """Return pending tasks made terminal by another session's watermark."""
    project_dir = project_dir.resolve()
    completions: dict[str, dict[str, Any]] = {}
    for row in _watermark_rows(project_dir):
        task_id = str(row.get("task_id") or "").strip()
        status = str(row.get("status") or "completed-by-watermark")
        if task_id and status in TERMINAL_BY_OTHER | {"completed", "done"}:
            completions[task_id] = row

    reconciled: list[Reconciliation] = []
    sessions_root = project_dir / ".cognitive-os" / "sessions"
    if not sessions_root.exists():
        return reconciled
    for session_dir in sorted(p for p in sessions_root.iterdir() if p.is_dir()):
        pending_session = session_dir.name
        for task in _task_rows(session_dir):
            task_id = str(task.get("task_id") or task.get("id") or "").strip()
            status = str(task.get("status") or "").lower()
            if not task_id or status not in {"pending", "in_progress", "queued", "open", "todo", "blocked"}:
                continue
            completion = completions.get(task_id)
            if not completion:
                continue
            completing_session = str(completion.get("session_id") or completion.get("completed_by_session") or "unknown")
            if completing_session == pending_session:
                continue
            reconciled.append(
                Reconciliation(
                    task_id=task_id,
                    pending_session=pending_session,
                    completing_session=completing_session,
                    status="completed-by-watermark" if completion.get("status") != "done-by-other-session" else "done-by-other-session",
                    evidence_path=str(completion.get("_evidence_path") or ""),
                )
            )
    return reconciled
