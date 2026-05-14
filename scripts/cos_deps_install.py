#!/usr/bin/env python3
# SCOPE: os-only
"""Dry-run-first cross-device/headless dependency installer for ADR-168/309."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.manifest_loader import ManifestError, Tool, load_manifest  # noqa: E402

PROFILE_ALIASES = {
    "core": "default",
    "standard": "default",
    "default": "default",
    "dev": "dev",
    "ci": "ci",
    "full": "full",
    "services": "services",
    "security": "security",
    "headless": "headless-instance",
    "headless-instance": "headless-instance",
    "rust-transpiler-lab": "rust-transpiler-lab",
}
AUTH_BOUND_TOOLS = {"gh", "codex", "claude", "gemini", "opencode"}
MANUAL_MANAGERS = {"manual", "unsupported"}
SAFE_SYSTEM_MANAGERS = {"brew", "apt", "dnf", "pacman", "apk", "winget", "choco", "scoop"}
USER_MANAGERS = {"standalone", "pip", "npm", "go", "cargo", "rustup", "script", "python"}


def detect_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        release = Path("/proc/sys/kernel/osrelease")
        text = release.read_text(encoding="utf-8", errors="ignore").lower() if release.exists() else ""
        if "microsoft" in text or os.environ.get("WSL_DISTRO_NAME"):
            return "windows_wsl"
        return "linux"
    return system or "unknown"


def detect_runtime_context() -> dict[str, Any]:
    return {
        "platform": detect_platform(),
        "in_container": Path("/.dockerenv").exists() or bool(os.environ.get("KUBERNETES_SERVICE_HOST")),
        "is_root": hasattr(os, "geteuid") and os.geteuid() == 0,
        "has_sudo": shutil.which("sudo") is not None,
        "package_managers": [name for name in ("brew", "apt-get", "dnf", "pacman", "apk", "winget", "choco", "scoop") if shutil.which(name)],
        "headless": not bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or os.environ.get("TERM_PROGRAM")),
    }


def _linux_distro_keys() -> list[str]:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return []
    values: dict[str, str] = {}
    for line in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k] = v.strip().strip('"').lower()
    ids = [values.get("ID", "")]
    ids.extend(values.get("ID_LIKE", "").split())
    mapped: list[str] = []
    for distro in ids:
        if distro in {"debian", "ubuntu"}:
            mapped.extend([distro, "debian"])
        elif distro in {"fedora", "rhel", "centos"}:
            mapped.extend([distro, "fedora"])
        elif distro in {"arch"}:
            mapped.append("arch")
        elif distro in {"alpine"}:
            mapped.append("alpine")
    return list(dict.fromkeys([x for x in mapped if x]))


def platform_key_order(target_platform: str) -> list[str]:
    keys = [target_platform]
    if target_platform in {"linux", "windows_wsl"}:
        keys.extend(_linux_distro_keys())
        keys.extend(["debian", "linux"])
    if target_platform == "windows":
        keys.extend(["windows"])
    keys.append("any")
    return list(dict.fromkeys(keys))


def command_for(tool: Tool, target_platform: str) -> tuple[str | None, str, str, str | None, str | None]:
    install = tool.install or {}
    for key in platform_key_order(target_platform):
        value = install.get(key)
        if not value:
            continue
        if isinstance(value, str):
            return value, key, "legacy", None, None
        if isinstance(value, dict):
            manager = str(value.get("manager") or "manual")
            command = value.get("command")
            url = value.get("url")
            notes = value.get("notes")
            return str(command) if command else None, key, manager, str(url) if url else None, str(notes) if notes else None
    return None, "unsupported_platform", "unsupported", None, None


def _command_present(tool: Tool) -> bool:
    cmd = (tool.check or tool.name).split()[0]
    if cmd == "python3" and shutil.which("python3"):
        return True
    return shutil.which(cmd) is not None or shutil.which(tool.name) is not None


def _needs_sudo_without_sudo(command: str | None) -> bool:
    return bool(command and "sudo " in command and shutil.which("sudo") is None and not (hasattr(os, "geteuid") and os.geteuid() == 0))


def status_for(tool: Tool, target_platform: str) -> dict[str, Any]:
    command, source, manager, url, notes = command_for(tool, target_platform)
    present = _command_present(tool)
    auth_bound = bool(getattr(tool, "auth_bound", False)) or tool.name in AUTH_BOUND_TOOLS
    platform_builtin = manager == "platform"
    manual = manager in MANUAL_MANAGERS or (command is None and not platform_builtin)
    action = "already_present" if present else "platform_builtin" if platform_builtin else "manual" if auth_bound or manual else "installable"
    if _needs_sudo_without_sudo(command):
        action = "manual"
        notes = (notes or "") + " Requires sudo/root; current context has no sudo."
    return {
        "name": tool.name,
        "category": getattr(tool, "category", "cli"),
        "criticality": tool.criticality,
        "profiles": list(getattr(tool, "profiles", [])),
        "scope": getattr(tool, "scope", "system"),
        "syncable": getattr(tool, "syncable", "no"),
        "present": present,
        "auth_bound": auth_bound,
        "install_command": command,
        "install_source": source,
        "install_manager": manager,
        "manual_url": url or getattr(tool, "manual_url", None),
        "notes": notes,
        "never_copy": list(getattr(tool, "never_copy", [])),
        "post_install": getattr(tool, "post_install", None),
        "manual": manual,
        "platform_builtin": platform_builtin,
        "action": action,
    }


def selected_profile(profile_name: str):
    manifest = load_manifest()
    return manifest, manifest.profile(PROFILE_ALIASES[profile_name])


def selected_tools(profile_name: str, *, required_only: bool = False) -> list[Tool]:
    manifest, profile = selected_profile(profile_name)
    names = list(profile.tools_required)
    if not required_only:
        names.extend(profile.tools_recommended)
    tools: list[Tool] = []
    for name in dict.fromkeys(names):
        tool = manifest.tool(name)
        if tool is not None:
            tools.append(tool)
    return tools


def python_plan(profile_name: str, *, include_python: bool) -> dict[str, Any]:
    manifest, profile = selected_profile(profile_name)
    groups = list(profile.python_groups)
    packages: list[str] = []
    for group in groups:
        packages.extend(manifest.python_groups.get(group, []))
    packages = list(dict.fromkeys(packages))
    installer = "uv pip install" if shutil.which("uv") else "python3 -m pip install --user"
    return {
        "included": include_python,
        "groups": groups,
        "packages": packages,
        "install_command": f"{installer} " + " ".join(packages) if packages else None,
        "manager": "uv" if installer.startswith("uv") else "pip",
    }


def build_report(profile_name: str, target_platform: str, *, apply: bool, include_python: bool, required_only: bool) -> dict[str, Any]:
    rows = [status_for(tool, target_platform) for tool in selected_tools(profile_name, required_only=required_only)]
    report: dict[str, Any] = {
        "schema_version": "cos-deps-install.v2",
        "profile": profile_name,
        "manifest_profile": PROFILE_ALIASES[profile_name],
        "platform": target_platform,
        "runtime_context": detect_runtime_context(),
        "mode": "apply" if apply else "dry-run",
        "required_only": required_only,
        "already_present": [],
        "installable": [],
        "manual": [],
        "auth_bound": [],
        "platform_builtin": [],
        "unsupported_platform": [],
        "installed": [],
        "failed": [],
        "python": python_plan(profile_name, include_python=include_python),
        "credential_policy": "never-copy-or-read-credential-stores",
        "git_hook_policy": "advisory-only-no-auto-install",
    }
    for row in rows:
        if row["auth_bound"]:
            report["auth_bound"].append(row)
        if row["present"]:
            report["already_present"].append(row)
        elif row["platform_builtin"]:
            report["platform_builtin"].append(row)
        elif row["auth_bound"]:
            continue
        elif row["install_command"] is None and row["install_manager"] == "unsupported":
            report["unsupported_platform"].append(row)
        elif row["manual"]:
            report["manual"].append(row)
        else:
            report["installable"].append(row)

    if apply:
        for row in list(report["installable"]):
            if row.get("auth_bound") or row.get("manual") or not row.get("install_command"):
                continue
            proc = subprocess.run(row["install_command"], shell=True, text=True, capture_output=True, check=False)
            result = {**row, "returncode": proc.returncode}
            if proc.returncode == 0:
                report["installed"].append(result)
            else:
                result["stderr"] = proc.stderr[-1000:]
                report["failed"].append(result)
        py = report["python"]
        if include_python and py.get("packages"):
            proc = subprocess.run(str(py["install_command"]), shell=True, text=True, capture_output=True, check=False)
            py["returncode"] = proc.returncode
            if proc.returncode != 0:
                report["failed"].append({"name": "python-groups", "returncode": proc.returncode, "stderr": proc.stderr[-1000:]})
            else:
                report["installed"].append({"name": "python-groups", "returncode": 0, "groups": py["groups"]})
    return report


def render_text(report: dict[str, Any]) -> str:
    lines = [f"COS dependency installer ({report['mode']})", f"profile: {report['profile']} platform: {report['platform']}", ""]
    for bucket in ("already_present", "installable", "manual", "auth_bound", "platform_builtin", "unsupported_platform", "installed", "failed"):
        rows = report[bucket]
        lines.append(f"{bucket}: {len(rows)}")
        for row in rows:
            command = row.get("install_command") or row.get("manual_url") or row.get("notes") or "manual/unsupported"
            lines.append(f"  - {row['name']}: {command}")
    py = report.get("python", {})
    if py.get("groups"):
        lines.extend(["", f"python_groups: {', '.join(py['groups'])}", f"  packages: {len(py.get('packages', []))}", f"  command: {py.get('install_command')}"])
    lines.append("")
    lines.append("credential policy: never read/copy .env, keys, Keychain, ~/.codex, ~/.claude, gh auth, or provider token stores")
    lines.append("git hook policy: advisory only; install/apply is reserved for explicit install/update commands")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_ALIASES), default="core")
    parser.add_argument("--platform", default="auto", choices=("auto", "macos", "linux", "windows_wsl", "windows"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-python", action="store_true", help="Do not install/report Python groups for the selected profile.")
    parser.add_argument("--required-only", action="store_true", help="Install/report required tools only, excluding recommended tools.")
    args = parser.parse_args(argv)

    target_platform = detect_platform() if args.platform == "auto" else args.platform
    try:
        report = build_report(args.profile, target_platform, apply=args.apply, include_python=not args.skip_python, required_only=args.required_only)
    except ManifestError as exc:
        print(f"cos-deps-install: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report), end="")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
