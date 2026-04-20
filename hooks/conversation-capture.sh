#!/usr/bin/env bash
# conversation-capture.sh — Capture session transcript for conversation memory
# Trigger: Stop (runs at session end, before session-cleanup.sh)

_HOOK_NAME="conversation-capture"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
TRANSCRIPTS_DIR="$PROJECT_DIR/.cognitive-os/transcripts"
METRICS_DIR="$(_resolve_metrics_dir)"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"

# Need session ID
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
[ -z "$SESSION_ID" ] && exit 0

mkdir -p "$TRANSCRIPTS_DIR" 2>/dev/null

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TIMESTAMP_EPOCH=$(date +%s)
DATE_PREFIX=$(date +%Y-%m-%d)

# Gather session context
SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
SESSION_META=""
[ -f "$SESSION_DIR/meta.json" ] && SESSION_META=$(cat "$SESSION_DIR/meta.json" 2>/dev/null)

# Gather session metrics (what happened)
ERRORS=0
[ -f "$METRICS_DIR/error-learning.jsonl" ] && ERRORS=$(wc -l < "$METRICS_DIR/error-learning.jsonl" 2>/dev/null | tr -d ' ')

SKILLS_USED=0
[ -f "$METRICS_DIR/skill-metrics.jsonl" ] && SKILLS_USED=$(wc -l < "$METRICS_DIR/skill-metrics.jsonl" 2>/dev/null | tr -d ' ')

REPAIRS=0
[ -f "$METRICS_DIR/repair-outcomes.jsonl" ] && REPAIRS=$(wc -l < "$METRICS_DIR/repair-outcomes.jsonl" 2>/dev/null | tr -d ' ')

# Build transcript index entry
ENTRY=$(jq -c -n \
  --arg sid "$SESSION_ID" \
  --arg ts "$TIMESTAMP" \
  --argjson te "$TIMESTAMP_EPOCH" \
  --arg date "$DATE_PREFIX" \
  --argjson errors "$ERRORS" \
  --argjson skills "$SKILLS_USED" \
  --argjson repairs "$REPAIRS" \
  '{
    session_id: $sid,
    timestamp: $ts,
    timestamp_epoch: $te,
    date: $date,
    stats: {
      errors: $errors,
      skills_used: $skills,
      repairs: $repairs
    }
  }' 2>/dev/null)

[ -z "$ENTRY" ] && exit 0

# Write transcript index
safe_jsonl_append "$TRANSCRIPTS_DIR/transcript-index.jsonl" "$ENTRY"

echo "[conversation-capture] Session $SESSION_ID indexed (errors: $ERRORS, skills: $SKILLS_USED, repairs: $REPAIRS)" >&2

exit 0
