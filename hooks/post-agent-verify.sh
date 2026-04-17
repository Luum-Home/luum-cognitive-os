#!/usr/bin/env bash
# CONCERNS: safety, agent-lifecycle, adr-003-mechanism-b
# Post-Agent Verify Hook — PostToolUse Agent
#
# After an Agent tool completes, diff the current working tree against the
# snapshot taken by pre-agent-snapshot.sh. Any file modified that is NOT
# inside the agent's declared TOUCH scope is auto-restored from the stash.
#
# Snapshot ref lives in:
#   .cognitive-os/sessions/<SESSION_ID>/agent-<AGENT_ID>-snapshot.json
#
# TOUCH scope is read (best-effort) from:
#   .cognitive-os/sessions/<SESSION_ID>/agent-<AGENT_ID>-prompt.txt
# The orchestrator writes this file with the prompt it gave the agent. If
# absent, this hook logs a warning and does NOT auto-restore — refusing to
# guess at scope is safer than restoring legitimate work by mistake.
#
# Writes:
#   .cognitive-os/metrics/agent-violations.jsonl (one line per violation)
#
# Advisory only — always exits 0. Reference: ADR-003 Mechanism B.

set -uo pipefail

_HOOK_NAME="post-agent-verify"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
VIOLATIONS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-violations.jsonl"

# Read stdin (best-effort)
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Only process Agent tool
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
  fi
fi

# Must be inside a git repo
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# Identify the agent — prefer env var, else use the most recent snapshot file
AGENT_ID="${CLAUDE_AGENT_ID:-}"
SNAPSHOT_FILE=""

if [ -n "$AGENT_ID" ] && [ -f "$SESSIONS_DIR/agent-${AGENT_ID}-snapshot.json" ]; then
  SNAPSHOT_FILE="$SESSIONS_DIR/agent-${AGENT_ID}-snapshot.json"
else
  # Fall back to most recent agent-*-snapshot.json in the session dir
  if [ -d "$SESSIONS_DIR" ]; then
    SNAPSHOT_FILE=$(ls -t "$SESSIONS_DIR"/agent-*-snapshot.json 2>/dev/null | head -1 || true)
  fi
fi

if [ -z "$SNAPSHOT_FILE" ] || [ ! -f "$SNAPSHOT_FILE" ]; then
  # No snapshot means Mechanism A did not record one — nothing we can verify.
  exit 0
fi

# Read stash ref + agent_id from the snapshot file
STASH_REF=""
RECORDED_AGENT_ID=""
SNAPSHOT_STATUS=""
if command -v jq >/dev/null 2>&1; then
  STASH_REF=$(jq -r '.stash_ref // empty' "$SNAPSHOT_FILE" 2>/dev/null || true)
  RECORDED_AGENT_ID=$(jq -r '.agent_id // empty' "$SNAPSHOT_FILE" 2>/dev/null || true)
  SNAPSHOT_STATUS=$(jq -r '.status // empty' "$SNAPSHOT_FILE" 2>/dev/null || true)
else
  # Regex fallback
  STASH_REF=$(grep -o '"stash_ref":"[^"]*"' "$SNAPSHOT_FILE" 2>/dev/null | head -1 | sed 's/"stash_ref":"\([^"]*\)"/\1/')
  RECORDED_AGENT_ID=$(grep -o '"agent_id":"[^"]*"' "$SNAPSHOT_FILE" 2>/dev/null | head -1 | sed 's/"agent_id":"\([^"]*\)"/\1/')
  SNAPSHOT_STATUS=$(grep -o '"status":"[^"]*"' "$SNAPSHOT_FILE" 2>/dev/null | head -1 | sed 's/"status":"\([^"]*\)"/\1/')
fi

[ -z "$AGENT_ID" ] && AGENT_ID="$RECORDED_AGENT_ID"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# If the tree was clean at snapshot time, there's no stash to diff against.
# Any changes now are all new — we only care about scope, not restoration.
if [ "$SNAPSHOT_STATUS" = "skip_clean" ] || [ -z "$STASH_REF" ]; then
  # Detect the agent's writes via git status vs HEAD since snapshot
  CHANGED_FILES=$(git -C "$PROJECT_DIR" diff --name-only HEAD 2>/dev/null || true)
  UNTRACKED=$(git -C "$PROJECT_DIR" ls-files --others --exclude-standard 2>/dev/null || true)
  if [ -z "$CHANGED_FILES" ] && [ -z "$UNTRACKED" ]; then
    exit 0
  fi
  ALL_CHANGED=$(printf '%s\n%s\n' "$CHANGED_FILES" "$UNTRACKED" | awk 'NF')
else
  # Diff current tree against the stash
  ALL_CHANGED=$(git -C "$PROJECT_DIR" diff --name-only "$STASH_REF" 2>/dev/null || true)
fi

if [ -z "$ALL_CHANGED" ]; then
  exit 0
fi

# Read TOUCH scope from the prompt file (one path per line, # for comments)
PROMPT_FILE="$SESSIONS_DIR/agent-${AGENT_ID}-prompt.txt"
TOUCH_SCOPE=""
if [ -f "$PROMPT_FILE" ]; then
  # Extract TOUCH lines: heuristic — look for "TOUCH:" or "TOUCH only:" blocks
  # and grab relative path-looking tokens until blank/terminator line.
  TOUCH_SCOPE=$(awk '
    BEGIN { in_touch=0 }
    /^[[:space:]]*TOUCH([[:space:]]+only)?:/ { in_touch=1; next }
    /^[[:space:]]*DO NOT TOUCH:|^[[:space:]]*PROHIBIT/ { in_touch=0 }
    /^[[:space:]]*$/ { if (in_touch) in_touch=0 }
    { if (in_touch) print }
  ' "$PROMPT_FILE" | tr -d '-' | tr ',' '\n' | awk '{$1=$1; print}' | grep -E '[A-Za-z0-9_./-]+\.[a-zA-Z0-9]+|/$' | awk 'NF')
fi

# If we cannot determine TOUCH scope, warn and bail — do not guess
if [ -z "$TOUCH_SCOPE" ]; then
  echo "" >&2
  echo "=== POST-AGENT-VERIFY: WARNING ===" >&2
  echo "No TOUCH scope found for agent $AGENT_ID (expected: $PROMPT_FILE)." >&2
  echo "Skipping auto-restore to avoid undoing legitimate work." >&2
  echo "Files changed by agent:" >&2
  echo "$ALL_CHANGED" | sed 's/^/  /' >&2
  echo "" >&2

  # Still log the event
  ENTRY=$(printf '{"timestamp":"%s","event":"verify_skipped_no_scope","agent_id":"%s","session_id":"%s","changed_count":%d}' \
    "$TIMESTAMP" "$AGENT_ID" "$SESSION_ID" "$(echo "$ALL_CHANGED" | wc -l | tr -d ' ')")
  safe_jsonl_append "$VIOLATIONS_LOG" "$ENTRY" 2>/dev/null || true
  exit 0
fi

# Classify each changed file as in_scope or forbidden
FORBIDDEN_FILES=""
while IFS= read -r file; do
  [ -z "$file" ] && continue
  MATCH=false
  while IFS= read -r scope; do
    [ -z "$scope" ] && continue
    # Exact match
    if [ "$file" = "$scope" ]; then
      MATCH=true; break
    fi
    # Directory prefix match (scope ends in /)
    case "$scope" in
      */) case "$file" in "$scope"*) MATCH=true; break ;; esac ;;
    esac
    # Prefix-with-glob heuristic: "dir/foo*" or "dir/*.sh"
    case "$file" in
      $scope) MATCH=true; break ;;
    esac
  done <<< "$TOUCH_SCOPE"

  if [ "$MATCH" = false ]; then
    FORBIDDEN_FILES="${FORBIDDEN_FILES}${file}"$'\n'
  fi
done <<< "$ALL_CHANGED"

FORBIDDEN_FILES=$(echo "$FORBIDDEN_FILES" | awk 'NF')

if [ -z "$FORBIDDEN_FILES" ]; then
  # All changes in scope — nothing to do
  exit 0
fi

# Restore forbidden files from stash (only meaningful if we have a stash ref)
RESTORED=""
if [ -n "$STASH_REF" ]; then
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    if git -C "$PROJECT_DIR" checkout "$STASH_REF" -- "$file" >/dev/null 2>&1; then
      RESTORED="${RESTORED}${file}"$'\n'
    fi
  done <<< "$FORBIDDEN_FILES"
fi

# Alert
echo "" >&2
echo "=== POST-AGENT-VERIFY: OUT-OF-SCOPE WRITE DETECTED ===" >&2
echo "Agent: $AGENT_ID" >&2
echo "AGENT WROTE OUTSIDE SCOPE:" >&2
echo "$FORBIDDEN_FILES" | sed 's/^/  /' >&2
if [ -n "$RESTORED" ]; then
  echo "Auto-restored from snapshot:" >&2
  echo "$RESTORED" | sed 's/^/  /' >&2
else
  echo "NOTE: no stash ref available — files NOT restored; manual review required." >&2
fi
echo "" >&2

# Log each violation
while IFS= read -r file; do
  [ -z "$file" ] && continue
  RESTORED_FLAG=false
  if echo "$RESTORED" | grep -Fxq "$file"; then
    RESTORED_FLAG=true
  fi
  # Escape path for JSON
  esc_file=${file//\\/\\\\}
  esc_file=${esc_file//\"/\\\"}
  ENTRY=$(printf '{"timestamp":"%s","event":"out_of_scope_write","agent_id":"%s","session_id":"%s","file":"%s","restored":%s}' \
    "$TIMESTAMP" "$AGENT_ID" "$SESSION_ID" "$esc_file" "$RESTORED_FLAG")
  safe_jsonl_append "$VIOLATIONS_LOG" "$ENTRY" 2>/dev/null || true
done <<< "$FORBIDDEN_FILES"

exit 0
