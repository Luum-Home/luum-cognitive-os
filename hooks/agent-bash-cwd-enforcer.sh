#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook on Bash — warns when a git operation is issued from a cwd
# that differs from the configured main worktree.
#
# Problem: sub-agents inherit the orchestrator's cwd (a worktree). If they run
# `git commit` without `git -C <main>` or `cd <main> &&`, the commit lands on
# the worktree branch instead of main.
#
# Behaviour:
#   - Reads tool_input.command from stdin (Claude Code PreToolUse:Bash payload)
#   - Resolves main worktree via _lib/resolve-main-worktree.sh
#   - If command contains git commit|push|merge|rebase|reset AND
#     cwd != main worktree AND command does NOT already include git -C <target>:
#       → emits additionalContext warning (exit 0, advisory only)
#       → logs to .cognitive-os/metrics/cwd-enforcer.jsonl
#   - All other cases: silent exit 0
#
# Never blocks (always exits 0). Registers under PreToolUse:Bash.
# p95 latency target: <50ms.

set -euo pipefail

# ADR-028 §584: respect killswitch flag.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ── Resolve shared worktree lib ──────────────────────────────────────────────
LIB_DIR="$(dirname "${BASH_SOURCE[0]}")/_lib"
source "$LIB_DIR/resolve-main-worktree.sh"

# ── Locate project root ──────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# ── Metrics helper ───────────────────────────────────────────────────────────
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/cwd-enforcer.jsonl"

log_event() {
  local event="$1"
  local detail="${2:-}"
  mkdir -p "$METRICS_DIR" 2>/dev/null || true
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")"
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg ts "$ts" --arg ev "$event" --arg det "$detail" \
      '{"timestamp":$ts,"event":$ev,"detail":$det}' \
      >> "$METRICS_FILE" 2>/dev/null || true
  else
    # Fallback: strip double-quotes from detail to keep JSONL valid
    local safe_detail
    safe_detail="$(printf '%s' "$detail" | tr -d '"')"
    printf '{"timestamp":"%s","event":"%s","detail":"%s"}\n' \
      "$ts" "$event" "$safe_detail" >> "$METRICS_FILE" 2>/dev/null || true
  fi
}

# ── Read stdin ────────────────────────────────────────────────────────────────
INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)

# Only process Bash tool calls
if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
  exit 0
fi

# ── Extract bash command ──────────────────────────────────────────────────────
BASH_CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)

if [ -z "$BASH_CMD" ]; then
  exit 0
fi

# ── Check if command contains a dangerous git operation ──────────────────────
# Match: git commit, git push, git merge, git rebase, git reset
# (with any flags or arguments following)
if ! printf '%s' "$BASH_CMD" | grep -qE 'git\s+(commit|push|merge|rebase|reset)'; then
  exit 0
fi

# ── Resolve target worktree ───────────────────────────────────────────────────
TARGET_DIR=$(resolve_main_worktree "$PROJECT_DIR")

if [ -z "$TARGET_DIR" ]; then
  exit 0
fi

# ── Check if the command is already scoped to the target ─────────────────────
# Accept: `git -C <target>` OR `cd <target>` prefix
# (Simple string containment — sufficient for advisory purposes)
if printf '%s' "$BASH_CMD" | grep -qF "git -C $TARGET_DIR"; then
  log_event "scoped_ok" "cmd already uses git -C $TARGET_DIR"
  exit 0
fi

if printf '%s' "$BASH_CMD" | grep -qF "cd $TARGET_DIR"; then
  log_event "scoped_ok" "cmd already uses cd $TARGET_DIR"
  exit 0
fi

# ── Determine current cwd ─────────────────────────────────────────────────────
CURRENT_CWD="${PWD:-unknown}"

# If we're already in the target directory, no warning needed
if [ "$CURRENT_CWD" = "$TARGET_DIR" ]; then
  exit 0
fi

# ── Emit warning via additionalContext ───────────────────────────────────────
WARNING="⚠ Bash command contains git operation but cwd is $CURRENT_CWD, expected $TARGET_DIR. Did you forget \`git -C $TARGET_DIR\`?"

log_event "warned" "cwd=$CURRENT_CWD target=$TARGET_DIR cmd_fragment=$(printf '%s' "$BASH_CMD" | head -c 80)"

if command -v jq >/dev/null 2>&1; then
  jq -n \
    --arg ctx "$WARNING" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$ctx}}'
else
  printf '%s' "$WARNING" | python3 -c "
import json, sys
ctx = sys.stdin.read()
out = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': ctx}}
sys.stdout.write(json.dumps(out))
"
fi

exit 0
