#!/usr/bin/env python3
# SCOPE: os-only
"""ADR-184 local cosd daemon for critical-surface intent arbitration."""
from __future__ import annotations

import argparse
import hmac
import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import UnixStreamServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cos_service_control_plane as service_control_plane  # noqa: E402

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


def resolve_project_dir(raw: str | None) -> Path:
    candidates = [raw, os.environ.get("COGNITIVE_OS_PROJECT_DIR"), os.environ.get("CODEX_PROJECT_DIR"), os.environ.get("CLAUDE_PROJECT_DIR")]
    for candidate in candidates:
        if candidate:
            return Path(candidate).expanduser().resolve()
    return Path.cwd().resolve()


def emit(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    detail = payload.get("reason") or payload.get("pid") or payload.get("intent_queue_depth") or ""
    print(f"cosd {payload.get('status', 'unknown')} {detail}".strip())


def start_daemon(project_dir: Path, *, interval_seconds: float) -> dict[str, Any]:
    current = status(project_dir)
    if current["status"] == "running":
        return {**current, "ok": True, "reason": "already running"}
    try:
        stop_path(project_dir).unlink()
    except FileNotFoundError:
        pass
    script = Path(__file__).resolve()
    proc = subprocess.Popen(
        [sys.executable, str(script), "--project-dir", str(project_dir), "loop", "--interval-seconds", str(interval_seconds)],
        cwd=str(project_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + 5
    payload = status(project_dir)
    while time.time() < deadline:
        payload = status(project_dir)
        if payload["status"] == "running":
            break
        time.sleep(0.05)
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



def api_audit_path(project_dir: Path) -> Path:
    return project_dir.resolve() / ".cognitive-os" / "cosd" / "api-audit.jsonl"


def append_api_audit(project_dir: Path, payload: dict[str, Any]) -> None:
    path = api_audit_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {key: value for key, value in payload.items() if key not in {"authorization", "token", "bearer"}}
    safe.setdefault("timestamp", utc_now_iso())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, sort_keys=True))
        handle.write("\n")


def is_local_bind_host(host: str) -> bool:
    normalized = host.strip().lower()
    return normalized in {"", "localhost", "127.0.0.1", "::1"}


def load_api_token(token_file: str | None) -> str | None:
    raw = token_file or os.environ.get("COSD_API_TOKEN_FILE")
    if not raw:
        return None
    token = Path(raw).expanduser().read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("cosd token file is empty")
    return token


def bearer_authorized(header: str | None, token: str | None) -> bool:
    if token is None:
        return True
    prefix = "Bearer "
    if not header or not header.startswith(prefix):
        return False
    supplied = header[len(prefix):].strip()
    return hmac.compare_digest(supplied, token)


def remote_policy_guard(host: str, *, allow_remote: bool, token: str | None) -> None:
    if is_local_bind_host(host):
        return
    if not allow_remote:
        raise ValueError("refusing non-local cosd bind without --allow-remote")
    if token is None:
        raise ValueError("refusing remote cosd bind without --token-file or COSD_API_TOKEN_FILE")

def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def make_handler(project_dir: Path, *, token: str | None = None, transport: str = "http") -> type[BaseHTTPRequestHandler]:
    class CosdHandler(BaseHTTPRequestHandler):
        server_version = "cosd-local-api/1"

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            return bearer_authorized(self.headers.get("Authorization"), token)

        def _reject_unauthorized(self, endpoint: str) -> None:
            append_api_audit(project_dir, {
                "event": "cosd.api.request",
                "transport": transport,
                "endpoint": endpoint,
                "method": self.command,
                "status": "unauthorized",
            })
            self._send(401, {"ok": False, "status": "unauthorized", "reason": "missing or invalid bearer token"})

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._send(200, {"ok": True, "status": "ok"})
                return
            if parsed.path == "/status":
                if not self._authorized():
                    self._reject_unauthorized(parsed.path)
                    return
                self._send(200, status(project_dir))
                return
            if parsed.path == "/tasks":
                if not self._authorized():
                    self._reject_unauthorized(parsed.path)
                    return
                self._send(200, service_control_plane.queue_drain(project_dir))
                return
            self._send(404, {"ok": False, "status": "not-found", "reason": f"unknown endpoint: {parsed.path}"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if not self._authorized():
                self._reject_unauthorized(parsed.path)
                return
            try:
                if parsed.path == "/process-once":
                    body = _read_json_body(self)
                    limit = body.get("limit")
                    rows = process_once(project_dir, limit=int(limit) if limit is not None else None)
                    append_api_audit(project_dir, {
                        "event": "cosd.api.request",
                        "transport": transport,
                        "endpoint": parsed.path,
                        "method": "POST",
                        "status": "processed",
                        "processed_count": len(rows),
                    })
                    self._send(200, {"ok": True, "status": "processed", "processed_count": len(rows), "results": rows})
                    return
                if parsed.path == "/submit-intent":
                    body = _read_json_body(self)
                    context = body.get("context") if isinstance(body.get("context"), dict) else {}
                    payload = submit_intent(
                        project_dir,
                        kind=str(body.get("kind") or ""),
                        session_id=str(body.get("session_id") or "api"),
                        context=context,
                        intent_id=str(body.get("intent_id")) if body.get("intent_id") else None,
                    )
                    processed_count = 0
                    if body.get("process") is True:
                        processed = process_once(project_dir)
                        processed_count = len(processed)
                        payload["processed"] = processed
                    append_api_audit(project_dir, {
                        "event": "cosd.api.request",
                        "transport": transport,
                        "endpoint": parsed.path,
                        "method": "POST",
                        "status": payload.get("status", "submitted"),
                        "intent_id": payload.get("intent", {}).get("id") if isinstance(payload.get("intent"), dict) else None,
                        "processed_count": processed_count,
                    })
                    self._send(200, payload)
                    return
                if parsed.path == "/tasks/submit":
                    body = _read_json_body(self)
                    kind = str(body.get("kind") or "")
                    if kind == "provider" and body.get("dry_run") is not True:
                        raise ValueError("provider tasks over cosd require dry_run=true and approval_policy=propose-only")
                    payload = service_control_plane.submit_task(
                        project_dir,
                        kind=kind,
                        command=str(body.get("command")) if body.get("command") is not None else None,
                        prompt=str(body.get("prompt")) if body.get("prompt") is not None else None,
                        task_id=str(body.get("task_id")) if body.get("task_id") else None,
                        requested_by=str(body.get("requested_by") or "cosd-api"),
                        executor_id=str(body.get("executor") or "local-command"),
                        dry_run=body.get("dry_run") is True,
                    )
                    append_api_audit(project_dir, {
                        "event": "cosd.api.request",
                        "transport": transport,
                        "endpoint": parsed.path,
                        "method": "POST",
                        "status": payload.get("status", "submitted"),
                        "task_id": payload.get("task", {}).get("task_id") if isinstance(payload.get("task"), dict) else None,
                        "task_kind": kind,
                    })
                    self._send(200, payload)
                    return
                if parsed.path == "/tasks/run-once":
                    body = _read_json_body(self)
                    if body.get("allow_provider_call") is True:
                        raise ValueError("cosd task API does not allow provider calls; run host provider adapters explicitly")
                    payload = service_control_plane.worker_run_once(
                        project_dir,
                        ttl_seconds=int(body.get("ttl_seconds") or 300),
                        worker_id=str(body.get("worker_id") or "cosd-api-worker"),
                        allow_provider_call=False,
                    )
                    append_api_audit(project_dir, {
                        "event": "cosd.api.request",
                        "transport": transport,
                        "endpoint": parsed.path,
                        "method": "POST",
                        "status": payload.get("status"),
                        "task_id": payload.get("task_id"),
                    })
                    self._send(200, payload)
                    return
                self._send(404, {"ok": False, "status": "not-found", "reason": f"unknown endpoint: {parsed.path}"})
            except Exception as exc:
                self._send(400, {"ok": False, "status": "error", "reason": str(exc)})

    return CosdHandler


def serve(project_dir: Path, *, host: str, port: int, allow_remote: bool = False, token_file: str | None = None) -> int:
    runtime_dir(project_dir).mkdir(parents=True, exist_ok=True)
    token = load_api_token(token_file)
    remote_policy_guard(host, allow_remote=allow_remote, token=token)
    server = ThreadingHTTPServer((host, port), make_handler(project_dir, token=token, transport="http"))
    bound_host, bound_port = server.server_address[:2]
    atomic_write_json(
        runtime_dir(project_dir) / "cosd-api.json",
        {
            "schema_version": "cosd-api.v1",
            "transport": "http",
            "host": bound_host,
            "port": bound_port,
            "base_url": f"http://{bound_host}:{bound_port}",
            "auth_required": token is not None,
            "remote_allowed": allow_remote,
            "updated_at": utc_now_iso(),
        },
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def serve_unix(project_dir: Path, *, socket_path: Path, token_file: str | None = None) -> int:
    runtime_dir(project_dir).mkdir(parents=True, exist_ok=True)
    socket_path = socket_path.expanduser().resolve()
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass
    token = load_api_token(token_file)
    server = UnixStreamServer(str(socket_path), make_handler(project_dir, token=token, transport="unix-http"))
    try:
        socket_path.chmod(0o600)
    except OSError:
        pass
    atomic_write_json(
        runtime_dir(project_dir) / "cosd-api.json",
        {
            "schema_version": "cosd-api.v1",
            "transport": "unix-http",
            "socket_path": str(socket_path),
            "auth_required": token is not None,
            "updated_at": utc_now_iso(),
        },
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        try:
            socket_path.unlink()
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

    api = subparsers.add_parser("serve")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8765)
    api.add_argument("--allow-remote", action="store_true", help="Allow non-local bind when token auth is configured")
    api.add_argument("--token-file", help="Bearer token file for protected API endpoints")

    unix_api = subparsers.add_parser("serve-unix")
    unix_api.add_argument("--socket", required=True, help="Unix domain socket path for HTTP-over-UDS")
    unix_api.add_argument("--token-file", help="Bearer token file for protected API endpoints")
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
        elif args.command == "serve":
            return serve(project_dir, host=args.host, port=args.port, allow_remote=args.allow_remote, token_file=args.token_file)
        elif args.command == "serve-unix":
            return serve_unix(project_dir, socket_path=Path(args.socket), token_file=args.token_file)
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
