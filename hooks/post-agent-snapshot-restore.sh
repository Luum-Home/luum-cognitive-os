#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: safety, agent-lifecycle, adr-003-mechanism-a, adr-099
# Post-Agent Snapshot Restore Hook — PostToolUse Agent
#
# Counterpart to pre-agent-snapshot.sh. After each Agent tool completes,
# this hook restores the working-tree state that pre-agent-snapshot.sh
# stashed so that agent writes do not silently disappear.
#
# Restore strategy:
#   1. Read the runtime marker written by pre-agent-snapshot.sh:
#      .cognitive-os/runtime/pre-agent-snapshot-<AGENT_ID>.json
#      which contains: {stash_ref, agent_id, timestamp, snapshot_id, mode}
#   2. If marker present: apply the exact stash_ref via `git stash apply`
#      (NOT pop — preserves the stash for inspection if conflicts arise)
#   3. If marker absent (fallback): find the most-recent `auto-pre-agent-*`
#      stash whose creation timestamp is within 5 minutes of now.
#   4. On apply success: log action=restored to metrics JSONL + remove marker.
#   5. On merge conflict: log action=conflict, leave stash intact, emit to
#      stderr (PostToolUse is non-blocking — operator sees the warning).
#   6. If WT was clean at snapshot time (no stash_ref): no-op, log action=skip.
#
# Bypasses:
#   COS_DISABLE_POST_AGENT_RESTORE=1   — skip entirely (env flag)
#   DISABLE_HOOK_POST_AGENT_SNAPSHOT_RESTORE=true  — killswitch via common.sh
#
# Advisory only — always exits 0. Never blocks post-agent processing.
#
# Reference: ADR-003 Mechanism A, ADR-099, R1 revert-investigation-2026-05-02.

set -uo pipefail

# ADR-028 §584: respect killswitch flag
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="post-agent-snapshot-restore"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
STASH_LOCK_LIB="$(dirname "$0")/_lib/stash-lock.sh"
[ -f "$STASH_LOCK_LIB" ] && source "$STASH_LOCK_LIB"
source "$(dirname "$0")/_lib/common.sh"

# ─── Bypass / killswitch ─────────────────────────────────────────────────────
if [ "${COS_DISABLE_POST_AGENT_RESTORE:-0}" = "1" ]; then
  exit 0
fi
check_disabled_env "post-agent-snapshot-restore"

# Validation mode: don't touch the worktree
if [ "${COS_VALIDATION_MODE:-0}" = "1" ] || [ "${COS_SUPPRESS_AGENT_SNAPSHOT:-0}" = "1" ]; then
  exit 0
fi

# ─── Paths ───────────────────────────────────────────────────────────────────
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-snapshots.jsonl"

# ─── Read stdin JSON (best-effort) ───────────────────────────────────────────
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Only process Agent tool calls
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

# ─── Resolve agent ID ────────────────────────────────────────────────────────
# Must mirror pre-agent-snapshot.sh. Native harnesses do not always echo an
# environment CLAUDE_AGENT_ID into PostToolUse, and generated random IDs made
# exact marker lookup impossible for long-running agents.
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

# ─── Helper: log metrics ──────────────────────────────────────────────────────
log_metric() {
  local action="$1"
  local stash_ref="${2:-}"
  local extra="${3:-}"
  local line
  line=$(printf '{"timestamp":"%s","event":"agent_snapshot_restore","agent_id":"%s","session_id":"%s","action":"%s","stash_ref":"%s"%s}' \
    "$TIMESTAMP" "${AGENT_ID:-unknown}" "$SESSION_ID" "$action" "${stash_ref//\"/\\\"}" "$extra")
  safe_jsonl_append "$METRICS_LOG" "$line" 2>/dev/null || true
}

# ─── Try exact match via marker file ─────────────────────────────────────────
MARKER_FILE=""
STASH_REF=""
SNAPSHOT_ID=""

if [ -n "$AGENT_ID" ]; then
  MARKER_FILE="$RUNTIME_DIR/pre-agent-snapshot-${AGENT_ID}.json"
fi

if [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && command -v jq >/dev/null 2>&1; then
  STASH_REF=$(jq -r '.stash_ref // empty' "$MARKER_FILE" 2>/dev/null || true)
  SNAPSHOT_ID=$(jq -r '.snapshot_id // empty' "$MARKER_FILE" 2>/dev/null || true)
fi

# If exact lookup failed because older markers used random IDs, recover only
# when there is a single safe candidate. Multiple pending stashes are ambiguous
# in multi-agent operation; applying the wrong stash is worse than surfacing the
# orphan.
if [ -z "$STASH_REF" ] && { [ -z "$MARKER_FILE" ] || [ ! -f "$MARKER_FILE" ]; } && command -v jq >/dev/null 2>&1; then
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
    if data.get("stash_ref"):
        candidates.append((marker.stat().st_mtime, str(marker), data.get("stash_ref", ""), data.get("snapshot_id", "")))
if len(candidates) == 1:
    _, path, stash_ref, snapshot_id = candidates[0]
    print(json.dumps({"marker": path, "stash_ref": stash_ref, "snapshot_id": snapshot_id}))
elif len(candidates) > 1:
    print(json.dumps({"ambiguous": len(candidates)}))
PYEOF
  )
  if [ -n "$CANDIDATE_SCAN" ]; then
    AMBIGUOUS_COUNT=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.ambiguous // empty' 2>/dev/null || true)
    if [ -n "$AMBIGUOUS_COUNT" ]; then
      MARKER_FILE=""
    else
      MARKER_FILE=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.marker // empty' 2>/dev/null || true)
      STASH_REF=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.stash_ref // empty' 2>/dev/null || true)
      SNAPSHOT_ID=$(printf '%s' "$CANDIDATE_SCAN" | jq -r '.snapshot_id // empty' 2>/dev/null || true)
    fi
  fi
fi

# ─── Fallback: scan stash list for most-recent auto-pre-agent-* stash ────────
FALLBACK_USED=false
if [ -z "$STASH_REF" ]; then
  if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
    cos_stash_lock_acquire "post-agent-snapshot-restore" || {
      log_metric "stash_lock_failed" "" ""
      exit 0
    }
    trap 'cos_stash_lock_release' EXIT INT TERM
  fi
  FALLBACK_USED=true
  FIVE_MIN_AGO=$(( TIMESTAMP_EPOCH - 300 ))
  # Parse stash list: stash@{N}: On branch: auto-pre-agent-<UUID>: ...
  while IFS= read -r stash_line; do
    stash_entry=$(echo "$stash_line" | cut -d: -f1 | tr -d ' ')
    stash_msg=$(echo "$stash_line" | grep -o 'auto-pre-agent-[^:]*' | head -1 || true)
    if [ -z "$stash_msg" ]; then
      continue
    fi
    # Check stash creation time via git log (best-effort)
    stash_ts=$(git -C "$PROJECT_DIR" log -1 --format="%ct" "$stash_entry" 2>/dev/null || echo 0)
    if [ "${stash_ts:-0}" -ge "$FIVE_MIN_AGO" ] 2>/dev/null; then
      STASH_REF="$stash_entry"
      break
    fi
  done < <(git -C "$PROJECT_DIR" stash list 2>/dev/null || true)
fi

# ─── No stash to restore — WT was clean or copy-only at snapshot time ────────
if [ -z "$STASH_REF" ]; then
  log_metric "skip_no_stash" "" ""
  # Exact copy-mode markers are completed by this no-op; leaving them behind
  # made healthy snapshots look like chronic orphaned restores.
  [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && rm -f "$MARKER_FILE" 2>/dev/null || true
  exit 0
fi

# ─── Apply the stash ─────────────────────────────────────────────────────────
APPLY_OUT=""
APPLY_RC=0
if command -v cos_stash_lock_acquire >/dev/null 2>&1 && [ "$FALLBACK_USED" != true ]; then
  cos_stash_lock_acquire "post-agent-snapshot-restore" || {
    log_metric "stash_lock_failed" "$STASH_REF" ""
    exit 0
  }
  trap 'cos_stash_lock_release' EXIT INT TERM
fi
APPLY_OUT=$(git -C "$PROJECT_DIR" stash apply "$STASH_REF" 2>&1) || APPLY_RC=$?
if command -v cos_stash_lock_release >/dev/null 2>&1; then
  cos_stash_lock_release
  trap - EXIT INT TERM
fi

if [ "$APPLY_RC" -eq 0 ]; then
  log_metric "restored" "$STASH_REF" \
    "$([ "$FALLBACK_USED" = true ] && printf ',"fallback":true' || true)"
  # Remove marker — restore complete. If fallback restored a stash without an
  # exact marker, also remove any marker that names the restored stash_ref.
  [ -n "$MARKER_FILE" ] && [ -f "$MARKER_FILE" ] && rm -f "$MARKER_FILE" 2>/dev/null || true
  if command -v jq >/dev/null 2>&1; then
    for candidate_marker in "$RUNTIME_DIR"/pre-agent-snapshot-*.json; do
      [ -f "$candidate_marker" ] || continue
      candidate_ref=$(jq -r '.stash_ref // empty' "$candidate_marker" 2>/dev/null || true)
      if [ "$candidate_ref" = "$STASH_REF" ]; then
        rm -f "$candidate_marker" 2>/dev/null || true
      fi
    done
  fi
else
  # Conflict or error — stash preserved, log, warn operator
  escaped_out="${APPLY_OUT//\"/\\\"}"
  log_metric "conflict" "$STASH_REF" \
    ",\"conflict_output\":\"${escaped_out:0:300}\""
  echo "[post-agent-snapshot-restore] WARN: git stash apply $STASH_REF had conflicts — stash preserved for manual inspection. Output: ${APPLY_OUT:0:200}" >&2
fi

# Always advisory — never block post-agent processing
exit 0
