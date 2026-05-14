#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook on Bash — legacy main_worktree policy rewriter.
# Rewrites git operations issued from a non-main cwd only when
# cognitive-os.yaml orchestration.sub_agent_cwd=main_worktree.
#
# Problem: sub-agents inherit or receive a cwd. In legacy main_worktree mode,
# `git commit` without `git -C <main>` or `cd <main> &&` may land on the wrong
# branch. In isolated_worktree mode this hook must stand down so it does not
# collapse dedicated agent worktrees back into the operator worktree.
#
# Behaviour (Layer 3 — command rewrite):
#   - Reads tool_input.command from stdin (Claude Code PreToolUse:Bash payload)
#   - Resolves main worktree via _lib/resolve-main-worktree.sh
#   - If command contains git commit|push|merge|rebase|reset|add AND
#     cwd != main worktree AND command does NOT already include git -C <target>:
#       → rewrites command: `git <sub> [args]` → `git -C <main> <sub> [args]`
#       → emits hookSpecificOutput with updatedInput (rewritten command) +
#         additionalContext explaining the rewrite
#       → logs to .cognitive-os/metrics/cwd-enforcer.jsonl with event=rewritten
#   - If rewrite fails to parse the command safely:
#       → falls back to strong advisory warning (no rewrite)
#       → logs event=warn_fallback
#   - All other cases: silent exit 0
#
# Protocol: Claude Code PreToolUse hooks support `hookSpecificOutput.updatedInput`
# to replace the tool's input before execution (documented in ADR-023, based on
# Claude Code 2.x PreToolUse return contract). This allows transparent command
# rewriting without blocking agent flow.
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

# ── Respect orchestration cwd policy ─────────────────────────────────────────
# Only the legacy main_worktree policy rewrites git commands back to the main
# worktree. The default isolated_worktree policy lets ADR-223 per-agent
# worktrees own commit isolation and prevents branch-shift races on main HEAD.
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
POLICY="isolated_worktree"
if [ -f "$CONFIG_FILE" ]; then
  extracted=$(grep -A8 '^orchestration:' "$CONFIG_FILE" 2>/dev/null \
    | grep 'sub_agent_cwd:' \
    | head -1 \
    | sed 's/.*sub_agent_cwd:[[:space:]]*//' \
    | sed 's/[[:space:]]*#.*//' \
    | tr -d '[:space:]' || true)
  [ -n "$extracted" ] && POLICY="$extracted"
fi
if [ "$POLICY" != "main_worktree" ]; then
  log_event "skip_policy" "policy=$POLICY"
  exit 0
fi

# ── Check if command contains a dangerous git operation ──────────────────────
# Match: git commit, git push, git merge, git rebase, git reset, git add
# (with any flags or arguments following)
if ! printf '%s' "$BASH_CMD" | grep -qE 'git\s+(commit|push|merge|rebase|reset|add)(\s|$)'; then
  exit 0
fi

# ── Resolve target worktree ───────────────────────────────────────────────────
TARGET_DIR=$(resolve_main_worktree "$PROJECT_DIR")

if [ -z "$TARGET_DIR" ]; then
  exit 0
fi

# ── Check if the command is already scoped to the target ─────────────────────
# Accept: `git -C <target>` OR `cd <target>` prefix
if printf '%s' "$BASH_CMD" | grep -qF "git -C $TARGET_DIR"; then
  log_event "scoped_ok" "cmd already uses git -C $TARGET_DIR"
  exit 0
fi

if printf '%s' "$BASH_CMD" | grep -qF "cd $TARGET_DIR"; then
  log_event "scoped_ok" "cmd already uses cd $TARGET_DIR"
  exit 0
fi

# Also skip if command uses any `git -C` (already explicitly scoped elsewhere)
if printf '%s' "$BASH_CMD" | grep -qE 'git\s+-C\s+'; then
  log_event "scoped_ok" "cmd already uses git -C <some-path>"
  exit 0
fi

# ── Determine current cwd ─────────────────────────────────────────────────────
CURRENT_CWD="${PWD:-unknown}"

# If we're already in the target directory, no rewrite needed
if [ "$CURRENT_CWD" = "$TARGET_DIR" ]; then
  exit 0
fi

# ── Attempt command rewrite ───────────────────────────────────────────────────
#
# Strategy: find the first `git <subcommand>` pattern in the command and
# replace it with `git -C <target> <subcommand>`. Handles:
#   git commit -m "..."      → git -C <main> commit -m "..."
#   git push origin main     → git -C <main> push origin main
#   git add file.txt         → git -C <main> add file.txt
#   cd <somewhere> && git    → unchanged (cd scopes it explicitly)
#
# Safety: if we can't do a clean rewrite, fall back to strong warning.

REWRITE_OK=0
REWRITTEN_CMD=""

# Only rewrite if the command starts with 'git' (possibly after whitespace)
# and does NOT contain '&&' followed by git (compound command — too complex to rewrite safely)
# and does NOT contain a cd before the git (explicitly scoped)
STRIPPED_CMD="${BASH_CMD#"${BASH_CMD%%[! ]*}"}"  # ltrim spaces

if printf '%s' "$STRIPPED_CMD" | grep -qE '^git\s+(commit|push|merge|rebase|reset|add)(\s|$)'; then
  # Simple case: command is just `git <sub> [args]`
  # Replace `git ` with `git -C <target> ` at the start
  REWRITTEN_CMD="git -C $(printf '%q' "$TARGET_DIR") ${STRIPPED_CMD#git }"
  REWRITE_OK=1
elif printf '%s' "$BASH_CMD" | grep -qE '(;|&&|\|\|)\s*git\s+(commit|push|merge|rebase|reset|add)'; then
  # Compound command like `cd /tmp && git commit` — too risky to blindly rewrite,
  # emit strong warning instead
  REWRITE_OK=0
fi

# ── Emit output ──────────────────────────────────────────────────────────────

if [ "$REWRITE_OK" -eq 1 ] && [ -n "$REWRITTEN_CMD" ]; then
  # SUCCESS PATH: emit updatedInput with rewritten command
  CONTEXT="[cwd-enforcer] Auto-prepended \`git -C $TARGET_DIR\` — command was issued from $CURRENT_CWD (worktree), rewrote to target main worktree per cognitive-os.yaml orchestration.sub_agent_cwd=main_worktree"

  log_event "rewritten" "cwd=$CURRENT_CWD target=$TARGET_DIR original=$(printf '%s' "$BASH_CMD" | head -c 80)"

  if command -v jq >/dev/null 2>&1; then
    jq -n \
      --arg cmd "$REWRITTEN_CMD" \
      --arg ctx "$CONTEXT" \
      '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "allow",
          updatedInput: {command: $cmd},
          additionalContext: $ctx
        }
      }'
  else
    python3 -c "
import json, sys
cmd = sys.argv[1]
ctx = sys.argv[2]
out = {
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'allow',
        'updatedInput': {'command': cmd},
        'additionalContext': ctx,
    }
}
sys.stdout.write(json.dumps(out))
" "$REWRITTEN_CMD" "$CONTEXT"
  fi

else
  # FALLBACK PATH: rewrite not safe — emit strong advisory warning
  WARNING="❌❌❌ BLOCKER WARNING: git command issued from WRONG DIRECTORY.
CWD:    $CURRENT_CWD  (worktree — commits here land on the WRONG branch)
TARGET: $TARGET_DIR  (main worktree — commits here land on main)

Auto-rewrite was NOT applied (compound command or unsafe pattern detected).
You MUST manually prefix: git -C $TARGET_DIR <subcommand> [args]

Example fix:
  WRONG:   $BASH_CMD
  CORRECT: git -C $TARGET_DIR ${BASH_CMD#git }"

  log_event "warn_fallback" "cwd=$CURRENT_CWD target=$TARGET_DIR cmd_fragment=$(printf '%s' "$BASH_CMD" | head -c 80)"

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
fi

exit 0
