#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Codebase Itinerary Capture
#
# ADR-256 Phase 3: append content-free Read/Grep/Glob/LS metadata to
#   .cognitive-os/metrics/codebase-itinerary.jsonl
#
# Privacy contract:
# - never writes file contents, tool output, raw grep/glob patterns, or raw paths;
# - records only hashes and coarse shape metadata needed to prove inspection flow;
# - always advisory/observe-only and exits 0.

set -uo pipefail
trap 'exit 0' ERR

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
_HOOK_NAME="codebase-itinerary-capture"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

TOOL_NAME=$(stdin_field '.tool_name' '')
case "$TOOL_NAME" in
  Read|Grep|Glob|LS) ;;
  *) exit 0 ;;
esac

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

_hash12() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | shasum -a 256 2>/dev/null | cut -c1-12 || printf '000000000000'
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$1" | sha256sum 2>/dev/null | cut -c1-12 || printf '000000000000'
  else
    printf '000000000000'
  fi
}

_path_depth() {
  local value="$1"
  [ -z "$value" ] && { printf '0'; return; }
  printf '%s' "$value" | awk -F/ '{ count=0; for (i=1; i<=NF; i++) if ($i != "") count++; print count }' 2>/dev/null || printf '0'
}

_path_ext() {
  local value="$1"
  local base ext
  base=${value##*/}
  case "$base" in
    *.*)
      ext=${base##*.}
      printf '%s' "$ext" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-.' | cut -c1-24
      ;;
    *) printf '' ;;
  esac
}

_json_string() {
  printf '%s' "$1" | jq -Rs . 2>/dev/null || printf '""'
}

_input_value() {
  local jq_path="$1"
  echo "$_STDIN_JSON" | jq -r "$jq_path // empty" 2>/dev/null || true
}

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-${CODEX_SESSION_ID:-}}}"
[ -z "$SESSION_ID" ] && SESSION_ID="${PPID:-0}"
TASK_ID="${COS_TASK_ID:-session-${SESSION_ID}}"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
TOOL_INPUT_RAW=$(echo "$_STDIN_JSON" | jq -c '.tool_input // {}' 2>/dev/null || echo '{}')
INPUT_HASH=$(_hash12 "$TOOL_INPUT_RAW")

ACTION_KIND="observe"
TARGET_KIND="unknown"
TARGET_HASH=""
PATH_EXT=""
PATH_DEPTH=0
ABSOLUTE_PATH=false
SELECTOR_KIND="none"
SELECTOR_HASH=""
SELECTOR_LENGTH=0
INCLUDE_HASH=""
INPUT_KEYS=$(echo "$TOOL_INPUT_RAW" | jq -c 'keys | sort' 2>/dev/null || echo '[]')

case "$TOOL_NAME" in
  Read)
    ACTION_KIND="read"
    TARGET_KIND="file"
    TARGET_VALUE=$(_input_value '.tool_input.file_path')
    TARGET_HASH=$(_hash12 "$TARGET_VALUE")
    PATH_EXT=$(_path_ext "$TARGET_VALUE")
    PATH_DEPTH=$(_path_depth "$TARGET_VALUE")
    case "$TARGET_VALUE" in /*) ABSOLUTE_PATH=true ;; esac
    ;;
  LS)
    ACTION_KIND="list"
    TARGET_KIND="directory"
    TARGET_VALUE=$(_input_value '.tool_input.path')
    TARGET_HASH=$(_hash12 "$TARGET_VALUE")
    PATH_DEPTH=$(_path_depth "$TARGET_VALUE")
    case "$TARGET_VALUE" in /*) ABSOLUTE_PATH=true ;; esac
    ;;
  Grep)
    ACTION_KIND="search"
    TARGET_KIND="query"
    TARGET_VALUE=$(_input_value '.tool_input.path')
    TARGET_HASH=$(_hash12 "$TARGET_VALUE")
    PATH_DEPTH=$(_path_depth "$TARGET_VALUE")
    case "$TARGET_VALUE" in /*) ABSOLUTE_PATH=true ;; esac
    PATTERN_VALUE=$(_input_value '.tool_input.pattern')
    SELECTOR_KIND="grep-pattern"
    SELECTOR_HASH=$(_hash12 "$PATTERN_VALUE")
    SELECTOR_LENGTH=${#PATTERN_VALUE}
    INCLUDE_VALUE=$(_input_value '.tool_input.include')
    [ -n "$INCLUDE_VALUE" ] && INCLUDE_HASH=$(_hash12 "$INCLUDE_VALUE")
    ;;
  Glob)
    ACTION_KIND="glob"
    TARGET_KIND="glob"
    TARGET_VALUE=$(_input_value '.tool_input.path')
    TARGET_HASH=$(_hash12 "$TARGET_VALUE")
    PATH_DEPTH=$(_path_depth "$TARGET_VALUE")
    case "$TARGET_VALUE" in /*) ABSOLUTE_PATH=true ;; esac
    PATTERN_VALUE=$(_input_value '.tool_input.pattern')
    SELECTOR_KIND="glob-pattern"
    SELECTOR_HASH=$(_hash12 "$PATTERN_VALUE")
    SELECTOR_LENGTH=${#PATTERN_VALUE}
    ;;
esac

SUCCESS=true
EXIT_CODE=$(_input_value '.tool_response.exit_code')
if [ -n "$EXIT_CODE" ] && [ "$EXIT_CODE" != "0" ] && [ "$EXIT_CODE" != "null" ]; then
  SUCCESS=false
fi

TIMESTAMP_JSON=$(_json_string "$TIMESTAMP")
SESSION_JSON=$(_json_string "$SESSION_ID")
TASK_JSON=$(_json_string "$TASK_ID")
TOOL_JSON=$(_json_string "$TOOL_NAME")
ACTION_JSON=$(_json_string "$ACTION_KIND")
TARGET_KIND_JSON=$(_json_string "$TARGET_KIND")
TARGET_HASH_JSON=$(_json_string "$TARGET_HASH")
PATH_EXT_JSON=$(_json_string "$PATH_EXT")
SELECTOR_KIND_JSON=$(_json_string "$SELECTOR_KIND")
SELECTOR_HASH_JSON=$(_json_string "$SELECTOR_HASH")
INCLUDE_HASH_JSON=$(_json_string "$INCLUDE_HASH")
INPUT_HASH_JSON=$(_json_string "$INPUT_HASH")

JSON_LINE=$(jq -cn \
  --argjson timestamp "$TIMESTAMP_JSON" \
  --argjson session_id "$SESSION_JSON" \
  --argjson task_id "$TASK_JSON" \
  --argjson tool "$TOOL_JSON" \
  --argjson action_kind "$ACTION_JSON" \
  --argjson target_kind "$TARGET_KIND_JSON" \
  --argjson target_hash "$TARGET_HASH_JSON" \
  --argjson path_ext "$PATH_EXT_JSON" \
  --argjson selector_kind "$SELECTOR_KIND_JSON" \
  --argjson selector_hash "$SELECTOR_HASH_JSON" \
  --argjson include_hash "$INCLUDE_HASH_JSON" \
  --argjson input_hash "$INPUT_HASH_JSON" \
  --argjson input_keys "$INPUT_KEYS" \
  --argjson path_depth "$PATH_DEPTH" \
  --argjson selector_length "$SELECTOR_LENGTH" \
  --argjson absolute_path "$ABSOLUTE_PATH" \
  --argjson success "$SUCCESS" \
  '{schema_version:"codebase-itinerary.v1", timestamp:$timestamp, session_id:$session_id, task_id:$task_id, tool:$tool, action_kind:$action_kind, target_kind:$target_kind, target_ref:{hash_sha256_12:$target_hash, path_ext:$path_ext, path_depth:$path_depth, absolute_path:$absolute_path}, selector_ref:{kind:$selector_kind, hash_sha256_12:$selector_hash, length:$selector_length, include_hash_sha256_12:$include_hash}, input_hash_sha256_12:$input_hash, input_keys:$input_keys, success:$success, privacy:{content_free:true, raw_paths:false, raw_patterns:false, raw_tool_output:false}}' \
  2>/dev/null || true)

[ -n "$JSON_LINE" ] || exit 0
METRICS_DIR=$(_resolve_metrics_dir)
safe_jsonl_append "$METRICS_DIR/codebase-itinerary.jsonl" "$JSON_LINE" 2>/dev/null || true

exit 0
