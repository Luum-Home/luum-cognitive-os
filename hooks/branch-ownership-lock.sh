#!/usr/bin/env bash
# SCOPE: both
# ADR-182: acquire/enforce per-branch single-writer locks for destructive git operations.

set -uo pipefail

[ -f "$(dirname "$0")/_lib/bypass-resolver.sh" ] && source "$(dirname "$0")/_lib/bypass-resolver.sh"
if [[ "${DISABLE_HOOK_BRANCH_OWNERSHIP_LOCK:-0}" == "1" || "${DISABLE_HOOK_BRANCH_OWNERSHIP_LOCK:-}" == "true" ]]; then
  exit 0
fi
if type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows branch_ownership; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}}"
INPUT="$(cat 2>/dev/null || true)"

python3 - "$PROJECT_DIR" "$SESSION_ID" "$COS_ROOT" "$INPUT" <<'PY'
from __future__ import annotations

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

tool = str(data.get("tool_name") or data.get("tool") or "")
tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
cmd = str(tool_input.get("command") or data.get("command") or "")
if tool and tool != "Bash":
    raise SystemExit(0)
if cmd and not re.search(r"(^|&&|;)\s*git\s+(commit|push|merge|rebase|cherry-pick|reset\s+--hard|stash\s+(apply|pop)|worktree\s+(add|remove)|branch\s+-D)\b", cmd):
    raise SystemExit(0)

sys.path.insert(0, str(cos_root))
from lib.branch_lock import acquire  # noqa: E402

try:
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(project), text=True, stderr=subprocess.DEVNULL, timeout=1).strip() or "detached"
except Exception:
    branch = "detached"

result = acquire(project, branch=branch, session_id=session_id, pid=os.getpid(), worktree=project)
if result["status"] == "acquired":
    raise SystemExit(0)
held = result.get("held_by") or {}
print("BRANCH OWNERSHIP LOCK: blocked destructive git operation", file=sys.stderr)
print(f"  branch: {branch}", file=sys.stderr)
print(f"  held_by_session: {held.get('session_id')}", file=sys.stderr)
print(f"  held_by_pid: {held.get('pid')}", file=sys.stderr)
print(f"  held_by_worktree: {held.get('worktree')}", file=sys.stderr)
print("  Override: COS_ALLOW_BRANCH_OWNERSHIP_OVERRIDE=1", file=sys.stderr)
raise SystemExit(2)
PY
rc=$?
if [[ "$rc" -eq 2 ]]; then
  exit 2
fi
exit "$rc"
