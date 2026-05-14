#!/usr/bin/env bash
# SCOPE: both
# ADR-183: emit standardized cross-session events into .cognitive-os/sessions/events.jsonl.

set -uo pipefail

if [[ "${DISABLE_HOOK_CROSS_SESSION_EVENT_EMIT:-0}" == "1" || "${DISABLE_HOOK_CROSS_SESSION_EVENT_EMIT:-}" == "true" ]]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
INPUT="$(cat 2>/dev/null || true)"

python3 - "$PROJECT_DIR" "$SESSION_ID" "$COS_ROOT" "$INPUT" <<'PY' 2>/dev/null || true
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

project = Path(sys.argv[1]).resolve()
session_id = sys.argv[2] or "unknown"
cos_root = Path(sys.argv[3]).resolve()
raw = sys.argv[4] if len(sys.argv) > 4 else ""
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}

sys.path.insert(0, str(cos_root))
from lib.session_bus import append_event  # noqa: E402


def current_branch() -> str:
    try:
        return subprocess.check_output(["git", "branch", "--show-current"], cwd=str(project), text=True, stderr=subprocess.DEVNULL, timeout=1).strip()
    except Exception:
        return ""


def tool_name() -> str:
    return str(data.get("tool_name") or data.get("tool") or "")


def command() -> str:
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    return str(tool_input.get("command") or data.get("command") or "")


def file_path() -> str:
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    return str(tool_input.get("file_path") or tool_input.get("path") or data.get("file_path") or "")


def event_name() -> str:
    explicit = os.environ.get("COS_SESSION_EVENT_TYPE", "").strip()
    if explicit:
        return explicit.replace("_", "-")
    hook_event = str(data.get("hook_event_name") or data.get("event") or "")
    tname = tool_name()
    cmd = command()
    if hook_event == "SessionStart" or not data:
        return "session-start"
    if hook_event == "Stop":
        return "session-end"
    if hook_event == "PreToolUse" and tname in {"Write", "Edit", "MultiEdit"}:
        return "file-write-intent"
    if hook_event == "PreToolUse" and tname == "Agent":
        return "agent-spawn"
    if hook_event == "PreToolUse" and tname == "Bash" and re.search(r"(^|&&|;)\s*git\s+commit\b", cmd):
        return "commit-intent"
    if hook_event == "PostToolUse" and tname == "Bash" and re.search(r"(^|&&|;)\s*git\s+commit\b", cmd):
        return "commit-landed"
    return "session-heartbeat"


def topic_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
    skip = {"bash", "git", "commit", "write", "edit", "agent", "session", "tool", "with", "from", "this", "that"}
    out: list[str] = []
    for word in words:
        if word in skip or word in out:
            continue
        out.append(word)
        if len(out) >= 5:
            break
    return out

etype = event_name()
cmd = command()
path = file_path()
payload = {
    "branch": current_branch(),
    "worktree": str(project),
}
if path:
    payload["path"] = path
if cmd:
    payload["command_hash"] = hashlib.sha256(cmd.encode()).hexdigest()[:16]
    payload["command_preview"] = cmd[:120]
if etype == "agent-spawn":
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    prompt = str(tool_input.get("prompt") or tool_input.get("description") or "")
    payload["topic_keywords"] = topic_keywords(prompt)
if etype == "file-write-intent" and path:
    payload["topic_keywords"] = topic_keywords(path)

append_event(etype, payload, project_dir=project, session_id=session_id)
PY

exit 0
