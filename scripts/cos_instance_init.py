#!/usr/bin/env python3
# SCOPE: os-only
"""Provision or dry-run an operational Cognitive OS instance profile.

This installer is intentionally separate from scripts/cos_init.py. cos_init.py
projects COS into consumer repositories; this script builds an operational SO
instance such as local maintainer runtime or Docker/headless runtime.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "cos-instance-profiles.yaml"
IMPLEMENTED_PROFILES = {"local", "docker-headless"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def profile_by_id(manifest: dict[str, Any], profile_id: str) -> dict[str, Any]:
    for profile in manifest["profiles"]:
        if profile["id"] == profile_id:
            return profile
    raise ValueError(f"unknown profile: {profile_id}")


def which_status(binary: str) -> str:
    return "present" if shutil.which(binary) else "missing"


def docker_compose_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(["docker", "compose", "version"], text=True, capture_output=True, timeout=10, check=False)
    except Exception:
        return False
    return result.returncode == 0


def requirement_status(requirement: str, project_dir: Path) -> dict[str, str]:
    if requirement == "python3":
        status = which_status("python3")
    elif requirement == "git":
        status = which_status("git")
    elif requirement == "docker":
        status = which_status("docker")
    elif requirement == "docker-compose-v2":
        status = "present" if docker_compose_available() else "missing"
    elif requirement in {"explicit-loopback-or-socket-auth", "allowlisted-commands", "provider-auth-probes", "cost-approval-gate"}:
        status = "planned"
    elif requirement in {"repo-checkout", "service-manager", "explicit-provider-auth-mode", "artifact-storage", "audit-log-export"}:
        status = "planned"
    elif requirement in {"namespace", "external-secrets-or-provider-cloud-auth", "queue-backend", "artifact-volume", "readiness-liveness-probes"}:
        status = "planned"
    else:
        status = "unknown"
    return {"requirement": requirement, "status": status}


def build_plan(profile: dict[str, Any], project_dir: Path, *, run_smoke: bool = False) -> dict[str, Any]:
    instance_dir = project_dir / ".cognitive-os" / "instances" / profile["id"]
    requirement_rows = [requirement_status(req, project_dir) for req in profile.get("requires", [])]
    planned = profile["status"] != "implemented"
    blocked = [row for row in requirement_rows if row["status"] in {"missing", "unknown"}]
    plan = {
        "schema_version": "cos-instance-init.plan.v1",
        "generated_at": utc_now(),
        "profile": profile["id"],
        "display_name": profile["display_name"],
        "status": "planned-only" if planned else "ready-to-write" if not blocked else "requirements-missing",
        "target": profile["target"],
        "proof_level": profile["proof_level"],
        "project_dir": str(project_dir),
        "instance_dir": str(instance_dir),
        "entrypoints": profile.get("entrypoints", []),
        "writes": profile.get("writes", []),
        "requirements": requirement_rows,
        "optional_requires": profile.get("optional_requires", []),
        "smoke_commands": profile.get("smoke_commands", []),
        "evidence_sources": profile.get("evidence_sources", []),
        "blocked_behaviors": load_manifest().get("blocked_behaviors", []),
        "notes": [],
    }
    if planned:
        plan["notes"].append("Profile is planned; write is intentionally disabled until proof is implemented.")
    if profile["id"] == "docker-headless":
        for rel in ["docker/cos-worker/docker-compose.yml", "scripts/cos-headless-service-drill"]:
            exists = (project_dir / rel).exists()
            plan.setdefault("file_checks", []).append({"path": rel, "status": "present" if exists else "missing"})
    if run_smoke:
        plan["notes"].append("Smoke execution is delegated to the listed smoke_commands; run them explicitly for evidence.")
    return plan


def write_instance(profile: dict[str, Any], project_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    if profile["id"] not in IMPLEMENTED_PROFILES:
        return {"ok": False, "status": "write-blocked", "reason": f"profile {profile['id']} is not implemented"}
    if plan["status"] == "requirements-missing":
        return {"ok": False, "status": "requirements-missing", "missing": [r for r in plan["requirements"] if r["status"] in {"missing", "unknown"}]}

    instance_dir = Path(plan["instance_dir"])
    runtime_dir = project_dir / ".cognitive-os" / "runtime"
    service_dir = project_dir / ".cognitive-os" / "service"
    instance_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    service_dir.mkdir(parents=True, exist_ok=True)

    instance = {
        "schema_version": "cos-instance.v1",
        "created_at": utc_now(),
        "profile": profile["id"],
        "target": profile["target"],
        "proof_level": profile["proof_level"],
        "entrypoints": profile.get("entrypoints", []),
        "approval_policy": "propose-only",
        "credential_policy": "no-credential-store-scraping",
        "smoke_commands": profile.get("smoke_commands", []),
    }
    (instance_dir / "instance.json").write_text(json.dumps(instance, indent=2, sort_keys=True) + "\n")
    (instance_dir / "commands.md").write_text(
        "# COS Instance Commands\n\n"
        f"Profile: `{profile['id']}`\n\n"
        "## Smoke commands\n\n"
        + "\n".join(f"```bash\n{cmd}\n```" for cmd in profile.get("smoke_commands", []))
        + "\n",
        encoding="utf-8",
    )
    return {"ok": True, "status": "written", "instance_dir": str(instance_dir), "files": [str(instance_dir / "instance.json"), str(instance_dir / "commands.md")]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Instance profile id from manifests/cos-instance-profiles.yaml")
    parser.add_argument("--project-dir", default=".", help="Repository/project directory to initialize; defaults to cwd")
    parser.add_argument("--dry-run", action="store_true", help="Emit plan without writing. Default unless --write is set.")
    parser.add_argument("--write", action="store_true", help="Write instance metadata for implemented profiles.")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--run-smoke", action="store_true", help="Do not execute smoke automatically; annotate plan with smoke handoff")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = Path(args.project_dir).expanduser().resolve()
    manifest = load_manifest()
    try:
        profile = profile_by_id(manifest, args.profile)
    except ValueError as exc:
        payload = {"ok": False, "status": "error", "reason": str(exc)}
        print(json.dumps(payload, sort_keys=True) if args.json else payload["reason"])
        return 2

    plan = build_plan(profile, project_dir, run_smoke=args.run_smoke)
    payload: dict[str, Any]
    if args.write:
        result = write_instance(profile, project_dir, plan)
        payload = {"ok": bool(result.get("ok")), "mode": "write", "plan": plan, "result": result}
    else:
        payload = {"ok": True, "mode": "dry-run", "plan": plan}

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"{payload['mode']}: {plan['profile']} -> {plan['status']}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
