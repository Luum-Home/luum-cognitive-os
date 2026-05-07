# SCOPE: both
"""ADR-232 lightweight sandbox adapter selection and command wrapping."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = "sandbox-adapter/v1"


class SandboxUnavailable(RuntimeError):
    """Raised when a requested sandbox backend is unavailable."""


@dataclass(frozen=True)
class SandboxPlan:
    schema_version: str
    backend: str
    command: list[str]
    network: bool
    writable_roots: list[str]
    fallback_used: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "backend": self.backend,
            "command": self.command,
            "network": self.network,
            "writable_roots": self.writable_roots,
            "fallback_used": self.fallback_used,
        }


def available_backend() -> str | None:
    if os.environ.get("COS_SANDBOX_DISABLE_NATIVE") == "1":
        return None
    system = platform.system().lower()
    if system == "linux" and shutil.which("bwrap"):
        return "bubblewrap"
    if system == "darwin" and shutil.which("sandbox-exec"):
        return "seatbelt"
    return None


def build_sandbox_command(
    command: list[str],
    *,
    workspace: str | Path,
    writable_roots: list[str] | None = None,
    network: bool = False,
    backend: str | None = None,
    allow_fallback: bool = False,
) -> SandboxPlan:
    """Build a sandboxed command line without executing it."""
    if not command:
        raise ValueError("command is required")
    workspace_path = str(Path(workspace).resolve())
    selected = backend or available_backend()
    writable = [str(Path(root).resolve()) for root in (writable_roots or [workspace_path])]

    if selected == "bubblewrap":
        if not shutil.which("bwrap"):
            raise SandboxUnavailable("bubblewrap backend requested but bwrap is not installed")
        wrapped = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--chdir", workspace_path,
        ]
        if not network:
            wrapped.append("--unshare-net")
        for root in writable:
            wrapped.extend(["--bind", root, root])
        wrapped.extend(["--", *command])
        return SandboxPlan(SCHEMA_VERSION, "bubblewrap", wrapped, network, writable)

    if selected == "seatbelt":
        if not shutil.which("sandbox-exec"):
            raise SandboxUnavailable("seatbelt backend requested but sandbox-exec is not installed")
        writes = "\n".join(f'(allow file-write* (subpath "{root}"))' for root in writable)
        net = "(allow network*)" if network else ""
        profile = f'(version 1)\n(deny default)\n(allow process*)\n(allow file-read*)\n{writes}\n{net}\n'
        return SandboxPlan(SCHEMA_VERSION, "seatbelt", ["sandbox-exec", "-p", profile, *command], network, writable)

    if allow_fallback:
        return SandboxPlan(SCHEMA_VERSION, "none", list(command), network, writable, fallback_used=True)
    raise SandboxUnavailable("no supported sandbox backend found; install bwrap or use macOS sandbox-exec")


def run_sandboxed(command: list[str], *, workspace: str | Path, allow_fallback: bool = False, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    plan = build_sandbox_command(command, workspace=workspace, allow_fallback=allow_fallback)
    return subprocess.run(plan.command, cwd=str(Path(workspace).resolve()), text=True, capture_output=True, timeout=timeout)
