#!/usr/bin/env python3
# SCOPE: os-only
"""ADR-184 local cosd daemon for critical-surface intent arbitration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.intent_arbiter import (  # noqa: E402
    atomic_write_json,
    pid_path,
    process_once,
    result_path,
    runtime_dir,
    started_path,
    status,
    stop_path,
    submit_intent,
    utc_now_iso,
)


def resolve_project_dir(value: str | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    for env_name in ("COGNITIVE_OS_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR"):
        env_value = os.environ.get(env_name)
        if env_value:
            return Path(env_value).expanduser().resolve()
    return Path.cwd().resolve()


def emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, sort_keys=True))
    else:
        state = payload.get("status") or ("ok" if payload.get("ok") else "error")
        detail = payload.get("reason") or payload.get("pid") or payload.get("intent_queue_depth") or ""
        print(f"{state}: {detail}")


def start_daemon(project_dir: Path, *, interval_seconds: float) -> dict[str, Any]:
    current = status(project_dir)
    if current["status"] == "running":
        return {**current, "ok": True, "reason": "already running"}
    runtime_dir(project_dir).mkdir(parents=True, exist_ok=True)
    try:
        stop_path(project_dir).unlink()
    except FileNotFoundError:
        pass
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--project-dir",
        str(project_dir),
        "loop",
        "--interval-seconds",
        str(interval_seconds),
    ]
    proc = subprocess.Popen(
        command,
        cwd=str(REPO_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(0.15)
    payload = status(project_dir)
    if payload["status"] != "running":
        payload.update({"ok": False, "reason": f"daemon failed to start; pid={proc.pid}"})
    else:
        payload["ok"] = True
    return payload


def stop_daemon(project_dir: Path, *, timeout_seconds: float = 5.0) -> dict[str, Any]:
    before = status(project_dir)
    runtime_dir(project_dir).mkdir(parents=True, exist_ok=True)
    stop_path(project_dir).write_text(utc_now_iso() + "\n", encoding="utf-8")
    pid = before.get("pid")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current = status(project_dir)
        if current["status"] == "stopped":
            return {**current, "ok": True, "reason": "stopped"}
        time.sleep(0.05)
    if isinstance(pid, int):
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            pass
    return {**status(project_dir), "ok": True, "reason": "stop requested"}


def loop(project_dir: Path, *, interval_seconds: float) -> int:
    runtime_dir(project_dir).mkdir(parents=True, exist_ok=True)
    atomic_write_json(pid_path(project_dir), {"pid": os.getpid(), "updated_at": utc_now_iso()})
    atomic_write_json(started_path(project_dir), {"started_at": utc_now_iso(), "started_epoch": time.time()})
    try:
        while not stop_path(project_dir).exists():
            process_once(project_dir)
            time.sleep(max(0.05, interval_seconds))
    finally:
        for path in (pid_path(project_dir), started_path(project_dir)):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", help="Project root; defaults to cwd/env project root.")
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--interval-seconds", type=float, default=0.1)

    subparsers.add_parser("stop")
    subparsers.add_parser("status")

    loop_parser = subparsers.add_parser("loop")
    loop_parser.add_argument("--interval-seconds", type=float, default=0.1)

    once = subparsers.add_parser("process-once")
    once.add_argument("--limit", type=int)

    submit = subparsers.add_parser("submit-intent")
    submit.add_argument("--kind", required=True, choices=("adr-number-request", "adr-tombstone-request"))
    submit.add_argument("--intent-id")
    submit.add_argument("--session-id", default=os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or "manual")
    submit.add_argument("--topic")
    submit.add_argument("--filename-stem")
    submit.add_argument("--adr-number", type=int)
    submit.add_argument("--candidate-filename")
    submit.add_argument("--wait", action="store_true")
    submit.add_argument("--timeout-seconds", type=float, default=5.0)
    return parser


def wait_for_result(project_dir: Path, intent_id: str, *, timeout_seconds: float) -> dict[str, Any] | None:
    path = result_path(project_dir, intent_id)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)
    try:
        if args.command == "start":
            payload = start_daemon(project_dir, interval_seconds=args.interval_seconds)
        elif args.command == "stop":
            payload = stop_daemon(project_dir)
        elif args.command == "status":
            payload = status(project_dir)
        elif args.command == "loop":
            return loop(project_dir, interval_seconds=args.interval_seconds)
        elif args.command == "process-once":
            rows = process_once(project_dir, limit=args.limit)
            payload = {"ok": True, "status": "processed", "processed_count": len(rows), "results": rows}
        elif args.command == "submit-intent":
            context: dict[str, Any] = {}
            if args.topic:
                context["topic"] = args.topic
            if args.filename_stem:
                context["filename_stem"] = args.filename_stem
            if args.adr_number is not None:
                context["adr_number"] = args.adr_number
            if args.candidate_filename:
                context["candidate_filename"] = args.candidate_filename
            payload = submit_intent(project_dir, kind=args.kind, session_id=args.session_id, context=context, intent_id=args.intent_id)
            if args.wait:
                result = wait_for_result(project_dir, payload["intent"]["id"], timeout_seconds=args.timeout_seconds)
                payload["result"] = result
                payload["status"] = "decided" if result else "submitted"
        else:
            raise ValueError(f"unknown command: {args.command}")
    except Exception as exc:
        payload = {"ok": False, "status": "error", "reason": str(exc)}
        emit(payload, json_output=args.json)
        return 2
    emit(payload, json_output=args.json)
    return 0 if payload.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
