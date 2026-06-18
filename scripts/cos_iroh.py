#!/usr/bin/env python3
"""Optional Iroh transport contract helpers for Cognitive OS.

This module intentionally does not vendor or require Iroh. It provides a
safe, disabled-by-default contract surface and a local loopback backend used by
unit/integration tests until an operator explicitly installs/enables a real
Iroh runtime.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import importlib.util
import json
import os
import secrets
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterable

SCHEMA_DOCTOR = "cos-iroh-doctor/v1"
SCHEMA_PING = "cos-iroh-ping/v1"
SCHEMA_BUS = "cos-agent-bus-iroh-adapter/v1"
DEFAULT_BACKEND = "local-loopback-contract"
DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "backend": DEFAULT_BACKEND,
    "relay_mode": "disabled",
    "allow_public_relays": False,
    "allow_peers": [],
}
SAFE_BUS_EVENTS = {"heartbeat", "status", "message"}
DESTRUCTIVE_WORDS = {
    "exec",
    "execute",
    "shell",
    "bash",
    "write",
    "delete",
    "remove",
    "rm",
    "unlink",
    "git-push",
    "push",
    "deploy",
    "release",
}


class IrohContractError(ValueError):
    """Raised for invalid optional-Iroh contract input."""


@dataclasses.dataclass(frozen=True)
class LocalContractKeypair:
    """Local test-contract identity; not a real Iroh private key."""

    public_key: str
    secret_key: str
    key_type: str = "cos-local-contract-ed25519-placeholder"

    @classmethod
    def generate(cls) -> "LocalContractKeypair":
        secret = secrets.token_hex(32)
        public = hashlib.sha256(bytes.fromhex(secret)).hexdigest()
        return cls(public_key=public, secret_key=secret)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocalContractKeypair":
        public = str(data.get("public_key", ""))
        secret = str(data.get("secret_key", ""))
        key_type = str(data.get("key_type", "cos-local-contract-ed25519-placeholder"))
        validate_public_key(public)
        if len(secret) != 64 or not _is_hex(secret):
            raise IrohContractError("secret_key must be 64 hex characters")
        expected = hashlib.sha256(bytes.fromhex(secret)).hexdigest()
        if public != expected:
            raise IrohContractError("public_key does not match secret_key")
        return cls(public_key=public, secret_key=secret, key_type=key_type)

    def to_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)


def _is_hex(value: str) -> bool:
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def validate_public_key(value: str) -> str:
    if len(value) != 64 or not _is_hex(value):
        raise IrohContractError("peer public key must be 64 lowercase hex characters")
    if value.lower() != value:
        raise IrohContractError("peer public key must use lowercase hex")
    return value


def project_dir_from(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    return Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()


def iroh_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "iroh"


def config_path(project_dir: Path) -> Path:
    return iroh_dir(project_dir) / "config.json"


def keypair_path(project_dir: Path) -> Path:
    return iroh_dir(project_dir) / "keypair.json"


def bus_ledger_path(project_dir: Path) -> Path:
    return iroh_dir(project_dir) / "agent-bus.jsonl"


def load_config(project_dir: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    path = config_path(project_dir)
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if not isinstance(loaded, dict):
            raise IrohContractError("iroh config must be a JSON object")
        config.update(loaded)
    if os.environ.get("COS_IROH_ENABLED") == "1":
        config["enabled"] = True
    config["allow_peers"] = sorted({str(p) for p in config.get("allow_peers", [])})
    for peer in config["allow_peers"]:
        validate_public_key(peer)
    if config.get("relay_mode") not in {"disabled", "local", "public"}:
        raise IrohContractError("relay_mode must be disabled, local, or public")
    if config.get("backend") not in {DEFAULT_BACKEND, "iroh-python", "iroh-cli"}:
        raise IrohContractError("backend must be local-loopback-contract, iroh-python, or iroh-cli")
    return config


def write_config(project_dir: Path, config: dict[str, Any]) -> None:
    path = config_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_or_create_keypair(project_dir: Path, create: bool) -> tuple[LocalContractKeypair | None, str]:
    path = keypair_path(project_dir)
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            return LocalContractKeypair.from_dict(json.load(fh)), "present"
    if not create:
        return None, "missing"
    path.parent.mkdir(parents=True, exist_ok=True)
    keypair = LocalContractKeypair.generate()
    path.write_text(json.dumps(keypair.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return keypair, "generated"


def backend_detection() -> dict[str, Any]:
    return {
        "iroh_python_available": importlib.util.find_spec("iroh") is not None,
        "iroh_binary": shutil.which("iroh"),
        "contract_backend_available": True,
    }


def ensure_peer_allowed(peer_key: str, allowed: Iterable[str]) -> None:
    validate_public_key(peer_key)
    allowed_set = set(allowed)
    if allowed_set and peer_key not in allowed_set:
        raise PermissionError("peer key is not allowlisted")


def _socket_json_roundtrip(server_key: LocalContractKeypair, client_key: LocalContractKeypair, allowed_peers: list[str]) -> dict[str, Any]:
    ready: dict[str, Any] = {}
    result: dict[str, Any] = {}

    def server() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            ready["addr"] = sock.getsockname()
            sock.settimeout(10)
            conn, _ = sock.accept()
            with conn:
                payload = json.loads(conn.recv(65536).decode("utf-8"))
                ensure_peer_allowed(str(payload.get("from")), allowed_peers)
                response = {
                    "type": "pong",
                    "from": server_key.public_key,
                    "to": payload.get("from"),
                    "transport_backend": DEFAULT_BACKEND,
                    "received": payload.get("type"),
                }
                conn.sendall(json.dumps(response).encode("utf-8"))

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while "addr" not in ready and time.time() < deadline:
        time.sleep(0.01)
    if "addr" not in ready:
        raise TimeoutError("local endpoint did not start")
    with socket.create_connection(ready["addr"], timeout=10) as sock:
        request = {
            "type": "ping",
            "from": client_key.public_key,
            "to": server_key.public_key,
            "transport_backend": DEFAULT_BACKEND,
        }
        sock.sendall(json.dumps(request).encode("utf-8"))
        result.update(json.loads(sock.recv(65536).decode("utf-8")))
    thread.join(timeout=10)
    return result


def run_self_ping() -> dict[str, Any]:
    server_key = LocalContractKeypair.generate()
    client_key = LocalContractKeypair.generate()
    response = _socket_json_roundtrip(server_key, client_key, [client_key.public_key])
    return {
        "status": "pass" if response.get("type") == "pong" else "fail",
        "transport_backend": DEFAULT_BACKEND,
        "server_public_key": server_key.public_key,
        "client_public_key": client_key.public_key,
        "response": response,
    }


def doctor(args: argparse.Namespace) -> int:
    project_dir = project_dir_from(args.project_dir)
    config = load_config(project_dir)
    if args.relay_mode:
        config["relay_mode"] = args.relay_mode
    keypair, key_status = load_or_create_keypair(project_dir, args.init_keypair)
    connectivity = {"status": "skipped", "reason": "self-test not requested"}
    if args.self_test:
        try:
            connectivity = run_self_ping()
        except Exception as exc:  # pragma: no cover - defensive reporting
            connectivity = {"status": "fail", "error": str(exc)}
    report = {
        "schema_version": SCHEMA_DOCTOR,
        "status": "pass" if connectivity.get("status") in {"pass", "skipped"} else "fail",
        "enabled": bool(config.get("enabled")),
        "backend": config.get("backend"),
        "relay_mode": config.get("relay_mode"),
        "allow_public_relays": bool(config.get("allow_public_relays")),
        "dependency_detection": backend_detection(),
        "keypair": {
            "status": key_status,
            "public_key": keypair.public_key if keypair else None,
            "path": str(keypair_path(project_dir)),
        },
        "connectivity": connectivity,
        "safety": {
            "disabled_by_default": True,
            "remote_execution": False,
            "destructive_writes": False,
            "allowlist_required_when_configured": True,
        },
    }
    emit(report, args.json)
    return 0 if report["status"] == "pass" else 2


def ping(args: argparse.Namespace) -> int:
    if args.self_test:
        report = {"schema_version": SCHEMA_PING, **run_self_ping()}
        emit(report, args.json)
        return 0 if report["status"] == "pass" else 2
    project_dir = project_dir_from(args.project_dir)
    config = load_config(project_dir)
    if not config.get("enabled"):
        report = {"schema_version": SCHEMA_PING, "status": "disabled", "enabled": False, "reason": "COS Iroh adapter is disabled by default"}
        emit(report, args.json)
        return 2
    if not args.peer:
        raise IrohContractError("--peer is required unless --self-test is used")
    validate_public_key(args.peer)
    ensure_peer_allowed(args.peer, config.get("allow_peers", []))
    report = {
        "schema_version": SCHEMA_PING,
        "status": "blocked",
        "reason": "real Iroh backend execution is not implemented in this advisory slice",
        "peer": args.peer,
        "transport_backend": config.get("backend"),
    }
    emit(report, args.json)
    return 2


def append_bus_event(project_dir: Path, event: dict[str, Any]) -> Path:
    path = bus_ledger_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
    return path


def is_destructive_event(event_type: str, message: str) -> bool:
    text = f"{event_type} {message}".lower()
    return any(word in text for word in DESTRUCTIVE_WORDS)


def agent_bus_adapter(args: argparse.Namespace) -> int:
    if args.self_test:
        with tempfile.TemporaryDirectory(prefix="cos-iroh-bus-") as tmp:
            project_dir = Path(tmp)
            peer = LocalContractKeypair.generate().public_key
            records = []
            for event_type, message in [("heartbeat", "alive"), ("status", "idle"), ("message", "hello")]:
                records.append(record_bus_event(project_dir, peer, [peer], event_type, "self-test", message))
            report = {"schema_version": SCHEMA_BUS, "status": "pass", "records": records, "transport_backend": DEFAULT_BACKEND}
            emit(report, args.json)
            return 0
    project_dir = project_dir_from(args.project_dir)
    config = load_config(project_dir)
    if not config.get("enabled"):
        report = {"schema_version": SCHEMA_BUS, "status": "disabled", "enabled": False, "reason": "COS Iroh adapter is disabled by default"}
        emit(report, args.json)
        return 2
    allowed = list(config.get("allow_peers", [])) + list(args.allow_peer or [])
    record = record_bus_event(project_dir, args.peer_key, allowed, args.event, args.agent_id, args.message)
    report = {"schema_version": SCHEMA_BUS, "status": "pass", "record": record, "transport_backend": config.get("backend")}
    emit(report, args.json)
    return 0


def record_bus_event(project_dir: Path, peer_key: str, allowed: list[str], event_type: str, agent_id: str, message: str) -> dict[str, Any]:
    if event_type not in SAFE_BUS_EVENTS:
        raise PermissionError("agent bus iroh adapter only supports heartbeat, status, and message events")
    if is_destructive_event(event_type, message):
        raise PermissionError("agent bus iroh adapter rejects destructive actions")
    ensure_peer_allowed(peer_key, allowed)
    event = {
        "schema_version": SCHEMA_BUS,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "peer_key": peer_key,
        "agent_id": agent_id,
        "event": event_type,
        "message": message,
        "remote_execution": False,
        "destructive_writes": False,
    }
    ledger = append_bus_event(project_dir, event)
    return {**event, "ledger": str(ledger)}


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload.get('schema_version')}: {payload.get('status')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optional COS Iroh transport contract helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="verify optional Iroh adapter readiness")
    p.add_argument("--project-dir")
    p.add_argument("--init-keypair", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--relay-mode", choices=["disabled", "local", "public"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=doctor)

    p = sub.add_parser("ping", help="ping a COS peer by public key or run local contract self-test")
    p.add_argument("--project-dir")
    p.add_argument("--peer")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=ping)

    p = sub.add_parser("agent-bus-adapter", help="append safe iroh agent bus events")
    p.add_argument("--project-dir")
    p.add_argument("--peer-key", default="")
    p.add_argument("--allow-peer", action="append", default=[])
    p.add_argument("--event", default="heartbeat")
    p.add_argument("--agent-id", default="cos-agent")
    p.add_argument("--message", default="alive")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=agent_bus_adapter)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (IrohContractError, PermissionError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        schema = {"doctor": SCHEMA_DOCTOR, "ping": SCHEMA_PING, "agent-bus-adapter": SCHEMA_BUS}.get(getattr(args, "command", ""), "cos-iroh/v1")
        emit({"schema_version": schema, "status": "blocked", "error": str(exc)}, getattr(args, "json", False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
