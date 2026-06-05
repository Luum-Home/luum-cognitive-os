#!/usr/bin/env python3
# SCOPE: os-only
"""Credential-safe allowlisted script runner.

This runner is intentionally narrow: it reads only allowlisted keys from a local
env file, forces safe child-process flags, captures stdout/stderr, redacts secret
values before printing anything to the agent/model, and writes a redacted audit
record. It does not expose env-file contents to the caller.
"""

from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import iso_utc_z as _utc
from lib.script_helpers import read_yaml_required as _load_manifest
from lib.script_helpers import sha256_file as _sha256_file

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any
from urllib.parse import quote

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "credential-safe-scripts.yaml"
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|auth[_-]?token|secret|password)=([^\s]+)"),
]
DEFAULT_INHERITED_ENV_KEYS = {"PATH", "HOME", "USER", "TMPDIR", "LANG", "LC_ALL"}


@dataclass(frozen=True)
class RunResult:
    script_id: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    redaction_count: int
    loaded_keys: list[str]
    audit_path: str
    command_sha256: str


def _script_entry(script_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    for entry in manifest.get("scripts", []):
        if entry.get("id") == script_id:
            return entry
    raise SystemExit(f"unsupported credential-safe script id: {script_id}")


def _parse_env_file(path: Path, allowed_keys: set[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in allowed_keys:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value
    return values


def _resolve_allowed_env_file(project_dir: Path, env_file: Path, allowed_files: set[str]) -> Path:
    relative_name = env_file.as_posix()
    if env_file.is_absolute():
        try:
            relative_name = env_file.resolve().relative_to(project_dir).as_posix()
        except ValueError as exc:
            raise SystemExit("env file must be inside the project directory") from exc
    if relative_name not in allowed_files:
        raise SystemExit(f"env file is not allowlisted for this credential-safe script: {relative_name}")
    env_path = (project_dir / relative_name).resolve()
    try:
        env_path.relative_to(project_dir)
    except ValueError as exc:
        raise SystemExit("env file must resolve inside the project directory") from exc
    return env_path


def _sanitized_child_env(entry: dict[str, Any], allowed: set[str], loaded: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    inherited = DEFAULT_INHERITED_ENV_KEYS | set(entry.get("inherited_env_keys", []))
    child_env: dict[str, str] = {}
    for key in sorted(inherited):
        if key in os.environ:
            child_env[key] = os.environ[key]
    parent_allowed: dict[str, str] = {}
    for key in sorted(allowed):
        if key in os.environ:
            parent_allowed[key] = os.environ[key]
    child_env.update(parent_allowed)
    child_env.update(loaded)
    child_env.update({str(k): str(v) for k, v in entry.get("forced_env", {}).items()})
    secret_values = list(parent_allowed.values()) + list(loaded.values())
    return child_env, secret_values


def _verify_command_integrity(project_dir: Path, entry: dict[str, Any]) -> str:
    integrity = entry.get("command_integrity")
    if not integrity:
        raise SystemExit("credential-safe script has no command integrity pin")
    rel_path = Path(str(integrity["path"]))
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise SystemExit("credential-safe command integrity path must be repo-relative")
    target = (project_dir / rel_path).resolve()
    try:
        target.relative_to(project_dir)
    except ValueError as exc:
        raise SystemExit("credential-safe command integrity path must resolve inside the project directory") from exc
    expected = str(integrity["sha256"])
    actual = _sha256_file(target)
    if actual != expected:
        raise SystemExit(
            "credential-safe command integrity mismatch: "
            f"{rel_path.as_posix()} sha256={actual} expected={expected}"
        )
    return actual


def _secret_variants(secret_values: list[str]) -> list[str]:
    variants: set[str] = set()
    for value in secret_values:
        if not value:
            continue
        variants.add(value)
        encoded = value.encode("utf-8")
        variants.add(base64.b64encode(encoded).decode("ascii"))
        variants.add(base64.urlsafe_b64encode(encoded).decode("ascii"))
        variants.add(encoded.hex())
        variants.add(quote(value, safe=""))
    return sorted(variants, key=len, reverse=True)


def _bounded(text: str, max_chars: int) -> tuple[str, int]:
    if len(text) <= max_chars:
        return text, 0
    marker = f"\n[TRUNCATED {len(text) - max_chars} chars]\n"
    return text[:max_chars] + marker, 1


def _redact(text: str, secret_values: list[str]) -> tuple[str, int]:
    redactions = 0
    safe = text
    for value in sorted({v for v in secret_values if v}, key=len, reverse=True):
        if value in safe:
            safe = safe.replace(value, "[REDACTED]")
            redactions += 1
    for pattern in SECRET_PATTERNS:
        safe, count = pattern.subn(lambda m: f"{m.group(1)}=[REDACTED]" if m.lastindex and m.lastindex >= 2 else "[REDACTED]", safe)
        redactions += count
    return safe, redactions


def _write_audit(project_dir: Path, entry: dict[str, Any], audit_rel: str) -> Path:
    audit_path = project_dir / audit_rel
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return audit_path


def run_credential_safe(
    script_id: str,
    *,
    project_dir: Path,
    env_file: Path,
    approved: bool,
    manifest_path: Path = MANIFEST,
) -> RunResult:
    manifest = _load_manifest(manifest_path)
    entry = _script_entry(script_id, manifest)
    if entry.get("requires_explicit_approval") and not approved and os.environ.get("COS_ALLOW_CREDENTIAL_SAFE_ENV") != "1":
        raise SystemExit("credential-safe env-file execution requires --approve or COS_ALLOW_CREDENTIAL_SAFE_ENV=1")

    project_dir = project_dir.resolve()
    allowed = set(entry.get("allowed_env_keys", []))
    allowed_files = set(entry.get("allowed_env_files", []))
    if not allowed_files:
        raise SystemExit("credential-safe script has no allowlisted env files")
    env_path = _resolve_allowed_env_file(project_dir, env_file, allowed_files)
    loaded = _parse_env_file(env_path, allowed)
    child_env, secret_values = _sanitized_child_env(entry, allowed, loaded)
    command_sha256 = _verify_command_integrity(project_dir, entry)

    command = [str(part) for part in entry["command"]]
    proc = subprocess.run(
        command,
        cwd=project_dir,
        env=child_env,
        text=True,
        capture_output=True,
        timeout=600,
    )
    max_output_chars = int(entry.get("max_output_chars", 20000))
    stdout, out_count = _redact(proc.stdout, _secret_variants(secret_values))
    stderr, err_count = _redact(proc.stderr, _secret_variants(secret_values))
    stdout, stdout_truncated = _bounded(stdout, max_output_chars)
    stderr, stderr_truncated = _bounded(stderr, max_output_chars)
    redaction_count = out_count + err_count
    audit_entry = {
        "timestamp": _utc(),
        "script_id": script_id,
        "command": command,
        "returncode": proc.returncode,
        "command_sha256": command_sha256,
        "loaded_keys": sorted(loaded.keys()),
        "forced_env_keys": sorted(entry.get("forced_env", {}).keys()),
        "redaction_count": redaction_count,
        "truncation_count": stdout_truncated + stderr_truncated,
        "stdout_chars": len(stdout),
        "stderr_chars": len(stderr),
        "status": "success" if proc.returncode == 0 else "failed",
    }
    audit_path = _write_audit(project_dir, audit_entry, entry["audit_log"])
    return RunResult(
        script_id=script_id,
        command=command,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        redaction_count=redaction_count,
        loaded_keys=sorted(loaded.keys()),
        audit_path=str(audit_path),
        command_sha256=command_sha256,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an allowlisted script with credential-safe env-file handling")
    parser.add_argument("script_id")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--approve", action="store_true", help="Explicit operator approval for env-file use")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_credential_safe(
        args.script_id,
        project_dir=Path(args.project_dir),
        env_file=Path(args.env_file),
        approved=args.approve,
        manifest_path=Path(args.manifest),
    )
    if args.json:
        print(json.dumps({
            "script_id": result.script_id,
            "returncode": result.returncode,
            "loaded_keys": result.loaded_keys,
            "command_sha256": result.command_sha256,
            "redaction_count": result.redaction_count,
            "audit_path": result.audit_path,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }, sort_keys=True))
    else:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        print(f"\ncredential-safe-run: script={result.script_id} returncode={result.returncode} redactions={result.redaction_count} audit={result.audit_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
