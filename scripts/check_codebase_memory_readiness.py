#!/usr/bin/env python3
# SCOPE: project
"""check_codebase_memory_readiness.py — Is the codebase-memory-mcp directive applicable HERE?

ADR-343. Read-only, deterministic, no session state, no network.

The problem this solves
-----------------------
A "always use codebase-memory-mcp tools FIRST" directive is only useful when two
conditions hold at once:

  1. the MCP server is actually reachable on this machine, AND
  2. *this* project has been indexed into its graph.

If (1) fails the agent burns a tool call on a server that is not there. If (2)
fails — the far more common case — the agent is ordered to consult an EMPTY
graph before grepping, which is strictly worse than grepping. This script turns
that unconditional directive into a measurable precondition.

How it decides
--------------
Detection is done through the vendor's own CLI (`codebase-memory-mcp cli
list_projects`), which is the authoritative source for both conditions in a
single call: if it runs, the server is present; its output says whether this
repo's root path is indexed. No harness config format is invented or parsed for
the decision — see `--explain` for the fallback discovery order.

Exit codes
----------
  0  READY      — server reachable AND this project indexed. Directive applies.
  1  NOT_READY  — server absent, or reachable but this project not indexed.
                  Directive must NOT fire; structural search falls back to grep.
  2  ERROR      — could not decide (unreadable config, malformed output).

Usage
-----
  python3 scripts/check_codebase_memory_readiness.py
  python3 scripts/check_codebase_memory_readiness.py --json
  python3 scripts/check_codebase_memory_readiness.py --explain
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

SERVER_NAME = "codebase-memory-mcp"
CLI_TIMEOUT_S = 30

READY = 0
NOT_READY = 1
ERROR = 2


def _project_root() -> Path:
    env = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve().parent.parent
    return here


def _redact(text: str) -> str:
    """Never emit the operator's home path or username.

    Redacts both $HOME and the account's real home directory, so an overridden
    HOME (tests, sandboxes) cannot leak the operator's path into output.
    """
    homes = {str(Path.home())}
    try:
        import pwd

        homes.add(pwd.getpwuid(os.getuid()).pw_dir)
    except Exception:  # pragma: no cover - non-POSIX
        pass
    for home in sorted(homes, key=len, reverse=True):
        if home and home != "/":
            text = text.replace(home, "~")
    return text


# ---------------------------------------------------------------------------
# Discovery of the server command
# ---------------------------------------------------------------------------
# Order matters. PATH first (the shape `npx codebase-memory-mcp install` leaves
# behind); then config files we can parse without guessing a schema — we only
# look for a *command string* under a key whose name contains the server name.
# We do NOT emit config for any harness, so no harness contract is asserted here.


def _candidate_config_files(root: Path) -> list[Path]:
    home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
    return [
        home / ".claude.json",
        home / ".claude" / "settings.json",
        home / ".mcp.json",
        root / ".mcp.json",
        root / ".claude" / "settings.json",
        codex_home / "config.toml",
        root / ".codex" / "config.toml",
    ]


def _commands_from_json(path: Path) -> list[list[str]]:
    """Find {"<...codebase-memory...>": {"command": str, "args": [...]}} at any depth.

    Only the command/args of a matching key are read. No other content of the
    file is retained, logged, or emitted.
    """
    found: list[list[str]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return found

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if (
                    isinstance(key, str)
                    and SERVER_NAME in key
                    and isinstance(val, dict)
                    and isinstance(val.get("command"), str)
                ):
                    args = val.get("args") or []
                    if isinstance(args, list) and all(isinstance(a, str) for a in args):
                        found.append([val["command"], *args])
                walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def _commands_from_toml(path: Path) -> list[list[str]]:
    try:
        import tomllib
    except ImportError:
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[list[str]] = []
    for table in data.values():
        if not isinstance(table, dict):
            continue
        for key, val in table.items():
            if SERVER_NAME in str(key) and isinstance(val, dict):
                cmd = val.get("command")
                args = val.get("args") or []
                if isinstance(cmd, str) and isinstance(args, list):
                    out.append([cmd, *[str(a) for a in args]])
    return out


def discover_commands(root: Path) -> tuple[list[list[str]], list[str]]:
    """Return (candidate argv lists, human-readable sources)."""
    cmds: list[list[str]] = []
    sources: list[str] = []

    on_path = shutil.which(SERVER_NAME)
    if on_path:
        cmds.append([on_path])
        sources.append("PATH")

    for cfg in _candidate_config_files(root):
        if not cfg.is_file():
            continue
        found = _commands_from_toml(cfg) if cfg.suffix == ".toml" else _commands_from_json(cfg)
        for argv in found:
            if argv not in cmds:
                cmds.append(argv)
                sources.append(_redact(str(cfg)))
    return cmds, sources


# ---------------------------------------------------------------------------
# The single authoritative probe
# ---------------------------------------------------------------------------


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """The CLI may print a JSON object with trailing noise. Take the first object."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except Exception:
                    return None
    return None


def probe(argv: list[str]) -> tuple[list[dict[str, Any]] | None, str]:
    """Run `<server> cli list_projects`. Return (projects, note)."""
    try:
        run = subprocess.run(
            [*argv, "cli", "list_projects"],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None, "command not found"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {CLI_TIMEOUT_S}s"
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"probe failed: {type(exc).__name__}"

    payload = _extract_json_object((run.stdout or "") + (run.stderr or ""))
    if payload is None:
        return None, f"no JSON in output (rc={run.returncode})"
    projects = payload.get("projects")
    if not isinstance(projects, list):
        return None, "output has no 'projects' list"
    return projects, f"ok (rc={run.returncode})"


def evaluate(root: Path) -> dict[str, Any]:
    cmds, sources = discover_commands(root)
    result: dict[str, Any] = {
        "server": SERVER_NAME,
        "project_root": _redact(str(root)),
        "discovery_sources": sources,
        "server_present": False,
        "project_indexed": False,
        "indexed_project_count": None,
        "note": "",
        "state": "NOT_READY",
    }
    if not cmds:
        result["note"] = "server not configured in any readable location and not on PATH"
        return result

    last_note = ""
    for argv in cmds:
        projects, note = probe(argv)
        last_note = note
        if projects is None:
            continue
        result["server_present"] = True
        result["indexed_project_count"] = len(projects)
        root_str = str(root)
        result["project_indexed"] = any(
            isinstance(p, dict)
            and isinstance(p.get("root_path"), str)
            and Path(p["root_path"]).resolve() == root
            for p in projects
        )
        result["note"] = (
            "this project is indexed"
            if result["project_indexed"]
            else "server reachable but this project is NOT in its graph"
        )
        result["state"] = "READY" if result["project_indexed"] else "NOT_READY"
        return result

    result["note"] = f"server configured but not reachable: {_redact(last_note)}"
    return result


EXPLAIN = """\
Decision rule (ADR-343)
  READY      server reachable AND this project's root_path is in list_projects
  NOT_READY  anything else — the directive must not fire

Discovery order for the server command
  1. `codebase-memory-mcp` on PATH
  2. a key containing "codebase-memory-mcp" with a `command` string, in:
       ~/.claude.json, ~/.claude/settings.json, ~/.mcp.json,
       <project>/.mcp.json, <project>/.claude/settings.json,
       $CODEX_HOME/config.toml, <project>/.codex/config.toml
     Only `command` and `args` of a matching key are read. Nothing else from
     those files is retained or printed, and the operator's home path is
     redacted to `~` in all output.

What this script deliberately does NOT do
  - It does not write MCP config for any harness. The vendor binary ships its
    own installer (`codebase-memory-mcp install`) which auto-detects the
    supported agents; reimplementing that would assert harness contracts this
    repo has not verified.
  - It does not index anything. Indexing is an operator action.
  - It does not reach the network.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--explain", action="store_true", help="print the decision rule and exit 0")
    args = ap.parse_args()

    if args.explain:
        print(EXPLAIN)
        return 0

    try:
        result = evaluate(_project_root())
    except Exception as exc:  # pragma: no cover - defensive
        print(f"ERROR: could not evaluate readiness: {type(exc).__name__}", file=sys.stderr)
        return ERROR

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['state']}: {SERVER_NAME}")
        print(f"  project           {result['project_root']}")
        print(f"  server present    {result['server_present']}")
        print(f"  project indexed   {result['project_indexed']}")
        if result["indexed_project_count"] is not None:
            print(f"  projects in graph {result['indexed_project_count']}")
        print(f"  note              {result['note']}")
        if result["state"] != "READY":
            print("  -> structural-search directive must NOT fire; use grep/Glob.")

    return READY if result["state"] == "READY" else NOT_READY


if __name__ == "__main__":
    sys.exit(main())
