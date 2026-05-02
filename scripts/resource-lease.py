#!/usr/bin/env python3
# SCOPE: both
"""Cooperative resource lease primitive for concurrent agents."""
from __future__ import annotations
import argparse, json, os, socket, sys, time
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.concurrency_safety import load_concurrency_safety_config, project_runtime_dir

def project_dir(args: argparse.Namespace) -> Path:
    value = args.project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).resolve()

def safe_name(resource: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in resource.strip())
    return cleaned.strip("-") or "unnamed"

def leases_dir(project: Path) -> Path:
    path = project_runtime_dir(project) / "resource-leases"
    path.mkdir(parents=True, exist_ok=True)
    return path

def manifest_path(project: Path, resource: str) -> Path:
    return leases_dir(project) / f"{safe_name(resource)}.json"

def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def lease_expired(manifest: dict[str, Any], now: float) -> bool:
    expires_at = manifest.get("expires_at")
    return not isinstance(expires_at, (int, float)) or now >= float(expires_at)

def acquire(args: argparse.Namespace) -> int:
    project = project_dir(args)
    cfg = load_concurrency_safety_config(str(project / "cognitive-os.yaml"))
    ttl = args.ttl_seconds or cfg.resource_leases.default_ttl_seconds
    path = manifest_path(project, args.resource)
    now = time.time()
    existing = read_json(path) if path.exists() else None
    if existing and not lease_expired(existing, now):
        print(json.dumps({"status": "blocked", "resource": args.resource, "held_by": existing}, sort_keys=True))
        return 2
    manifest = {"resource": args.resource, "safe_resource": safe_name(args.resource), "agent_id": args.agent_id, "session_id": args.session_id, "reason": args.reason, "pid": os.getpid(), "host": socket.gethostname(), "created_at": now, "expires_at": now + ttl, "ttl_seconds": ttl}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    print(json.dumps({"status": "acquired", "lease": manifest}, sort_keys=True))
    return 0

def release(args: argparse.Namespace) -> int:
    project = project_dir(args)
    path = manifest_path(project, args.resource)
    existing = read_json(path) if path.exists() else None
    if not existing:
        print(json.dumps({"status": "absent", "resource": args.resource}, sort_keys=True)); return 0
    if args.agent_id and existing.get("agent_id") != args.agent_id:
        print(json.dumps({"status": "blocked", "resource": args.resource, "held_by": existing}, sort_keys=True)); return 2
    path.unlink()
    print(json.dumps({"status": "released", "resource": args.resource}, sort_keys=True)); return 0

def check(args: argparse.Namespace) -> int:
    project = project_dir(args); path = manifest_path(project, args.resource); existing = read_json(path) if path.exists() else None; now = time.time()
    if not existing or lease_expired(existing, now):
        print(json.dumps({"status": "free", "resource": args.resource}, sort_keys=True)); return 0
    print(json.dumps({"status": "held", "resource": args.resource, "held_by": existing}, sort_keys=True)); return 2

def status(args: argparse.Namespace) -> int:
    project = project_dir(args); now = time.time(); leases = []
    for path in sorted(leases_dir(project).glob("*.json")):
        manifest = read_json(path)
        if manifest:
            manifest["expired"] = lease_expired(manifest, now); leases.append(manifest)
    print(json.dumps({"project_dir": str(project), "leases": leases}, sort_keys=True)); return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--project-dir"); sub = parser.add_subparsers(dest="command", required=True)
    acq = sub.add_parser("acquire"); acq.add_argument("resource"); acq.add_argument("--agent-id", required=True); acq.add_argument("--session-id", required=True); acq.add_argument("--reason", required=True); acq.add_argument("--ttl-seconds", type=int); acq.set_defaults(func=acquire)
    rel = sub.add_parser("release"); rel.add_argument("resource"); rel.add_argument("--agent-id"); rel.set_defaults(func=release)
    chk = sub.add_parser("check"); chk.add_argument("resource"); chk.set_defaults(func=check)
    stat = sub.add_parser("status"); stat.set_defaults(func=status)
    return parser

def main() -> int:
    args = build_parser().parse_args(); return int(args.func(args))
if __name__ == "__main__":
    raise SystemExit(main())
