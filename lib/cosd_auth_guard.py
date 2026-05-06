# SCOPE: both
"""cosd secure API guard policy for hook and audit use.

The runtime daemon enforces ADR-194 at startup. This module provides an agentic
primitive guard that catches unsafe commands and protected cosd config edits
before a tool call runs.
"""

from __future__ import annotations

import fnmatch
import json
import os
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
PROTECTED_COSD_GLOBS = (
    "infra/cosd/**",
    "scripts/cosd",
    "scripts/cos_daemon.py",
    "docs/adrs/ADR-193-cosd-local-network-api.md",
    "docs/adrs/ADR-194-cosd-secure-remote-api.md",
)
APPROVAL_ENV = "COS_ALLOW_COSD_AUTH_CONFIG_WRITE"


@dataclass(frozen=True)
class Finding:
    """Guard finding for a blocked cosd auth policy violation."""

    status: str
    reason: str
    evidence: str
    command: str = ""
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "reason": self.reason,
            "evidence": self.evidence,
            "command": self.command,
            "path": self.path,
        }


def _is_local_host(host: str) -> bool:
    return host.strip().lower() in LOCAL_HOSTS


def _option_value(tokens: list[str], option: str) -> str | None:
    for index, token in enumerate(tokens):
        if token == option and index + 1 < len(tokens):
            return tokens[index + 1]
        prefix = option + "="
        if token.startswith(prefix):
            return token[len(prefix) :]
    return None


def _has_option(tokens: list[str], option: str) -> bool:
    return option in tokens or any(token.startswith(option + "=") for token in tokens)


def _has_token_auth(tokens: list[str]) -> bool:
    if _has_option(tokens, "--token-file"):
        return True
    for token in tokens:
        if token.startswith("COSD_API_TOKEN_FILE=") and token.split("=", 1)[1].strip():
            return True
    return bool(os.environ.get("COSD_API_TOKEN_FILE"))


def _looks_like_cosd_invocation(tokens: list[str]) -> int | None:
    """Return index where cosd args begin, or None."""

    for index, token in enumerate(tokens):
        base = Path(token).name
        if base == "cosd":
            return index + 1
        if base == "cos_daemon.py":
            return index + 1
    return None


def inspect_command(command: str) -> Finding | None:
    """Return a finding if a Bash command violates ADR-194 remote auth policy."""

    if not command.strip():
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    start = _looks_like_cosd_invocation(tokens)
    if start is None:
        return None
    args = tokens[start:]
    if "serve" not in args:
        return None
    serve_index = args.index("serve")
    serve_args = args[serve_index + 1 :]
    host = _option_value(serve_args, "--host") or "127.0.0.1"
    if _is_local_host(host):
        return None
    if not _has_option(serve_args, "--allow-remote"):
        return Finding(
            status="FAIL",
            reason="cosd remote bind requires --allow-remote",
            evidence=f"host={host}",
            command=command,
        )
    if not _has_token_auth(serve_args):
        return Finding(
            status="FAIL",
            reason="cosd remote bind requires bearer token auth",
            evidence="missing --token-file or COSD_API_TOKEN_FILE",
            command=command,
        )
    return None


def _payload_paths(payload: dict[str, Any]) -> list[str]:
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    paths: list[str] = []
    for key in ("file_path", "path", "filePath"):
        value = tool_input.get(key)
        if value:
            paths.append(str(value))
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and edit.get("file_path"):
                paths.append(str(edit["file_path"]))
    return paths


def _relative_path(project_dir: Path, raw: str) -> str:
    path = Path(raw)
    full = (path if path.is_absolute() else project_dir / path).resolve()
    try:
        return full.relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return raw


def inspect_payload(payload: dict[str, Any], *, project_dir: str | Path) -> list[Finding]:
    """Inspect a hook payload for cosd auth policy violations."""

    project = Path(project_dir)
    tool = str(payload.get("tool_name") or payload.get("tool") or "")
    findings: list[Finding] = []
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}

    if tool == "Bash":
        command = str(tool_input.get("command") or payload.get("command") or "")
        finding = inspect_command(command)
        if finding is not None:
            findings.append(finding)

    if tool in {"Edit", "Write", "MultiEdit"} and os.environ.get(APPROVAL_ENV) != "1":
        for raw in _payload_paths(payload):
            rel = _relative_path(project, raw)
            if any(fnmatch.fnmatch(rel, pattern) for pattern in PROTECTED_COSD_GLOBS):
                findings.append(
                    Finding(
                        status="FAIL",
                        reason="cosd auth/control-plane config edit requires explicit approval",
                        evidence=f"set {APPROVAL_ENV}=1 only after human review",
                        path=rel,
                    )
                )
    return findings


def audit_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / ".cognitive-os" / "metrics" / "cosd-auth-guard.jsonl"


def append_audit(project_dir: str | Path, findings: list[Finding]) -> None:
    if not findings:
        return
    path = audit_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for finding in findings:
            row = {"timestamp_epoch": time.time(), **finding.to_dict()}
            handle.write(json.dumps(row, sort_keys=True) + "\n")
