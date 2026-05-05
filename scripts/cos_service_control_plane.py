#!/usr/bin/env python3
# SCOPE: os-only
"""Local COS service-control-plane proof implementation.

This is Phase 1 only: a local JSONL queue, one-shot worker, local-command
executor, leases, and artifact bundles. It intentionally does not call Claude,
Codex, provider APIs, Docker, Kubernetes, Redis, or any credential store.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SERVICE_DIR = Path(".cognitive-os") / "service"
QUEUE_FILE = SERVICE_DIR / "queue.jsonl"
LEASE_FILE = SERVICE_DIR / "leases.jsonl"
ARTIFACTS_DIR = SERVICE_DIR / "artifacts"
WORKSPACES_DIR = SERVICE_DIR / "workspaces"

TOKEN_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|auth[_-]?token|bearer|oauth)[=:]\S+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"),
]


@dataclass(frozen=True)
class Task:
    task_id: str
    kind: str
    created_at: str
    requested_by: str
    executor_id: str
    payload: dict[str, Any]
    desired_outputs: list[str]
    approval_policy: str
    status: str = "pending"


@dataclass(frozen=True)
class Lease:
    lease_id: str
    task_id: str
    worker_id: str
    acquired_at: str
    expires_at: str
    heartbeat_at: str
    status: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def resolve_project_dir(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    for env_name in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        env_value = os.environ.get(env_name)
        if env_value:
            return Path(env_value).expanduser().resolve()
    return Path.cwd().resolve()


def service_path(project_dir: Path, relative: Path) -> Path:
    return project_dir / relative


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_name = tmp.name
    Path(tmp_name).replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value).strip(".-")
    return cleaned or "task"


def redact(text: str) -> tuple[str, int]:
    count = 0
    redacted = text
    for pattern in TOKEN_PATTERNS:
        redacted, replacements = pattern.subn("[REDACTED]", redacted)
        count += replacements
    return redacted, count


def build_task_state(project_dir: Path) -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(service_path(project_dir, QUEUE_FILE)):
        event_type = row.get("event_type")
        task_id = row.get("task_id")
        if not isinstance(task_id, str):
            continue
        if event_type == "task_submitted":
            tasks[task_id] = dict(row["task"])
        elif event_type in {"task_completed", "task_failed"} and task_id in tasks:
            tasks[task_id]["status"] = "completed" if event_type == "task_completed" else "failed"
            tasks[task_id]["result"] = row.get("result", {})
    return tasks


def build_lease_state(project_dir: Path) -> dict[str, dict[str, Any]]:
    leases: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(service_path(project_dir, LEASE_FILE)):
        lease_id = row.get("lease_id")
        if isinstance(lease_id, str):
            leases[lease_id] = dict(row["lease"])
    return leases


def active_task_ids(project_dir: Path, now: datetime | None = None) -> set[str]:
    now = now or utc_now()
    active: set[str] = set()
    for lease in build_lease_state(project_dir).values():
        if lease.get("status") != "active":
            continue
        expires_at = lease.get("expires_at")
        if isinstance(expires_at, str) and parse_iso(expires_at) > now:
            active.add(lease["task_id"])
    return active


def submit_task(
    project_dir: Path,
    *,
    kind: str,
    command: str | None,
    task_id: str | None = None,
    requested_by: str = "operator",
    executor_id: str = "local-command",
    approval_policy: str = "propose-only",
) -> dict[str, Any]:
    if kind != "local-command":
        raise ValueError("Phase 1 only supports kind=local-command")
    if executor_id != "local-command":
        raise ValueError("Phase 1 only supports executor_id=local-command")
    if not command or not command.strip():
        raise ValueError("--command is required for local-command tasks")
    if approval_policy != "propose-only":
        raise ValueError("Phase 1 requires approval_policy=propose-only")

    task_id = safe_id(task_id or f"task-{uuid.uuid4().hex[:12]}")
    now = iso(utc_now())
    task = Task(
        task_id=task_id,
        kind=kind,
        created_at=now,
        requested_by=requested_by,
        executor_id=executor_id,
        payload={"command": command},
        desired_outputs=["artifact_bundle"],
        approval_policy=approval_policy,
    )
    event = {
        "event_type": "task_submitted",
        "timestamp": now,
        "task_id": task_id,
        "task": asdict(task),
    }
    append_jsonl(service_path(project_dir, QUEUE_FILE), event)
    return {"ok": True, "status": "submitted", "task": asdict(task)}


def next_pending_task(project_dir: Path) -> dict[str, Any] | None:
    tasks = build_task_state(project_dir)
    active = active_task_ids(project_dir)
    for task in tasks.values():
        if task.get("status") == "pending" and task["task_id"] not in active:
            return task
    return None


def acquire_lease(project_dir: Path, task_id: str, *, ttl_seconds: int, worker_id: str) -> Lease:
    now = utc_now()
    lease = Lease(
        lease_id=f"lease-{uuid.uuid4().hex[:12]}",
        task_id=task_id,
        worker_id=worker_id,
        acquired_at=iso(now),
        expires_at=iso(now + timedelta(seconds=ttl_seconds)),
        heartbeat_at=iso(now),
        status="active",
    )
    append_jsonl(
        service_path(project_dir, LEASE_FILE),
        {
            "event_type": "lease_acquired",
            "timestamp": lease.acquired_at,
            "lease_id": lease.lease_id,
            "task_id": task_id,
            "lease": asdict(lease),
        },
    )
    return lease


def update_lease(project_dir: Path, lease: Lease, status: str) -> Lease:
    now = iso(utc_now())
    updated = Lease(
        lease_id=lease.lease_id,
        task_id=lease.task_id,
        worker_id=lease.worker_id,
        acquired_at=lease.acquired_at,
        expires_at=lease.expires_at,
        heartbeat_at=now,
        status=status,
    )
    append_jsonl(
        service_path(project_dir, LEASE_FILE),
        {
            "event_type": f"lease_{status}",
            "timestamp": now,
            "lease_id": lease.lease_id,
            "task_id": lease.task_id,
            "lease": asdict(updated),
        },
    )
    return updated


def run_local_command(project_dir: Path, task: dict[str, Any], lease: Lease) -> dict[str, Any]:
    command = task["payload"]["command"]
    task_dir = service_path(project_dir, ARTIFACTS_DIR) / safe_id(task["task_id"]) / lease.lease_id
    workspace = service_path(project_dir, WORKSPACES_DIR) / safe_id(task["task_id"])
    logs = task_dir / "logs"
    workspace.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    started_at = iso(utc_now())
    result = subprocess.run(
        command,
        shell=True,
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )
    completed_at = iso(utc_now())
    stdout, stdout_redactions = redact(result.stdout)
    stderr, stderr_redactions = redact(result.stderr)
    (logs / "stdout.txt").write_text(stdout, encoding="utf-8")
    (logs / "stderr.txt").write_text(stderr, encoding="utf-8")

    status = "completed" if result.returncode == 0 else "failed"
    result_payload = {
        "status": status,
        "returncode": result.returncode,
        "started_at": started_at,
        "completed_at": completed_at,
        "artifact_dir": str(task_dir),
        "workspace": str(workspace),
        "redactions": stdout_redactions + stderr_redactions,
    }
    atomic_write_json(task_dir / "task.json", task)
    atomic_write_json(task_dir / "lease.json", asdict(lease))
    atomic_write_json(
        task_dir / "executor.json",
        {
            "executor_id": "local-command",
            "credential_mode": "none",
            "cost_mode": "none",
            "allowed_runtime": "host",
            "provider_calls": 0,
        },
    )
    atomic_write_json(task_dir / "result.json", result_payload)
    atomic_write_json(
        task_dir / "redaction-report.json",
        {
            "stdout_redactions": stdout_redactions,
            "stderr_redactions": stderr_redactions,
            "total_redactions": stdout_redactions + stderr_redactions,
        },
    )
    return result_payload


def worker_run_once(project_dir: Path, *, ttl_seconds: int = 300, worker_id: str | None = None) -> dict[str, Any]:
    task = next_pending_task(project_dir)
    if task is None:
        return {"ok": True, "status": "idle", "reason": "no pending tasks"}

    worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
    lease = acquire_lease(project_dir, task["task_id"], ttl_seconds=ttl_seconds, worker_id=worker_id)
    result = run_local_command(project_dir, task, lease)
    final_status = "completed" if result["status"] == "completed" else "failed"
    update_lease(project_dir, lease, final_status)
    append_jsonl(
        service_path(project_dir, QUEUE_FILE),
        {
            "event_type": "task_completed" if final_status == "completed" else "task_failed",
            "timestamp": iso(utc_now()),
            "task_id": task["task_id"],
            "lease_id": lease.lease_id,
            "result": result,
        },
    )
    return {"ok": final_status == "completed", "status": final_status, "task_id": task["task_id"], "lease_id": lease.lease_id, "result": result}


def queue_drain(project_dir: Path) -> dict[str, Any]:
    tasks = build_task_state(project_dir)
    leases = build_lease_state(project_dir)
    counts = {"pending": 0, "completed": 0, "failed": 0}
    for task in tasks.values():
        status = task.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    active = active_task_ids(project_dir)
    return {
        "ok": True,
        "status": "drained",
        "task_count": len(tasks),
        "lease_count": len(leases),
        "active_task_ids": sorted(active),
        "counts": counts,
        "tasks": list(tasks.values()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", help="Project root; defaults to cwd/env project root.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--project-dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        subparser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    cosd = subparsers.add_parser("cosd", help="Minimal local cosd status surface.")
    add_common(cosd)
    cosd.add_argument("action", nargs="?", default="status", choices=("status",))

    submit = subparsers.add_parser("submit", help="Submit a local Phase 1 task.")
    add_common(submit)
    submit.add_argument("--kind", required=True, choices=("local-command",))
    submit.add_argument("--command", dest="task_command", required=True)
    submit.add_argument("--task-id")
    submit.add_argument("--requested-by", default="operator")
    submit.add_argument("--executor", default="local-command", choices=("local-command",))

    worker = subparsers.add_parser("worker-run-once", help="Claim and execute one pending local task.")
    add_common(worker)
    worker.add_argument("--executor", default="local-command", choices=("local-command",))
    worker.add_argument("--ttl-seconds", type=int, default=300)
    worker.add_argument("--worker-id")

    drain = subparsers.add_parser("queue-drain", help="Report local queue state.")
    add_common(drain)
    return parser


def emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"{payload.get('status')}: {payload.get('task_id', payload.get('reason', ''))}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)
    try:
        if args.subcommand == "cosd":
            payload = queue_drain(project_dir)
            payload["daemon"] = "cosd"
        elif args.subcommand == "submit":
            payload = submit_task(
                project_dir,
                kind=args.kind,
                command=args.task_command,
                task_id=args.task_id,
                requested_by=args.requested_by,
                executor_id=args.executor,
            )
        elif args.subcommand == "worker-run-once":
            payload = worker_run_once(project_dir, ttl_seconds=args.ttl_seconds, worker_id=args.worker_id)
        elif args.subcommand == "queue-drain":
            payload = queue_drain(project_dir)
        else:  # pragma: no cover
            raise ValueError(f"unknown command: {args.subcommand}")
    except ValueError as exc:
        payload = {"ok": False, "status": "error", "reason": str(exc)}
        emit(payload, json_output=args.json)
        return 2
    emit(payload, json_output=args.json)
    return 0 if payload.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
