#!/usr/bin/env bash
# PreToolUse hook: Blast Radius Estimation
# Fires on "Agent" tool use — estimates the impact scope of a task
# Advisory only (exit 0) — does NOT block, but warns for HIGH/CRITICAL
# Must complete in <3 seconds
#
# PURPOSE: Estimates how many files and systems a task will affect.
# High blast radius tasks need extra caution, sampling, and review.

set -uo pipefail

_HOOK_NAME="blast-radius"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 4
check_capability_level "blast-radius"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
BLAST_LOG="$METRICS_DIR/blast-radius.jsonl"

# Session-aware metrics directory
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
  if [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ]; then
    METRICS_DIR="$SESSION_METRICS"
    BLAST_LOG="$SESSION_METRICS/blast-radius.jsonl"
  fi
fi

# Read stdin (JSON with tool_name, tool_input)
INPUT=$(cat)

# Exit early if no input
if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Check private mode — skip if active
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Extract agent prompt/description
AGENT_PROMPT=$(echo "$INPUT" | jq -r '
  .tool_input.prompt // .tool_input.description // ""
' 2>/dev/null)

if [ -z "$AGENT_PROMPT" ] || [ "$AGENT_PROMPT" = "null" ]; then
  exit 0
fi

# --- Blast Radius Estimation ---
FILE_SCORE=0
INFRA_HIT=false
SECURITY_HIT=false
SIGNALS=""
SIGNAL_COUNT=0

add_signal() {
  SIGNAL_COUNT=$((SIGNAL_COUNT + 1))
  if [ -z "$SIGNALS" ]; then
    SIGNALS="$1"
  else
    SIGNALS="$SIGNALS\n$1"
  fi
}

# --- File scope estimation ---

# Explicit file paths mentioned (count unique path-like patterns)
FILE_PATH_COUNT=$(echo "$AGENT_PROMPT" | grep -oE '[a-zA-Z0-9_./-]+\.(go|ts|py|js|yaml|yml|json|md|sh|jsx|tsx|css|sql|proto|toml)' | sort -u | wc -l | tr -d ' ')
if [ "$FILE_PATH_COUNT" -gt 0 ]; then
  FILE_SCORE=$((FILE_SCORE + FILE_PATH_COUNT))
  add_signal "FILE PATHS: $FILE_PATH_COUNT explicit file references detected"
fi

# Directory patterns (each directory implies multiple files)
DIR_COUNT=$(echo "$AGENT_PROMPT" | grep -oE '(src|internal|pkg|lib|cmd|hooks|rules|skills|tests|services|api|domain|application|infrastructure)/[a-zA-Z0-9_/-]*' | sort -u | wc -l | tr -d ' ')
if [ "$DIR_COUNT" -gt 0 ]; then
  FILE_SCORE=$((FILE_SCORE + DIR_COUNT * 5))
  add_signal "DIRECTORIES: $DIR_COUNT directory references (estimated ~$((DIR_COUNT * 5)) files)"
fi

# Cross-service keywords (multiplier)
if echo "$AGENT_PROMPT" | grep -qiE '\b(all services|every endpoint|across the project|across services|every service|all endpoints|all controllers|all repositories|every module)\b'; then
  FILE_SCORE=$((FILE_SCORE + 50))
  add_signal "CROSS-SERVICE: broad scope keywords detected (all services/endpoints/controllers)"
fi

# Bulk operation keywords
if echo "$AGENT_PROMPT" | grep -qiE '\b(rebrand|rename everywhere|migrate all|replace all|bulk update|mass rename|global replace|find and replace)\b'; then
  FILE_SCORE=$((FILE_SCORE + 30))
  add_signal "BULK OP: bulk/mass operation keywords detected"
fi

# Explicit file counts in prompt
EXPLICIT_COUNT=$(echo "$AGENT_PROMPT" | grep -oE '[0-9]+\s*(files?|endpoints?|services?|modules?|components?)' | grep -oE '[0-9]+' | sort -rn | head -1)
if [ -n "$EXPLICIT_COUNT" ] && [ "$EXPLICIT_COUNT" -gt "$FILE_SCORE" ]; then
  FILE_SCORE=$EXPLICIT_COUNT
  add_signal "EXPLICIT COUNT: $EXPLICIT_COUNT items mentioned in prompt"
fi

# --- Infrastructure detection ---
if echo "$AGENT_PROMPT" | grep -qiE '\b(docker|docker-compose|container|kubernetes|k8s|helm|terraform|deploy|deployment|pipeline|ci/cd|github actions|dockerfile)\b'; then
  INFRA_HIT=true
  add_signal "INFRASTRUCTURE: infrastructure/deployment keywords detected"
fi

if echo "$AGENT_PROMPT" | grep -qiE '\b(database|migration|schema|alter table|create table|drop|truncate|seed|fixture|sql)\b'; then
  INFRA_HIT=true
  add_signal "DATABASE: database/migration keywords detected"
fi

# --- Security detection ---
if echo "$AGENT_PROMPT" | grep -qiE '\b(auth|authentication|authorization|permission|credential|secret|token|jwt|oauth|api.?key|password|encrypt|decrypt|certificate|ssl|tls|cors|csrf|xss|rbac|acl)\b'; then
  SECURITY_HIT=true
  add_signal "SECURITY: auth/security keywords detected"
fi

# --- Classification ---
RADIUS="LOW"
if [ "$INFRA_HIT" = true ] || [ "$SECURITY_HIT" = true ] || [ "$FILE_SCORE" -gt 50 ]; then
  RADIUS="CRITICAL"
elif [ "$FILE_SCORE" -gt 20 ]; then
  RADIUS="HIGH"
elif [ "$FILE_SCORE" -gt 5 ]; then
  RADIUS="MEDIUM"
fi

# --- Logging ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

AGENT_DESC=$(echo "$AGENT_PROMPT" | head -c 100)
ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg radius "$RADIUS" \
  --argjson file_score "$FILE_SCORE" \
  --argjson infra "$INFRA_HIT" \
  --argjson security "$SECURITY_HIT" \
  --argjson signals "$SIGNAL_COUNT" \
  --arg agent "$AGENT_DESC" \
  '{timestamp: $ts, radius: $radius, file_score: $file_score, infra: $infra, security: $security, signals: $signals, agent: $agent}')
safe_jsonl_append "$BLAST_LOG" "$ENTRY"

# --- Output ---
# ADR-023: prefer hookSpecificOutput.additionalContext (mutation-style) over
# free-form stderr warnings. Claude Code surfaces additionalContext to the
# orchestrator without surfacing it as a "block" event, which is exactly the
# advisory semantics we want here. We still allow the agent to launch.
emit_additional_context() {
  local context="$1"
  jq -c -n \
    --arg ctx "$context" \
    '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "allow",
        additionalContext: $ctx
      }
    }'
}

if [ "$RADIUS" = "CRITICAL" ]; then
  EXTRA=""
  [ "$INFRA_HIT" = true ]    && EXTRA="${EXTRA} Infrastructure changes detected."
  [ "$SECURITY_HIT" = true ] && EXTRA="${EXTRA} Security-sensitive changes detected."
  CTX="BLAST RADIUS WARNING: this operation is CRITICAL. Estimated impact: ${FILE_SCORE}+ files.${EXTRA}"
  CTX="${CTX} Signals:\n$(printf '%b' "$SIGNALS")"
  CTX="${CTX}\nRECOMMENDATION: use /sandbox-sample before scaling. Consider /exhaustive-prompt for scope enumeration. For security changes, ensure adversarial review is included."
  emit_additional_context "$CTX"
elif [ "$RADIUS" = "HIGH" ]; then
  CTX="BLAST RADIUS WARNING: this operation is HIGH-impact. Estimated impact: ${FILE_SCORE} files."
  CTX="${CTX} Signals:\n$(printf '%b' "$SIGNALS")"
  CTX="${CTX}\nRECOMMENDATION: consider /sandbox-sample for validation before full-scale apply."
  emit_additional_context "$CTX"
fi

# Advisory only — always exit 0
exit 0
