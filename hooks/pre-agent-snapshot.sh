#!/usr/bin/env bash
# CONCERNS: safety, agent-lifecycle, adr-003-mechanism-a
# Pre-Agent Snapshot Hook — PreToolUse Agent
#
# Creates a working-tree snapshot before every Agent tool launch so that
# post-agent-verify.sh can restore out-of-scope writes without guessing.
#
# Snapshot strategy: `git stash push --include-untracked --keep-index`
#   - captures tracked + untracked changes (excludes .gitignore'd files)
#   - --keep-index preserves staged changes for the agent's workflow
#   - tagged "auto-pre-agent-<AGENT_ID>" so it's identifiable in git stash list
#
# Writes metadata to:
#   .cognitive-os/sessions/<SESSION_ID>/agent-<AGENT_ID>-snapshot.json
#
# Appends event to:
#   .cognitive-os/metrics/agent-snapshots.jsonl
#
# Advisory only — always exits 0. Never blocks agent launch on snapshot failure.
#
# Reference: ADR-003 Mechanism A.

set -uo pipefail

_HOOK_NAME="pre-agent-snapshot"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-snapshots.jsonl"

# Read stdin JSON (best-effort)
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

# Skip if not inside a git repo
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# Resolve agent ID — prefer env, else generate UUID-ish id
AGENT_ID="${CLAUDE_AGENT_ID:-}"
if [ -z "$AGENT_ID" ]; then
  if command -v uuidgen >/dev/null 2>&1; then
    AGENT_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
  else
    AGENT_ID="agent-$(date +%s)-$$-$RANDOM"
  fi
fi

# Extract a short prompt summary (first 200 chars) for the metadata file
PROMPT_SUMMARY=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  PROMPT_SUMMARY=$(echo "$INPUT" | jq -r '
    (.tool_input.description // .tool_input.prompt // .tool_input.task // "")
  ' 2>/dev/null | head -c 200 | tr '\n\r' '  ' || true)
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$SESSIONS_DIR" 2>/dev/null || true
mkdir -p "$(dirname "$METRICS_LOG")" 2>/dev/null || true

SNAPSHOT_FILE="$SESSIONS_DIR/agent-${AGENT_ID}-snapshot.json"

# Determine if working tree has changes
# NOTE: we check porcelain status but EXCLUDE our own session/metrics dirs
# because git stash --include-untracked would otherwise sweep them away.
TREE_DIRTY=false
STATUS_OUT=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null || true)
# Filter out .cognitive-os/ paths (our bookkeeping) to decide dirtiness
FILTERED_STATUS=$(echo "$STATUS_OUT" | grep -v -E '(^\?\? |^.. )\.cognitive-os/' || true)
if [ -n "$FILTERED_STATUS" ]; then
  TREE_DIRTY=true
fi

STASH_MSG="auto-pre-agent-${AGENT_ID}"
STASH_REF=""
SNAPSHOT_STATUS="skipped"
ERROR_MSG=""

if [ "$TREE_DIRTY" = true ]; then
  # Use pathspec exclusion to keep .cognitive-os/ in the working tree.
  # Git's stash push accepts pathspecs — we pass `.` with an exclude so the
  # stash captures every normally-tracked/untracked change except our own
  # session state (which MUST survive stash push or the metadata write
  # that follows this block would fail).
  if git -C "$PROJECT_DIR" stash push --include-untracked --keep-index \
        -m "$STASH_MSG" \
        -- ':(exclude).cognitive-os' ':(exclude).cognitive-os/**' '.' \
        >/dev/null 2>&1; then
    STASH_REF=$(git -C "$PROJECT_DIR" stash list --max-count=1 2>/dev/null | head -1 | cut -d: -f1 || true)
    if [ -n "$STASH_REF" ]; then
      SNAPSHOT_STATUS="stashed"
    else
      SNAPSHOT_STATUS="stash_created_no_ref"
      ERROR_MSG="stash push succeeded but ref could not be read"
    fi
  else
    SNAPSHOT_STATUS="stash_failed"
    ERROR_MSG="git stash push returned non-zero"
  fi
else
  SNAPSHOT_STATUS="skip_clean"
fi

# Re-create SESSIONS_DIR in case stash swallowed it despite our exclude
mkdir -p "$SESSIONS_DIR" 2>/dev/null || true
mkdir -p "$(dirname "$METRICS_LOG")" 2>/dev/null || true

# Write snapshot metadata JSON (no jq dep — manual emit to stay fast)
{
  printf '{'
  printf '"timestamp":"%s",' "$TIMESTAMP"
  printf '"agent_id":"%s",' "$AGENT_ID"
  printf '"session_id":"%s",' "$SESSION_ID"
  printf '"stash_ref":"%s",' "${STASH_REF//\"/\\\"}"
  printf '"stash_message":"%s",' "$STASH_MSG"
  printf '"status":"%s",' "$SNAPSHOT_STATUS"
  printf '"tree_dirty":%s,' "$TREE_DIRTY"
  # Prompt summary — escape double quotes and backslashes
  escaped_prompt=${PROMPT_SUMMARY//\\/\\\\}
  escaped_prompt=${escaped_prompt//\"/\\\"}
  printf '"prompt_summary":"%s"' "$escaped_prompt"
  if [ -n "$ERROR_MSG" ]; then
    printf ',"error":"%s"' "${ERROR_MSG//\"/\\\"}"
  fi
  printf '}\n'
} > "$SNAPSHOT_FILE" 2>/dev/null || true

# Append to metrics JSONL
METRICS_LINE=$(printf '{"timestamp":"%s","event":"agent_snapshot","agent_id":"%s","session_id":"%s","status":"%s","stash_ref":"%s","tree_dirty":%s}' \
  "$TIMESTAMP" "$AGENT_ID" "$SESSION_ID" "$SNAPSHOT_STATUS" "${STASH_REF}" "$TREE_DIRTY")
safe_jsonl_append "$METRICS_LOG" "$METRICS_LINE" 2>/dev/null || true

# Always advisory — never block
exit 0
