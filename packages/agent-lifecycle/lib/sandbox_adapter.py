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
    adapter_status: str = "active"
    adapter_hint: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "backend": self.backend,
            "command": self.command,
            "network": self.network,
            "writable_roots": self.writable_roots,
            "fallback_used": self.fallback_used,
            "adapter_status": self.adapter_status,
            "adapter_hint": self.adapter_hint,
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



def adapter_plan(backend: str) -> dict[str, object]:
    """Return ADR-232 adapter status without executing external runtimes."""
    selected = backend.strip().lower()
    if selected in {"bubblewrap", "seatbelt"}:
        return {"backend": selected, "status": "active", "dependency_policy": "host-native optional", "requires": ["bwrap" if selected == "bubblewrap" else "sandbox-exec"]}
    if selected == "microvm":
        return {
            "backend": "microvm",
            "status": "adapter_contract",
            "dependency_policy": "opt-in only; no Firecracker/Kata/E2B dependency in default install",
            "requires": ["microvm-provider"],
            "command_contract": ["<microvm-runner>", "--workspace", "<workspace>", "--", "<command>"],
        }
    if selected == "contree":
        return {
            "backend": "contree",
            "status": "adapter_contract",
            "dependency_policy": "opt-in only; no ConTree runtime in default install",
            "requires": ["contree"],
            "command_contract": ["contree", "fork", "--workspace", "<workspace>", "--", "<command>"],
        }
    raise ValueError("backend must be one of: bubblewrap, seatbelt, microvm, contree")


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
            "--die-with-parent",
            "--unshare-pid",
            "--unshare-uts",
            "--unshare-ipc",
            "--unshare-cgroup-try",
            "--new-session",
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

    if selected in {"microvm", "contree"}:
        plan = adapter_plan(selected)
        runner = os.environ.get("COS_SANDBOX_MICROVM_RUNNER" if selected == "microvm" else "COS_SANDBOX_CONTREE_RUNNER")
        if runner:
            return SandboxPlan(SCHEMA_VERSION, selected, [runner, "--workspace", workspace_path, "--", *command], network, writable, adapter_status="active", adapter_hint=str(plan["dependency_policy"]))
        if allow_fallback:
            return SandboxPlan(SCHEMA_VERSION, "none", list(command), network, writable, fallback_used=True, adapter_status="fallback", adapter_hint=f"{selected} runner unavailable")
        raise SandboxUnavailable(f"{selected} backend requested but no runner configured")

    if allow_fallback:
        return SandboxPlan(SCHEMA_VERSION, "none", list(command), network, writable, fallback_used=True)
    raise SandboxUnavailable("no supported sandbox backend found; install bwrap or use macOS sandbox-exec")


def run_sandboxed(
    command: list[str],
    *,
    workspace: str | Path,
    backend: str | None = None,
    writable_roots: list[str] | None = None,
    network: bool = False,
    allow_fallback: bool = False,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    plan = build_sandbox_command(command, workspace=workspace, backend=backend, writable_roots=writable_roots, network=network, allow_fallback=allow_fallback)
    return subprocess.run(plan.command, cwd=str(Path(workspace).resolve()), text=True, capture_output=True, timeout=timeout)
