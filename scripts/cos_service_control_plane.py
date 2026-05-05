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
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.script_io import atomic_write_json

import cos_auth_probe

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
        elif event_type in {"task_completed", "task_failed", "task_needs_human"} and task_id in tasks:
            if event_type == "task_completed":
                tasks[task_id]["status"] = "completed"
            elif event_type == "task_needs_human":
                tasks[task_id]["status"] = "needs_human"
            else:
                tasks[task_id]["status"] = "failed"
            tasks[task_id]["result"] = row.get("result", {})
    return tasks


def build_lease_state(project_dir: Path) -> dict[str, dict[str, Any]]:
    leases: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(service_path(project_dir, LEASE_FILE)):
        lease_id = row.get("lease_id")
        if isinstance(lease_id, str):
            leases[lease_id] = dict(row["lease"])
    return leases


def expire_stale_leases(project_dir: Path, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or utc_now()
    expired: list[dict[str, Any]] = []
    for lease in build_lease_state(project_dir).values():
        if lease.get("status") != "active":
            continue
        expires_at = lease.get("expires_at")
        if isinstance(expires_at, str) and parse_iso(expires_at) <= now:
            lease_obj = Lease(**lease)
            updated = update_lease(project_dir, lease_obj, "expired")
            expired.append(asdict(updated))
    return expired


def active_task_ids(project_dir: Path, now: datetime | None = None) -> set[str]:
    now = now or utc_now()
    expire_stale_leases(project_dir, now)
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
    prompt: str | None = None,
    task_id: str | None = None,
    requested_by: str = "operator",
    executor_id: str = "local-command",
    approval_policy: str = "propose-only",
    dry_run: bool = False,
) -> dict[str, Any]:
    if kind == "local-command":
        if executor_id != "local-command":
            raise ValueError("local-command tasks require executor_id=local-command")
        if not command or not command.strip():
            raise ValueError("--command is required for local-command tasks")
        payload = {"command": command}
    elif kind == "provider":
        if executor_id not in {"codex-cli-host", "claude-cli-host"}:
            raise ValueError("provider tasks require executor_id=codex-cli-host or claude-cli-host")
        if not prompt or not prompt.strip():
            raise ValueError("--prompt is required for provider tasks")
        payload = {"prompt": prompt, "dry_run": dry_run}
    else:
        raise ValueError("unsupported task kind")
    if approval_policy != "propose-only":
        raise ValueError("service control plane tasks require approval_policy=propose-only")

    task_id = safe_id(task_id or f"task-{uuid.uuid4().hex[:12]}")
    now = iso(utc_now())
    task = Task(
        task_id=task_id,
        kind=kind,
        created_at=now,
        requested_by=requested_by,
        executor_id=executor_id,
        payload=payload,
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


def run_host_cli_adapter(
    project_dir: Path,
    task: dict[str, Any],
    lease: Lease,
    *,
    allow_provider_call: bool = False,
) -> dict[str, Any]:
    executor_id = task["executor_id"]
    provider = "codex" if executor_id == "codex-cli-host" else "claude"
    prompt = task["payload"]["prompt"]
    task_dir = service_path(project_dir, ARTIFACTS_DIR) / safe_id(task["task_id"]) / lease.lease_id
    logs = task_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    probe = cos_auth_probe.probe(provider, "account-session")
    stdout = ""
    stderr = ""
    provider_calls = 0
    command_shape: list[str]
    status = "needs_human"
    returncode = 0
    reason = "provider call blocked; rerun with --allow-provider-call after reviewing cost and credential posture"

    if executor_id == "codex-cli-host":
        command_shape = ["codex", "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", prompt]
    else:
        command_shape = ["claude", "-p", prompt]

    if allow_provider_call:
        if probe.status != cos_auth_probe.READY:
            status = "auth_required"
            returncode = 2
            reason = probe.reason
        elif executor_id == "claude-cli-host":
            status = "unsupported"
            returncode = 3
            reason = "claude-cli-host provider execution is not enabled until a non-invasive auth status probe is implemented"
        else:
            result = subprocess.run(
                command_shape,
                cwd=project_dir,
                text=True,
                capture_output=True,
                check=False,
            )
            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode
            provider_calls = 1
            status = "completed" if result.returncode == 0 else "failed"
            reason = "provider call executed through official CLI"

    redacted_stdout, stdout_redactions = redact(stdout)
    redacted_stderr, stderr_redactions = redact(stderr)
    (logs / "stdout.txt").write_text(redacted_stdout, encoding="utf-8")
    (logs / "stderr.txt").write_text(redacted_stderr, encoding="utf-8")

    result_payload = {
        "status": status,
        "returncode": returncode,
        "reason": reason,
        "artifact_dir": str(task_dir),
        "redactions": stdout_redactions + stderr_redactions,
        "provider_calls": provider_calls,
        "command_shape": command_shape[:4] + ["<prompt>"],
    }
    atomic_write_json(task_dir / "task.json", task)
    atomic_write_json(task_dir / "lease.json", asdict(lease))
    atomic_write_json(
        task_dir / "executor.json",
        {
            "executor_id": executor_id,
            "provider": provider,
            "credential_mode": "account-session",
            "cost_mode": probe.cost_mode,
            "allowed_runtime": "host",
            "auth_probe": asdict(probe),
            "provider_calls": provider_calls,
            "allow_provider_call": allow_provider_call,
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


def worker_run_once(
    project_dir: Path,
    *,
    ttl_seconds: int = 300,
    worker_id: str | None = None,
    simulate_crash_after_lease: bool = False,
    allow_provider_call: bool = False,
) -> dict[str, Any]:
    expire_stale_leases(project_dir)
    task = next_pending_task(project_dir)
    if task is None:
        return {"ok": True, "status": "idle", "reason": "no pending tasks"}

    worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
    lease = acquire_lease(project_dir, task["task_id"], ttl_seconds=ttl_seconds, worker_id=worker_id)
    if simulate_crash_after_lease:
        return {
            "ok": False,
            "status": "crash_simulated",
            "task_id": task["task_id"],
            "lease_id": lease.lease_id,
            "reason": "lease acquired and worker exited before execution",
        }

    if task["executor_id"] == "local-command":
        result = run_local_command(project_dir, task, lease)
    elif task["executor_id"] in {"codex-cli-host", "claude-cli-host"}:
        result = run_host_cli_adapter(project_dir, task, lease, allow_provider_call=allow_provider_call)
    else:
        raise ValueError(f"unsupported executor_id: {task['executor_id']}")

    if result["status"] == "completed":
        final_status = "completed"
    elif result["status"] in {"needs_human", "auth_required", "unsupported"}:
        final_status = "needs_human"
    else:
        final_status = "failed"
    update_lease(project_dir, lease, final_status)
    append_jsonl(
        service_path(project_dir, QUEUE_FILE),
        {
            "event_type": "task_completed" if final_status == "completed" else "task_needs_human" if final_status == "needs_human" else "task_failed",
            "timestamp": iso(utc_now()),
            "task_id": task["task_id"],
            "lease_id": lease.lease_id,
            "result": result,
        },
    )
    return {"ok": final_status in {"completed", "needs_human"}, "status": final_status, "task_id": task["task_id"], "lease_id": lease.lease_id, "result": result}


def queue_drain(project_dir: Path) -> dict[str, Any]:
    expired = expire_stale_leases(project_dir)
    tasks = build_task_state(project_dir)
    leases = build_lease_state(project_dir)
    counts = {"pending": 0, "completed": 0, "failed": 0, "needs_human": 0}
    for task in tasks.values():
        status = task.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    active = active_task_ids(project_dir)
    return {
        "ok": True,
        "status": "drained",
        "task_count": len(tasks),
        "lease_count": len(leases),
        "expired_leases": expired,
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

    submit = subparsers.add_parser("submit", help="Submit a service-control-plane task.")
    add_common(submit)
    submit.add_argument("--kind", required=True, choices=("local-command", "provider"))
    submit.add_argument("--command", dest="task_command")
    submit.add_argument("--prompt")
    submit.add_argument("--task-id")
    submit.add_argument("--requested-by", default="operator")
    submit.add_argument("--executor", default="local-command", choices=("local-command", "codex-cli-host", "claude-cli-host"))
    submit.add_argument("--dry-run", action="store_true")

    worker = subparsers.add_parser("worker-run-once", help="Claim and execute one pending local task.")
    add_common(worker)
    worker.add_argument("--executor", default="local-command", choices=("local-command", "codex-cli-host", "claude-cli-host"))
    worker.add_argument("--ttl-seconds", type=int, default=300)
    worker.add_argument("--worker-id")
    worker.add_argument("--simulate-crash-after-lease", action="store_true")
    worker.add_argument("--allow-provider-call", action="store_true")

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
                prompt=args.prompt,
                task_id=args.task_id,
                requested_by=args.requested_by,
                executor_id=args.executor,
                dry_run=args.dry_run,
            )
        elif args.subcommand == "worker-run-once":
            payload = worker_run_once(
                project_dir,
                ttl_seconds=args.ttl_seconds,
                worker_id=args.worker_id,
                simulate_crash_after_lease=args.simulate_crash_after_lease,
                allow_provider_call=args.allow_provider_call,
            )
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
