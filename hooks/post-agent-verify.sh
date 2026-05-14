#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: safety, agent-lifecycle, adr-003-mechanism-b, adr-099
# Post-Agent Verify Hook — PostToolUse Agent
#
# Verifies an agent stayed inside its declared TOUCH scope. Out-of-scope
# tracked writes are restored from the pre-agent snapshot when available and
# violations are logged to .cognitive-os/metrics/agent-violations.jsonl.
# Advisory only: never blocks the host; exits 0 on all recoverable failures.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="post-agent-verify"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
AGENT_ID="${CLAUDE_AGENT_ID:-default-agent}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
SNAPSHOT_FILE="$SESSIONS_DIR/agent-${AGENT_ID}-snapshot.json"
PROMPT_FILE="$SESSIONS_DIR/agent-${AGENT_ID}-prompt.txt"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-violations.jsonl"

INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
  fi
fi

if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

mkdir -p "$(dirname "$METRICS_LOG")" 2>/dev/null || true

if [ ! -f "$PROMPT_FILE" ]; then
  echo "post-agent-verify: No TOUCH scope found for agent ${AGENT_ID}. Skipping auto-restore." >&2
  exit 0
fi

# Extract allowed TOUCH paths. Supports prompt blocks like:
#   TOUCH only:
#     - src/foo.py
#   DO NOT TOUCH:
ALLOWED_PATHS=()
_ALLOWED_TMP=$(mktemp 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}/post-agent-verify-allowed-$$")
python3 - "$PROMPT_FILE" > "$_ALLOWED_TMP" <<'PY' 2>/dev/null || true
from pathlib import Path
import re, sys
path = Path(sys.argv[1])
lines = path.read_text(errors="ignore").splitlines()
in_touch = False
for raw in lines:
    line = raw.strip()
    low = line.lower()
    if low.startswith("touch only") or low.startswith("touch scope") or low == "touch:":
        in_touch = True
        continue
    if in_touch and (not line or low.startswith("do not touch") or low.startswith("forbidden")):
        break
    if not in_touch:
        continue
    m = re.match(r"^(?:[-*]\s+|\d+[.)]\s+)?`?([^`#]+?)`?\s*$", line)
    if m:
        value = m.group(1).strip()
        if value and value.lower() not in {"none", "n/a"}:
            print(value)
PY
while IFS= read -r allowed_path; do
  [ -n "$allowed_path" ] && ALLOWED_PATHS+=("$allowed_path")
done < "$_ALLOWED_TMP"
rm -f "$_ALLOWED_TMP" 2>/dev/null || true

if [ "${#ALLOWED_PATHS[@]}" -eq 0 ]; then
  echo "post-agent-verify: No TOUCH scope entries found. Skipping auto-restore." >&2
  exit 0
fi

_is_allowed() {
  local file="$1" allowed
  for allowed in "${ALLOWED_PATHS[@]}"; do
    allowed="${allowed%/}"
    if [ "$file" = "$allowed" ] || [[ "$file" == "$allowed/"* ]]; then
      return 0
    fi
  done
  return 1
}

SNAPSHOT_ID=""
STASH_REF=""
if [ -f "$SNAPSHOT_FILE" ] && command -v jq >/dev/null 2>&1; then
  SNAPSHOT_ID=$(jq -r '.snapshot_id // empty' "$SNAPSHOT_FILE" 2>/dev/null || true)
  STASH_REF=$(jq -r '.stash_ref // .tracked_stash_ref // empty' "$SNAPSHOT_FILE" 2>/dev/null || true)
fi

_restore_file() {
  local file="$1"
  # Prefer the exact pre-agent tracked snapshot.
  if [ -n "$STASH_REF" ] && git -C "$PROJECT_DIR" cat-file -e "${STASH_REF}:${file}" 2>/dev/null; then
    git -C "$PROJECT_DIR" checkout "$STASH_REF" -- "$file" >/dev/null 2>&1 && return 0
  fi

  # Restore untracked snapshot copies when present.
  if [ -n "$SNAPSHOT_ID" ]; then
    local snap_file="$PROJECT_DIR/.cognitive-os/snapshots/$SNAPSHOT_ID/$file"
    if [ -f "$snap_file" ]; then
      mkdir -p "$(dirname "$PROJECT_DIR/$file")" 2>/dev/null || true
      cp -p "$snap_file" "$PROJECT_DIR/$file" 2>/dev/null && return 0
    fi
  fi

  # Last resort for tracked files: reset to HEAD. For untracked out-of-scope
  # files, remove the file rather than preserving an undeclared write.
  if git -C "$PROJECT_DIR" ls-files --error-unmatch "$file" >/dev/null 2>&1; then
    git -C "$PROJECT_DIR" checkout HEAD -- "$file" >/dev/null 2>&1 && return 0
  elif [ -e "$PROJECT_DIR/$file" ]; then
    rm -rf "$PROJECT_DIR/$file" 2>/dev/null && return 0
  fi
  return 1
}

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
STATUS_OUT=$(git -C "$PROJECT_DIR" status --porcelain --untracked-files=all 2>/dev/null || true)
[ -n "$STATUS_OUT" ] || exit 0

printf '%s\n' "$STATUS_OUT" | while IFS= read -r line; do
  [ -n "$line" ] || continue
  file="${line:3}"
  # Rename entries look like "old -> new"; verify the destination path.
  case "$file" in
    *" -> "*) file="${file##* -> }" ;;
  esac
  case "$file" in
    .cognitive-os/*) continue ;;
  esac
  if _is_allowed "$file"; then
    continue
  fi

  restored=false
  if _restore_file "$file"; then
    restored=true
  fi
  echo "post-agent-verify: OUT-OF-SCOPE write restored=${restored}: ${file}" >&2
  line_json=$(python3 - "$TIMESTAMP" "$AGENT_ID" "$SESSION_ID" "$file" "$restored" <<'PY' 2>/dev/null || true
import json, sys
ts, agent, session, file, restored = sys.argv[1:]
print(json.dumps({
    "timestamp": ts,
    "event": "out_of_scope_write",
    "agent_id": agent,
    "session_id": session,
    "file": file,
    "restored": restored == "true",
}))
PY
)
  if [ -n "$line_json" ]; then
    safe_jsonl_append "$METRICS_LOG" "$line_json" 2>/dev/null || true
  fi
done

exit 0
