#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: safety, agent-lifecycle, adr-222, adr-221
# ADR-222 Phase 2 — commit a pre-agent snapshot plan only after launch gates passed.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="agent-launch-confirmed"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
STASH_LOCK_LIB="$(dirname "$0")/_lib/stash-lock.sh"
[ -f "$STASH_LOCK_LIB" ] && source "$STASH_LOCK_LIB"

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-snapshots.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "${COS_SUPPRESS_AGENT_SNAPSHOT:-0}" = "1" ] || [ "${COS_VALIDATION_MODE:-0}" = "1" ]; then
  exit 0
fi

INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
  fi
fi
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

AGENT_ID="${CLAUDE_AGENT_ID:-}"
if [ -z "$AGENT_ID" ] && [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  AGENT_ID=$(echo "$INPUT" | jq -r '
    .tool_input.agent_id
    // .tool_use_id
    // .tool_input.tool_use_id
    // .tool_input.id
    // empty
  ' 2>/dev/null || true)
fi
if [ -z "$AGENT_ID" ] && [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_INPUT_CANONICAL=$(echo "$INPUT" | jq -cS '.tool_input // {}' 2>/dev/null || true)
  if [ -n "$TOOL_INPUT_CANONICAL" ]; then
    if command -v shasum >/dev/null 2>&1; then
      AGENT_ID="payload-$(printf '%s' "$TOOL_INPUT_CANONICAL" | shasum -a 256 | awk '{print substr($1,1,16)}')"
    elif command -v sha256sum >/dev/null 2>&1; then
      AGENT_ID="payload-$(printf '%s' "$TOOL_INPUT_CANONICAL" | sha256sum | awk '{print substr($1,1,16)}')"
    fi
  fi
fi
[ -n "$AGENT_ID" ] || exit 0

PLAN_FILE="$RUNTIME_DIR/pre-agent-plan-${AGENT_ID}.json"
MARKER_FILE="$RUNTIME_DIR/pre-agent-snapshot-${AGENT_ID}.json"
SNAPSHOT_FILE="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/agent-${AGENT_ID}-snapshot.json"
[ -f "$PLAN_FILE" ] || exit 0
mkdir -p "$RUNTIME_DIR" "$(dirname "$METRICS_LOG")" 2>/dev/null || true

if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
  cos_stash_lock_acquire "agent-launch-confirmed" || {
    safe_jsonl_append "$METRICS_LOG" "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"agent_snapshot_commit\",\"agent_id\":\"$AGENT_ID\",\"session_id\":\"$SESSION_ID\",\"status\":\"stash_lock_failed\"}" 2>/dev/null || true
    exit 0
  }
  trap 'cos_stash_lock_release' EXIT INT TERM
fi

COMMIT_RESULT=$(PYTHONPATH="$OS_ROOT" python3 - "$PROJECT_DIR" "$PLAN_FILE" <<'PYEOF' 2>/dev/null
import json, sys
from pathlib import Path
from lib.snapshot_manager import commit_snapshot_plan
repo = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
plan = json.loads(plan_path.read_text())
print(json.dumps(commit_snapshot_plan(repo, plan)))
PYEOF
) || COMMIT_RESULT='{"status":"error","tracked_stash_ref":null,"tracked_stash_sha":null,"snapshot_id":""}'

if command -v cos_stash_lock_release >/dev/null 2>&1; then
  cos_stash_lock_release
  trap - EXIT INT TERM
fi

if command -v jq >/dev/null 2>&1; then
  SNAPSHOT_STATUS=$(printf '%s' "$COMMIT_RESULT" | jq -r '.status // "error"' 2>/dev/null || echo error)
  STASH_REF=$(printf '%s' "$COMMIT_RESULT" | jq -r '.tracked_stash_ref // empty' 2>/dev/null || true)
  STASH_SHA=$(printf '%s' "$COMMIT_RESULT" | jq -r '.tracked_stash_sha // empty' 2>/dev/null || true)
  SNAPSHOT_ID=$(printf '%s' "$COMMIT_RESULT" | jq -r '.snapshot_id // empty' 2>/dev/null || true)
else
  SNAPSHOT_STATUS="committed"
  STASH_REF=""
  STASH_SHA=""
  SNAPSHOT_ID=""
fi

if [ -n "$STASH_SHA" ] || [ -n "$STASH_REF" ] || [ -n "$SNAPSHOT_ID" ]; then
  printf '{"schema_version":"pre-agent-snapshot/v2","stash_sha":"%s","stash_ref_at_capture":"%s","stash_ref":"%s","agent_id":"%s","session_id":"%s","timestamp":"%s","snapshot_id":"%s","mode":"copy"}\n' \
    "${STASH_SHA//\"/\\\"}" "${STASH_REF//\"/\\\"}" "${STASH_REF//\"/\\\"}" "$AGENT_ID" "$SESSION_ID" "$TIMESTAMP" "${SNAPSHOT_ID//\"/\\\"}" \
    > "$MARKER_FILE" 2>/dev/null || true

  if [ -f "$SNAPSHOT_FILE" ] && command -v jq >/dev/null 2>&1; then
    SNAPSHOT_TMP=$(mktemp "${TMPDIR:-/tmp}/agent-snapshot.XXXXXX.json")
    if jq \
      --arg status "$SNAPSHOT_STATUS" \
      --arg stash_ref "$STASH_REF" \
      --arg stash_sha "$STASH_SHA" \
      --arg snapshot_id "$SNAPSHOT_ID" \
      '.status=$status | .stash_ref=$stash_ref | .stash_sha=$stash_sha | .snapshot_id=$snapshot_id | .launch_confirmed=true' \
      "$SNAPSHOT_FILE" > "$SNAPSHOT_TMP" 2>/dev/null; then
      mv "$SNAPSHOT_TMP" "$SNAPSHOT_FILE" 2>/dev/null || rm -f "$SNAPSHOT_TMP" 2>/dev/null || true
    else
      rm -f "$SNAPSHOT_TMP" 2>/dev/null || true
    fi
  fi
fi
rm -f "$PLAN_FILE" 2>/dev/null || true
safe_jsonl_append "$METRICS_LOG" "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"agent_snapshot_commit\",\"agent_id\":\"$AGENT_ID\",\"session_id\":\"$SESSION_ID\",\"status\":\"$SNAPSHOT_STATUS\",\"stash_ref\":\"$STASH_REF\",\"stash_sha\":\"$STASH_SHA\",\"snapshot_id\":\"$SNAPSHOT_ID\"}" 2>/dev/null || true
exit 0
