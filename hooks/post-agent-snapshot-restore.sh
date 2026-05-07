#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: safety, agent-lifecycle, adr-003-mechanism-a, adr-099, adr-221
# Post-Agent Snapshot Restore Hook — PostToolUse Agent
#
# Counterpart to pre-agent-snapshot.sh. Restores pre-agent stash/snapshot state
# after an Agent tool completes. ADR-221: runtime markers persist stash_sha as
# canonical identity; stash@{N} refs are forensics only because positions drift.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="post-agent-snapshot-restore"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
STASH_LOCK_LIB="$(dirname "$0")/_lib/stash-lock.sh"
[ -f "$STASH_LOCK_LIB" ] && source "$STASH_LOCK_LIB"
source "$(dirname "$0")/_lib/common.sh"

if [ "${COS_DISABLE_POST_AGENT_RESTORE:-0}" = "1" ]; then
  exit 0
fi
check_disabled_env "post-agent-snapshot-restore"

if [ "${COS_VALIDATION_MODE:-0}" = "1" ] || [ "${COS_SUPPRESS_AGENT_SNAPSHOT:-0}" = "1" ]; then
  exit 0
fi

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-snapshots.jsonl"

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

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TIMESTAMP_EPOCH=$(date -u +%s 2>/dev/null || python3 -c "import time; print(int(time.time()))" 2>/dev/null || echo 0)
mkdir -p "$(dirname "$METRICS_LOG")" 2>/dev/null || true

json_escape() {
  local value="${1:-}"
  value=${value//\/\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/}
  printf '%s' "$value"
}

log_metric() {
  local action="$1"
  local stash_ref="${2:-}"
  local extra="${3:-}"
  local line
  line=$(printf '{"timestamp":"%s","event":"agent_snapshot_restore","agent_id":"%s","session_id":"%s","action":"%s","stash_ref":"%s"%s}' \
    "$TIMESTAMP" "$(json_escape "${AGENT_ID:-unknown}")" "$(json_escape "$SESSION_ID")" "$action" "$(json_escape "$stash_ref")" "$extra")
  safe_jsonl_append "$METRICS_LOG" "$line" 2>/dev/null || true
}

resolve_stash_sha_to_ref() {
  local wanted_sha="${1:-}"
  [ -n "$wanted_sha" ] || return 1
  git -C "$PROJECT_DIR" stash list --format='%H %gd' 2>/dev/null | awk -v sha="$wanted_sha" '$1 == sha {print $2; exit}'
}

stash_subject_for_sha() {
  local wanted_sha="${1:-}"
  [ -n "$wanted_sha" ] || return 1
  git -C "$PROJECT_DIR" stash list --format='%H%x1f%gs' 2>/dev/null | awk -F $'\x1f' -v sha="$wanted_sha" '$1 == sha {print $2; exit}'
}

MARKER_FILE=""
STASH_REF=""
STASH_SHA=""
SNAPSHOT_ID=""
if [ -n "$AGENT_ID" ]; then
  MARKER_FILE="$RUNTIME_DIR/pre-agent-snapshot-${AGENT_ID}.json"
fi

if [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && command -v jq >/dev/null 2>&1; then
  STASH_SHA=$(jq -r '.stash_sha // empty' "$MARKER_FILE" 2>/dev/null || true)
  STASH_REF=$(jq -r '.stash_ref_at_capture // .stash_ref // empty' "$MARKER_FILE" 2>/dev/null || true)
  SNAPSHOT_ID=$(jq -r '.snapshot_id // empty' "$MARKER_FILE" 2>/dev/null || true)
fi

if [ -z "$STASH_SHA" ] && [ -z "$STASH_REF" ] && { [ -z "$MARKER_FILE" ] || [ ! -f "$MARKER_FILE" ]; } && command -v jq >/dev/null 2>&1; then
  CANDIDATE_SCAN=$(RUNTIME_DIR="$RUNTIME_DIR" SESSION_ID="$SESSION_ID" python3 - <<'PYEOF' 2>/dev/null || true
import json, os
from pathlib import Path
runtime = Path(os.environ["RUNTIME_DIR"])
session_id = os.environ.get("SESSION_ID", "")
candidates = []
for marker in runtime.glob("pre-agent-snapshot-*.json"):
    try:
        data = json.loads(marker.read_text())
    except Exception:
        continue
    if data.get("session_id") and data.get("session_id") != session_id:
        continue
    if data.get("stash_sha") or data.get("stash_ref"):
        candidates.append((marker.stat().st_mtime, str(marker), data.get("stash_sha", ""), data.get("stash_ref_at_capture") or data.get("stash_ref", ""), data.get("snapshot_id", "")))
if len(candidates) == 1:
    _, path, stash_sha, stash_ref, snapshot_id = candidates[0]
    print(json.dumps({"marker": path, "stash_sha": stash_sha, "stash_ref": stash_ref, "snapshot_id": snapshot_id}))
elif len(candidates) > 1:
    print(json.dumps({"ambiguous": len(candidates)}))
PYEOF
  )
  if [ -n "$CANDIDATE_SCAN" ]; then
    AMBIGUOUS_COUNT=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.ambiguous // empty' 2>/dev/null || true)
    if [ -z "$AMBIGUOUS_COUNT" ]; then
      MARKER_FILE=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.marker // empty' 2>/dev/null || true)
      STASH_SHA=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.stash_sha // empty' 2>/dev/null || true)
      STASH_REF=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.stash_ref // empty' 2>/dev/null || true)
      SNAPSHOT_ID=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.snapshot_id // empty' 2>/dev/null || true)
    fi
  fi
fi

FALLBACK_USED=false
if [ -z "$STASH_SHA" ] && [ -z "$STASH_REF" ]; then
  if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
    cos_stash_lock_acquire "post-agent-snapshot-restore" || {
      log_metric "stash_lock_failed" "" ""
      exit 0
    }
    trap 'cos_stash_lock_release' EXIT INT TERM
  fi
  FALLBACK_USED=true
  FIVE_MIN_AGO=$(( TIMESTAMP_EPOCH - 300 ))
  while IFS= read -r stash_line; do
    stash_entry=$(echo "$stash_line" | cut -d: -f1 | tr -d ' ')
    stash_msg=$(echo "$stash_line" | grep -o 'auto-pre-agent-[^:]*' | head -1 || true)
    [ -n "$stash_msg" ] || continue
    stash_ts=$(git -C "$PROJECT_DIR" log -1 --format="%ct" "$stash_entry" 2>/dev/null || echo 0)
    if [ "${stash_ts:-0}" -ge "$FIVE_MIN_AGO" ] 2>/dev/null; then
      STASH_REF="$stash_entry"
      STASH_SHA=$(git -C "$PROJECT_DIR" rev-parse --verify "$stash_entry" 2>/dev/null || true)
      break
    fi
  done < <(git -C "$PROJECT_DIR" stash list 2>/dev/null || true)
fi

if [ -n "$STASH_SHA" ]; then
  RESOLVED_STASH_REF=$(resolve_stash_sha_to_ref "$STASH_SHA" || true)
  if [ -n "$RESOLVED_STASH_REF" ]; then
    STASH_REF="$RESOLVED_STASH_REF"
  else
    log_metric "stash_lost" "$STASH_REF" ",\"stash_sha\":\"$(json_escape "$STASH_SHA")\""
    [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && rm -f "$MARKER_FILE" 2>/dev/null || true
    exit 0
  fi
fi

if [ -z "$STASH_REF" ]; then
  log_metric "skip_no_stash" "" ""
  [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && rm -f "$MARKER_FILE" 2>/dev/null || true
  exit 0
fi

APPLY_OUT=""
APPLY_RC=0
if command -v cos_stash_lock_acquire >/dev/null 2>&1 && [ "$FALLBACK_USED" != true ]; then
  cos_stash_lock_acquire "post-agent-snapshot-restore" || {
    log_metric "stash_lock_failed" "$STASH_REF" ""
    exit 0
  }
  trap 'cos_stash_lock_release' EXIT INT TERM
fi
STASH_APPLY_ID="${STASH_SHA:-$STASH_REF}"
APPLY_OUT=$(git -C "$PROJECT_DIR" stash apply "$STASH_APPLY_ID" 2>&1) || APPLY_RC=$?
if command -v cos_stash_lock_release >/dev/null 2>&1; then
  cos_stash_lock_release
  trap - EXIT INT TERM
fi

if [ "$APPLY_RC" -eq 0 ]; then
  DROP_STATUS="not_attempted"
  DROP_OUT=""
  if [ -n "$STASH_SHA" ]; then
    STASH_SUBJECT=$(stash_subject_for_sha "$STASH_SHA" || true)
  else
    STASH_SUBJECT=$(git -C "$PROJECT_DIR" stash list --format='%gd %s' 2>/dev/null | awk -v ref="$STASH_REF" '$1 == ref {sub($1 " ", ""); print; exit}' || true)
  fi
  if printf '%s' "$STASH_SUBJECT" | grep -q 'auto-pre-agent-'; then
    DROP_LOG="${TMPDIR:-/tmp}/cos-post-agent-stash-drop.$$"
    if git -C "$PROJECT_DIR" stash drop "$STASH_REF" >"$DROP_LOG" 2>&1; then
      DROP_STATUS="dropped"
    else
      DROP_STATUS="drop_failed"
      DROP_OUT=$(head -c 200 "$DROP_LOG" 2>/dev/null || true)
    fi
    rm -f "$DROP_LOG" 2>/dev/null || true
  fi
  EXTRA=""
  [ "$FALLBACK_USED" = true ] && EXTRA="${EXTRA},\"fallback\":true"
  [ -n "$STASH_SHA" ] && EXTRA="${EXTRA},\"stash_sha\":\"$(json_escape "$STASH_SHA")\""
  if [ "$DROP_STATUS" != "not_attempted" ]; then
    EXTRA="${EXTRA},\"stash_cleanup\":\"${DROP_STATUS}\""
    [ -n "$DROP_OUT" ] && EXTRA="${EXTRA},\"stash_cleanup_error\":\"$(json_escape "$DROP_OUT")\""
  fi
  log_metric "restored" "$STASH_REF" "$EXTRA"
  [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && rm -f "$MARKER_FILE" 2>/dev/null || true
  if command -v jq >/dev/null 2>&1; then
    for candidate_marker in "$RUNTIME_DIR"/pre-agent-snapshot-*.json; do
      [ -f "$candidate_marker" ] || continue
      candidate_ref=$(jq -r '.stash_ref_at_capture // .stash_ref // empty' "$candidate_marker" 2>/dev/null || true)
      candidate_sha=$(jq -r '.stash_sha // empty' "$candidate_marker" 2>/dev/null || true)
      if [ "$candidate_ref" = "$STASH_REF" ] || { [ -n "$STASH_SHA" ] && [ "$candidate_sha" = "$STASH_SHA" ]; }; then
        rm -f "$candidate_marker" 2>/dev/null || true
      fi
    done
  fi
else
  escaped_out=$(json_escape "${APPLY_OUT:0:300}")
  log_metric "conflict" "$STASH_REF" ",\"stash_sha\":\"$(json_escape "$STASH_SHA")\",\"conflict_output\":\"${escaped_out}\""
  echo "[post-agent-snapshot-restore] WARN: git stash apply $STASH_APPLY_ID had conflicts — stash preserved for manual inspection. Output: ${APPLY_OUT:0:200}" >&2
fi

exit 0
