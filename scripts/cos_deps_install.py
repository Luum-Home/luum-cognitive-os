#!/usr/bin/env python3
# SCOPE: os-only
"""Dry-run-first cross-device dependency installer for ADR-168."""
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

PROFILE_ALIASES = {"core": "default", "standard": "default", "default": "default", "full": "full"}
AUTH_BOUND_TOOLS = {"gh", "codex", "claude", "gemini", "opencode"}
MANUAL_INSTALL_MARKERS = ("see ", "manual", "vendor", "app store")


def detect_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "linux":
        release = Path("/proc/sys/kernel/osrelease")
        text = release.read_text(encoding="utf-8", errors="ignore").lower() if release.exists() else ""
        if "microsoft" in text or os.environ.get("WSL_DISTRO_NAME"):
            return "windows_wsl"
        return "linux"
    return system or "unknown"


def command_for(tool: Tool, target_platform: str) -> tuple[str | None, str, str, str | None]:
    """Return (command, source, manager, url) for a tool/platform.

    Supports both legacy manifest values (`macos: brew install jq`) and the
    ADR-168 structured shape (`macos: {manager, command|url}`).
    """
    install = tool.install or {}
    key_order = [target_platform]
    if target_platform in {"linux", "windows_wsl"}:
        key_order.extend(["debian", "linux"])
    key_order.extend(["any", "macos"] if target_platform == "macos" else ["any"])
    for key in key_order:
        value = install.get(key)
        if not value:
            continue
        if isinstance(value, str):
            return value, key, "legacy", None
        if isinstance(value, dict):
            manager = str(value.get("manager") or "manual")
            command = value.get("command")
            url = value.get("url")
            return str(command) if command else None, key, manager, str(url) if url else None
    return None, "unsupported_platform", "unsupported", None


def status_for(tool: Tool, target_platform: str) -> dict[str, Any]:
    command, source, manager, url = command_for(tool, target_platform)
    present = shutil.which(tool.name) is not None
    auth_bound = bool(getattr(tool, "auth_bound", False)) or tool.name in AUTH_BOUND_TOOLS
    command_text = command or ""
    manual = command is None or manager == "manual" or any(
        marker in command_text.lower() for marker in MANUAL_INSTALL_MARKERS
    )
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
        "never_copy": list(getattr(tool, "never_copy", [])),
        "post_install": getattr(tool, "post_install", None),
        "manual": manual,
        "action": "already_present" if present else "manual" if auth_bound or manual else "installable",
    }


def selected_tools(profile_name: str) -> list[Tool]:
    manifest = load_manifest()
    profile = manifest.profile(PROFILE_ALIASES[profile_name])
    names = profile.tools_required + profile.tools_recommended
    tools: list[Tool] = []
    for name in names:
        tool = manifest.tool(name)
        if tool is not None:
            tools.append(tool)
    return tools


def build_report(profile_name: str, target_platform: str, *, apply: bool) -> dict[str, Any]:
    rows = [status_for(tool, target_platform) for tool in selected_tools(profile_name)]
    report: dict[str, Any] = {
        "schema_version": "cos-deps-install.v1",
        "profile": profile_name,
        "manifest_profile": PROFILE_ALIASES[profile_name],
        "platform": target_platform,
        "mode": "apply" if apply else "dry-run",
        "already_present": [],
        "installable": [],
        "manual": [],
        "auth_bound": [],
        "unsupported_platform": [],
        "installed": [],
        "failed": [],
        "credential_policy": "never-copy-or-read-credential-stores",
    }
    for row in rows:
        if row["auth_bound"]:
            report["auth_bound"].append(row)
        if row["present"]:
            report["already_present"].append(row)
        elif row["auth_bound"]:
            continue
        elif row["install_command"] is None:
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
    return report


def render_text(report: dict[str, Any]) -> str:
    lines = [f"COS dependency installer ({report['mode']})", f"profile: {report['profile']} platform: {report['platform']}", ""]
    for bucket in ("already_present", "installable", "manual", "auth_bound", "unsupported_platform", "installed", "failed"):
        rows = report[bucket]
        lines.append(f"{bucket}: {len(rows)}")
        for row in rows:
            command = row.get("install_command") or "manual/unsupported"
            lines.append(f"  - {row['name']}: {command}")
    lines.append("")
    lines.append("credential policy: never read/copy .env, keys, Keychain, ~/.codex, ~/.claude, gh auth, or provider token stores")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_ALIASES), default="core")
    parser.add_argument("--platform", default="auto", choices=("auto", "macos", "linux", "windows_wsl"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    target_platform = detect_platform() if args.platform == "auto" else args.platform
    try:
        report = build_report(args.profile, target_platform, apply=args.apply)
    except ManifestError as exc:
        print(f"cos-deps-install: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report), end="")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
