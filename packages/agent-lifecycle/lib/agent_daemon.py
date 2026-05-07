# SCOPE: both
"""ADR-235 opt-in detached agent daemon substrate.

This module deliberately does not run a resident service by default. It provides
file-backed queue/state primitives and a tmux launcher that a future launchd or
systemd wrapper can call. The default path is local-first and opt-in.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "detached-agent-task/v1"


class AgentDaemonError(RuntimeError):
    """Raised when a detached-agent operation cannot proceed safely."""


@dataclass(frozen=True)
class DetachedAgentTask:
    schema_version: str
    task_id: str
    session_id: str
    command: str
    project_dir: str
    worktree_path: str
    status: str
    tmux_session: str
    created_at: float
    updated_at: float
    team_name: str | None = None
    max_runtime_seconds: int = 3600

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentDaemon:
    """File-backed detached-agent queue plus tmux launcher."""

    def __init__(self, *, project_dir: str | Path | None = None, root_dir: str | Path | None = None) -> None:
        self.project_dir = Path(project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()
        self.root = Path(root_dir).expanduser().resolve() if root_dir else self.project_dir / ".cognitive-os" / "agent-daemon"
        self.tasks_dir = self.root / "tasks"
        self.root.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    @property
    def queue_path(self) -> Path:
        return self.root / "queue.jsonl"

    @property
    def results_path(self) -> Path:
        return self.root / "results.jsonl"

    def task_dir(self, task_id: str) -> Path:
        return self.tasks_dir / _safe_id(task_id)

    def state_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "state.json"

    def done_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "done.json"

    def heartbeat_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "heartbeat.json"

    def enqueue(
        self,
        *,
        command: str,
        task_id: str | None = None,
        session_id: str | None = None,
        worktree_path: str | Path | None = None,
        team_name: str | None = None,
        max_runtime_seconds: int = 3600,
    ) -> DetachedAgentTask:
        if not command.strip():
            raise AgentDaemonError("command is required")
        tid = _safe_id(task_id or f"agent-{uuid.uuid4().hex[:12]}")
        if max_runtime_seconds <= 0:
            raise AgentDaemonError("max_runtime_seconds must be positive")
        now = time.time()
        task = DetachedAgentTask(
            schema_version=SCHEMA_VERSION,
            task_id=tid,
            session_id=session_id or os.environ.get("COGNITIVE_OS_SESSION_ID") or "manual",
            command=command,
            project_dir=str(self.project_dir),
            worktree_path=str(Path(worktree_path or self.project_dir).resolve()),
            status="queued",
            tmux_session=f"cos-agent-{tid}",
            created_at=now,
            updated_at=now,
            team_name=team_name,
            max_runtime_seconds=max_runtime_seconds,
        )
        self._write_state(task)
        _append_jsonl(self.queue_path, task.to_dict())
        return task

    def list_tasks(self) -> list[DetachedAgentTask]:
        tasks: list[DetachedAgentTask] = []
        for state in sorted(self.tasks_dir.glob("*/state.json")):
            try:
                data = json.loads(state.read_text(encoding="utf-8"))
                tasks.append(DetachedAgentTask(**data))
            except (json.JSONDecodeError, TypeError):
                continue
        return tasks

    def next_queued(self) -> DetachedAgentTask | None:
        for task in self.list_tasks():
            if task.status == "queued":
                return task
        return None

    def launch_next(self, *, tmux_bin: str | None = None, dry_run: bool = False) -> DetachedAgentTask | None:
        task = self.next_queued()
        if task is None:
            return None
        return self.launch(task.task_id, tmux_bin=tmux_bin, dry_run=dry_run)

    def launch(self, task_id: str, *, tmux_bin: str | None = None, dry_run: bool = False) -> DetachedAgentTask:
        task = self.get_task(task_id)
        if task.status not in {"queued", "failed"}:
            raise AgentDaemonError(f"task {task_id} is not launchable from status {task.status}")
        launcher = tmux_bin or shutil.which("tmux")
        if launcher and not Path(launcher).exists() and os.sep in launcher:
            launcher = None
        if not launcher and not dry_run:
            raise AgentDaemonError("tmux not found; install tmux or run with --dry-run")

        script = self._write_run_script(task)
        running = self._replace_task(task, status="running")
        if not dry_run:
            proc = subprocess.run(
                [launcher or "tmux", "new-session", "-d", "-s", running.tmux_session, "bash", str(script)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode != 0:
                self._replace_task(running, status="failed")
                raise AgentDaemonError(proc.stderr.strip() or proc.stdout.strip() or "tmux launch failed")
        return running

    def get_task(self, task_id: str) -> DetachedAgentTask:
        path = self.state_path(task_id)
        if not path.is_file():
            raise AgentDaemonError(f"unknown task: {task_id}")
        return DetachedAgentTask(**json.loads(path.read_text(encoding="utf-8")))

    def reap_completed(self) -> list[DetachedAgentTask]:
        completed: list[DetachedAgentTask] = []
        for task in self.list_tasks():
            if task.status != "running" or not self.done_path(task.task_id).is_file():
                continue
            done = json.loads(self.done_path(task.task_id).read_text(encoding="utf-8"))
            status = "completed" if int(done.get("exit_code", 1)) == 0 else "failed"
            updated = self._replace_task(task, status=status)
            _append_jsonl(self.results_path, {**updated.to_dict(), "done": done})
            completed.append(updated)
        return completed

    def _write_run_script(self, task: DetachedAgentTask) -> Path:
        task_dir = self.task_dir(task.task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        script = task_dir / "run.sh"
        heartbeat = self.heartbeat_path(task.task_id)
        done = self.done_path(task.task_id)
        escaped_command = task.command.replace("'", "'\\''")
        script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"cd {json.dumps(task.worktree_path)}\n"
            f"printf '{{\"timestamp\":%s,\"task_id\":\"{task.task_id}\"}}\\n' \"$(date +%s)\" > {json.dumps(str(heartbeat))}\n"
            "exit_code=0\n"
            f"bash -lc '{escaped_command}' || exit_code=$?\n"
            f"printf '{{\"timestamp\":%s,\"task_id\":\"{task.task_id}\",\"exit_code\":%s}}\\n' \"$(date +%s)\" \"$exit_code\" > {json.dumps(str(done))}\n"
            "exit \"$exit_code\"\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    def _write_state(self, task: DetachedAgentTask) -> None:
        path = self.state_path(task.task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(task.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _replace_task(self, task: DetachedAgentTask, *, status: str) -> DetachedAgentTask:
        updated = DetachedAgentTask(**{**task.to_dict(), "status": status, "updated_at": time.time()})
        self._write_state(updated)
        return updated


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in value.strip())
    cleaned = cleaned.strip(".-_")
    if not cleaned:
        raise AgentDaemonError("unsafe empty task id")
    return cleaned[:96]


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
