#!/usr/bin/env bash
# SCOPE: both
# PreToolUse Bash guard: block git commit/merge/land commands when leftover
# conflict markers are present in staged additions or tracked files.
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh" 2>/dev/null || true

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SCRIPT="$PROJECT_DIR/scripts/cos-conflict-marker-guard"
[ -x "$SCRIPT" ] || exit 0

INPUT=""
if [ ! -t 0 ]; then INPUT="$(cat 2>/dev/null || true)"; fi

TOOL_NAME=""
COMMAND="${CLAUDE_TOOL_INPUT:-}"
if [ -n "$INPUT" ] && command -v python3 >/dev/null 2>&1; then
  TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_name", ""))' 2>/dev/null || true)"
  [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ] && exit 0
  extracted="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.load(sys.stdin); ti=d.get("tool_input") or {}; print(ti.get("command") or ti.get("cmd") or "")' 2>/dev/null || true)"
  [ -n "$extracted" ] && COMMAND="$extracted"
fi

[ -n "$COMMAND" ] || exit 0

# Use semantic-ish shell token parsing to avoid matching prose in commit messages.
ACTION="$(python3 - "$COMMAND" <<'PY' 2>/dev/null || true
import shlex
import sys
from pathlib import Path
try:
    parts = shlex.split(sys.argv[1])
except ValueError:
    sys.exit(0)
for i, token in enumerate(parts):
    name = Path(token).name
    if token == "git" or name == "git":
        j = i + 1
        while j < len(parts):
            t = parts[j]
            if t in {"-C", "--git-dir", "--work-tree", "-c"}:
                j += 2; continue
            if t.startswith("--git-dir=") or t.startswith("--work-tree="):
                j += 1; continue
            sub = t
            if sub == "commit":
                print("staged")
            elif sub in {"merge", "rebase", "pull"}:
                print("tree")
            sys.exit(0)
if any(Path(token).name in {"merge-to-main.sh", "cos-merge-queue-worker.sh"} for token in parts):
    print("tree")
PY
)"

case "$ACTION" in
  staged) MODE="--staged" ;;
  tree) MODE="--tree" ;;
  *) exit 0 ;;
esac

cd "$PROJECT_DIR" 2>/dev/null || exit 0
OUTPUT="$($SCRIPT "$MODE" 2>&1)"
rc=$?
if [ "$rc" -eq 0 ]; then
  exit 0
fi

# Claude/Codex/OpenCode consume non-zero hook exits differently. Prefer JSON
# block when the harness expects it, but stderr is still useful for shell/CI.
REASON="conflict-marker-guard blocked command: $OUTPUT"
printf '%s\n' "$REASON" >&2
if [ -n "$INPUT" ]; then
  python3 - "$REASON" <<'PY' 2>/dev/null || true
import json
import sys
print(json.dumps({"decision": "block", "reason": sys.argv[1][:1200]}))
PY
fi
exit 2
