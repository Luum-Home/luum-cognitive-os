#!/usr/bin/env python3
# SCOPE: project
"""check_mcp_servers.py — Diagnostic tool for MCP server health.

Reads MCP server definitions from:
  1. ~/.claude/settings.json and ~/.claude/mcp/*.json
  2. ~/.claude/plugins/cache/*/.mcp.json  (plugin-bundled MCP configs)
  3. ~/.codex/config.toml
  4. Project-local MCP files for Codex, Claude, Cursor, Devin, Qoder, etc.

For each declared MCP server, checks:
  - Is the binary resolvable in PATH? (uses `which -a` to detect multi-path)
  - Is the configured command a brittle Homebrew Cellar path?
  - Is a process currently running? (pgrep by command)
  - What version does the binary report?

Exit code: 0 if all servers healthy, 1 if any issue detected.

Usage:
  python3 scripts/check_mcp_servers.py
  python3 scripts/check_mcp_servers.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover - Python <3.11 fallback not expected in CI
    tomllib = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------

CLAUDE_DIR = Path.home() / ".claude"
MCP_DIR = CLAUDE_DIR / "mcp"
PLUGINS_CACHE = CLAUDE_DIR / "plugins" / "cache"
CODEX_CONFIG = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
PROJECT_ROOT = Path(
    os.environ.get("COGNITIVE_OS_PROJECT_DIR")
    or os.environ.get("CODEX_PROJECT_DIR")
    or os.environ.get("CLAUDE_PROJECT_DIR")
    or os.getcwd()
)
HOMEBREW_ENGRAM_CELLAR_RE = re.compile(
    r"(^|/)Cellar/engram/[^/]+/bin/engram$"
)


def _insert_server(
    servers: dict[str, dict[str, Any]],
    name: str,
    cfg: dict[str, Any],
    source: Path,
) -> None:
    """Insert a server config without hiding duplicate host registrations."""
    entry = dict(cfg, _source=str(source))
    key = name
    if key in servers:
        suffix = 2
        while f"{name}#{suffix}" in servers:
            suffix += 1
        key = f"{name}#{suffix}"
        entry["_logical_name"] = name
    servers[key] = entry


def _load_json_mcp_servers(path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    if "command" in data:
        return {path.stem: data}

    servers = data.get("mcpServers")
    if isinstance(servers, dict):
        return {
            str(name): cfg
            for name, cfg in servers.items()
            if isinstance(cfg, dict)
        }

    return {}


def _load_toml_mcp_servers(path: Path) -> dict[str, dict[str, Any]]:
    if tomllib is None:
        return {}
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}

    servers = data.get("mcp_servers")
    if isinstance(servers, dict):
        return {
            str(name): cfg
            for name, cfg in servers.items()
            if isinstance(cfg, dict)
        }
    return {}


def find_mcp_configs() -> dict[str, dict[str, Any]]:
    """Return a mapping of {server_name: server_config} from all known sources.

    Config sources (duplicate names are retained with #2/#3 suffixes so stale
    host-specific registrations cannot be hidden by another source):
      1. ~/.claude/settings.json and ~/.claude/mcp/*.json
      2. ~/.claude/plugins/cache/**/.mcp.json
      3. ~/.codex/config.toml
      4. Project-local host MCP config files
    """
    servers: dict[str, dict[str, Any]] = {}

    # Source 0: Claude user settings.
    claude_settings = CLAUDE_DIR / "settings.json"
    if claude_settings.is_file():
        for name, cfg in _load_json_mcp_servers(claude_settings).items():
            _insert_server(servers, name, cfg, claude_settings)

    # Source 1: standalone MCP configs
    if MCP_DIR.is_dir():
        for config_path in sorted(MCP_DIR.glob("*.json")):
            for name, cfg in _load_json_mcp_servers(config_path).items():
                _insert_server(servers, name, cfg, config_path)

    # Source 2: plugin-bundled .mcp.json files
    if PLUGINS_CACHE.is_dir():
        for mcp_json in sorted(PLUGINS_CACHE.glob("**/.mcp.json")):
            for name, cfg in _load_json_mcp_servers(mcp_json).items():
                _insert_server(servers, name, cfg, mcp_json)

    # Source 3: Codex user config.
    if CODEX_CONFIG.is_file():
        for name, cfg in _load_toml_mcp_servers(CODEX_CONFIG).items():
            _insert_server(servers, name, cfg, CODEX_CONFIG)

    # Source 4: Project-local MCP config files installed by IDE projections.
    project_sources = [
        (PROJECT_ROOT / ".claude" / "settings.json", "json"),
        (PROJECT_ROOT / ".codex" / "config.toml", "toml"),
        (PROJECT_ROOT / ".cursor" / "mcp.json", "json"),
        (PROJECT_ROOT / ".devin" / "mcp_config.json", "json"),
        (PROJECT_ROOT / ".vscode" / "mcp.json", "json"),
        (PROJECT_ROOT / ".mcp.json", "json"),
        (PROJECT_ROOT / ".factory" / "mcp.json", "json"),
        (PROJECT_ROOT / ".augment" / "mcp.json", "json"),
        (PROJECT_ROOT / ".kimi" / "mcp.json", "json"),
    ]
    for path, kind in project_sources:
        if not path.is_file():
            continue
        loader = _load_toml_mcp_servers if kind == "toml" else _load_json_mcp_servers
        for name, cfg in loader(path).items():
            _insert_server(servers, name, cfg, path)

    return servers


# ---------------------------------------------------------------------------
# Binary checks
# ---------------------------------------------------------------------------

def which_all(command: str) -> list[str]:
    """Return all PATH locations for *command* (equivalent to `which -a`).

    Falls back to a shell-expanded lookup for commands that may be defined as
    shell functions or wrappers (e.g. `npx` via fnm, `nvm`-managed node).
    """
    try:
        result = subprocess.run(
            ["which", "-a", command],
            capture_output=True,
            text=True,
            timeout=5,
        )
        paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if paths:
            return paths
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Shell-expanded fallback: some commands (npx via fnm, node via nvm) live in
    # directories not on the non-interactive subprocess PATH.
    try:
        result = subprocess.run(
            ["bash", "-lc", f"which -a {command} 2>/dev/null"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if paths:
            return paths
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return []


def get_binary_version(command: str) -> str:
    """Try common version flags and return the first version string found."""
    for flag in ["version", "--version", "-v", "-version"]:
        try:
            result = subprocess.run(
                [command, flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = (result.stdout + result.stderr).strip()
            # Extract semver-ish string
            import re
            match = re.search(r"\d+\.\d+\.\d+", output)
            if match:
                return match.group(0)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    return "unknown"


def is_homebrew_engram_cellar_path(command: str) -> bool:
    """Return True when command pins Engram to a Homebrew Cellar version."""
    return bool(HOMEBREW_ENGRAM_CELLAR_RE.search(command))


def resolve_command(command: str) -> tuple[str | None, list[str]]:
    """Resolve a command or absolute path to the executable candidates."""
    if "/" in command:
        path = Path(command).expanduser()
        if path.exists():
            return str(path), [str(path)]
        return None, []

    all_paths = which_all(command)
    resolved = all_paths[0] if all_paths else shutil.which(command)
    return resolved, all_paths


def is_process_running(command: str, args: list[str]) -> bool:
    """Return True if a process matching the command+args is currently running."""
    # Build a search pattern from the command and first meaningful arg
    pattern_parts = [Path(command).name if "/" in command else command]
    if args:
        pattern_parts.append(args[0])
    pattern = " ".join(pattern_parts)
    try:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ---------------------------------------------------------------------------
# Per-server health check
# ---------------------------------------------------------------------------

def check_server(name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Return a health-check result dict for one MCP server."""
    command = config.get("command", "")
    args = config.get("args", [])
    source = config.get("_source", "unknown")

    result: dict[str, Any] = {
        "name": name,
        "command": command,
        "args": args,
        "source": source,
        "binary_found": False,
        "binary_path": None,
        "binary_paths_all": [],
        "multi_path_conflict": False,
        "version": "unknown",
        "process_running": False,
        "issues": [],
        "status": "unknown",
    }

    if not command:
        result["issues"].append("No command defined in config")
        result["status"] = "ERROR"
        return result

    # Resolve all PATH entries (which_all includes shell-expanded fallback).
    resolved, all_paths = resolve_command(command)

    result["binary_paths_all"] = all_paths
    result["binary_path"] = resolved

    if is_homebrew_engram_cellar_path(command):
        result["issues"].append(
            "Engram MCP command is pinned to a Homebrew Cellar version; "
            "use 'engram' or '/opt/homebrew/bin/engram' so upgrades do not "
            "hide mem_* tools from new sessions"
        )

    if not resolved:
        # Some commands (e.g. `npx` via fnm/nvm, `uvx`) are shell functions or managed
        # wrappers not visible in non-interactive subprocess PATH. Treat them as WARN
        # rather than hard ERROR so that legitimate shell-wrapper MCP servers don't
        # block overall health reporting.
        _shell_wrappers = {"npx", "node", "uvx", "uv", "deno", "bun"}
        if command in _shell_wrappers:
            result["issues"].append(
                f"'{command}' not found in subprocess PATH "
                f"(may be a shell wrapper — verify with: which -a {command})"
            )
            result["status"] = "WARN"
            return result
        result["issues"].append(f"Binary '{command}' not found in PATH")
        result["status"] = "ERROR"
        return result

    result["binary_found"] = True

    if len(all_paths) > 1:
        result["multi_path_conflict"] = True
        result["issues"].append(
            f"Multi-path conflict: '{command}' found in {len(all_paths)} locations "
            f"— use `which -a {command}` to inspect; symlink all to canonical"
        )

    # Version
    result["version"] = get_binary_version(resolved)

    # Process check
    result["process_running"] = is_process_running(command, args)
    if not result["process_running"]:
        result["issues"].append(
            f"No running process found for '{command}' — "
            "restart the host IDE/agent session to spawn the MCP server"
        )

    # Determine overall status
    fatal = [i for i in result["issues"] if "not found" in i]
    if fatal:
        result["status"] = "ERROR"
    elif result["issues"]:
        result["status"] = "WARN"
    else:
        result["status"] = "OK"

    return result


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_table(results: list[dict[str, Any]]) -> None:
    """Print a human-readable table of MCP server health."""
    print("\nMCP Server Health")
    print("-" * 70)
    for r in results:
        status_marker = {"OK": "[OK]   ", "WARN": "[WARN] ", "ERROR": "[ERROR]"}.get(
            r["status"], "[?]    "
        )
        path_display = r["binary_path"] or "(not found)"
        print(
            f"  {status_marker} {r['name']:<18} "
            f"binary={path_display}  version={r['version']}  "
            f"process={'running' if r['process_running'] else 'NOT running'}"
        )
        if r["multi_path_conflict"]:
            print(f"           paths: {r['binary_paths_all']}")
        for issue in r["issues"]:
            print(f"           issue: {issue}")
    print()


def print_json(results: list[dict[str, Any]]) -> None:
    """Print JSON output."""
    print(json.dumps({"mcp_servers": results}, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check health of Claude Code MCP servers"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    args = parser.parse_args()

    servers = find_mcp_configs()

    if not servers:
        msg = {
            "error": "No MCP server configs found",
            "checked": [
                str(CLAUDE_DIR / "settings.json"),
                str(MCP_DIR),
                str(PLUGINS_CACHE),
                str(CODEX_CONFIG),
                str(PROJECT_ROOT),
            ],
        }
        if args.json:
            print(json.dumps(msg))
        else:
            print(
                "No MCP server configs found. Checked:\n"
                f"  {CLAUDE_DIR / 'settings.json'}\n"
                f"  {MCP_DIR}\n"
                f"  {PLUGINS_CACHE}\n"
                f"  {CODEX_CONFIG}\n"
                f"  {PROJECT_ROOT} project-local MCP configs"
            )
        # Not an error — may just be a fresh install
        return 0

    results = [check_server(name, cfg) for name, cfg in servers.items()]

    if args.json:
        print_json(results)
    else:
        print_table(results)

    any_error = any(r["status"] == "ERROR" for r in results)
    return 1 if any_error else 0


if __name__ == "__main__":
    sys.exit(main())
