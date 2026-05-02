#!/usr/bin/env python3
"""Codex governed-tool layer for COS hook surfaces Codex cannot emit natively.

Codex currently projects native Bash lifecycle hooks. This runner lets Codex
operators and agents execute the same canonical hook chains around synthetic
Agent and Edit/Write events instead of pretending those matchers are native.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

EVENT_BY_ACTION = {
    "pre-agent": ("PreToolUse", "Agent", "Agent"),
    "post-agent": ("PostToolUse", "Agent", "Agent"),
    "pre-edit": ("PreToolUse", "Edit", "Edit"),
    "post-edit": ("PostToolUse", "Edit", "Edit"),
    "pre-write": ("PreToolUse", "Write", "Write"),
    "post-write": ("PostToolUse", "Write", "Write"),
}


def project_root() -> Path:
    for name in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(name)
        if value:
            return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def load_hooks(root: Path) -> dict[str, dict[str, Any]]:
    config_path = root / "cognitive-os.yaml"
    if not config_path.is_file():
        raise SystemExit(f"cognitive-os.yaml not found at {config_path}")
    config = yaml.safe_load(config_path.read_text()) or {}
    hooks = ((config.get("harness") or {}).get("hooks") or {})
    if not isinstance(hooks, dict):
        raise SystemExit("cognitive-os.yaml harness.hooks must be a mapping")
    return hooks


def matcher_matches(config_matcher: str, requested: str, include_global: bool) -> bool:
    normalized = config_matcher.strip()
    if include_global and normalized == "":
        return True
    if normalized == requested:
        return True
    return requested in {part.strip() for part in normalized.split("|") if part.strip()}


def select_chain(
    hooks: dict[str, dict[str, Any]], event: str, matcher: str, include_global: bool
) -> list[tuple[str, dict[str, Any]]]:
    selected: list[tuple[str, dict[str, Any]]] = []
    for hook_id, entry in hooks.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("event") != event:
            continue
        entry_matcher = str(entry.get("matcher") or "")
        if matcher_matches(entry_matcher, matcher, include_global):
            selected.append((hook_id, entry))
    return selected


def read_text_arg(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    if value == "-":
        return sys.stdin.read()
    if value.startswith("@"):
        return Path(value[1:]).read_text()
    return value


def build_payload(args: argparse.Namespace, event: str, matcher: str, tool_name: str) -> dict[str, Any]:
    if args.payload_json:
        return json.loads(read_text_arg(args.payload_json))

    payload: dict[str, Any] = {
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": {},
        "cos_runner": "cos-codex-guard",
        "harness": "codex",
    }

    if matcher == "Agent":
        prompt = read_text_arg(args.prompt, args.description or "")
        payload["tool_input"] = {
            "prompt": prompt,
            "description": args.description or prompt[:160],
        }
        if event == "PostToolUse":
            payload["tool_response"] = read_text_arg(args.output, "")
    else:
        content = read_text_arg(args.content, "")
        tool_input = {"file_path": args.file_path or "", "content": content}
        if tool_name == "Edit":
            tool_input = {
                "file_path": args.file_path or "",
                "old_string": args.old_string or "",
                "new_string": content,
            }
        payload["tool_input"] = tool_input
        if event == "PostToolUse":
            payload["tool_response"] = {"file_path": args.file_path or ""}

    return payload


def runner_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("COGNITIVE_OS_HARNESS", "codex")
    env["COGNITIVE_OS_PROJECT_DIR"] = str(root)
    env.setdefault("CODEX_PROJECT_DIR", str(root))
    env.setdefault("CLAUDE_PROJECT_DIR", str(root))
    return env


def run_chain(root: Path, chain: list[tuple[str, dict[str, Any]]], payload: dict[str, Any]) -> int:
    env = runner_env(root)
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    worst = 0
    for hook_id, entry in chain:
        script_value = str(entry.get("script") or "")
        if not script_value:
            continue
        script = root / script_value
        if not script.is_file():
            print(f"cos-codex-guard: missing script for {hook_id}: {script_value}", file=sys.stderr)
            worst = max(worst, 1)
            continue
        proc = subprocess.run(
            ["bash", str(script)],
            input=payload_bytes,
            cwd=str(root),
            env=env,
            stdout=sys.stdout.buffer,
            stderr=sys.stderr.buffer,
            check=False,
        )
        if proc.returncode == 2:
            print(f"cos-codex-guard: blocked by {hook_id}", file=sys.stderr)
            return 2
        if proc.returncode != 0:
            worst = max(worst, proc.returncode)
    return worst


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run COS hook chains Codex cannot emit natively.")
    parser.add_argument("action", choices=sorted(EVENT_BY_ACTION))
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--prompt", default=None, help="Agent prompt text, '-' for stdin, or @file")
    parser.add_argument("--description", default=None)
    parser.add_argument("--output", default=None, help="Agent result text, '-' for stdin, or @file")
    parser.add_argument("--file-path", default=None)
    parser.add_argument("--content", default=None, help="Write/Edit content, '-' for stdin, or @file")
    parser.add_argument("--old-string", default=None)
    parser.add_argument("--payload-json", default=None, help="Raw hook payload JSON, literal or @file")
    parser.add_argument("--list", action="store_true", help="Print selected hook scripts as JSON without running them")
    parser.add_argument("--no-global", action="store_true", help="Do not include matcherless all-tool hooks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).expanduser().resolve() if args.project_dir else project_root()
    event, matcher, tool_name = EVENT_BY_ACTION[args.action]
    hooks = load_hooks(root)
    chain = select_chain(hooks, event, matcher, include_global=not args.no_global)
    if args.list:
        print(json.dumps({"event": event, "matcher": matcher, "scripts": [entry.get("script") for _, entry in chain]}, indent=2))
        return 0
    payload = build_payload(args, event, matcher, tool_name)
    return run_chain(root, chain, payload)


if __name__ == "__main__":
    raise SystemExit(main())
