#!/usr/bin/env bash
# common.sh — Shared utility functions for Cognitive OS hooks
#
# Usage: source "$(dirname "$0")/_lib/common.sh"
#
# Provides:
#   require_tool <tool_name>        — exit 0 if TOOL_NAME doesn't match (gate)
#   resolve_session_dir             — echo session-scoped metrics directory path
#   get_phase                       — echo current project phase from cognitive-os.yaml
#   check_private_mode              — exit 0 if private mode is active
#   read_stdin_json                 — read and cache stdin JSON (sets $_STDIN_JSON)
#   stdin_field <jq_path> [default] — extract a field from cached stdin JSON

# Guard: only load once
[ "${_COMMON_SH_LOADED:-}" = "true" ] && return 0
_COMMON_SH_LOADED="true"

# ─── Core paths ─────────────────────────────────────────────────────────────

if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  _PROJECT_DIR="$CLAUDE_PROJECT_DIR"
elif [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
  _PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
else
  _PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
_CONFIG_FILE="$_PROJECT_DIR/.cognitive-os/cognitive-os.yaml"

# Alternate config path for projects that use cognitive-os.yaml at root
[ ! -f "$_CONFIG_FILE" ] && [ -f "$_PROJECT_DIR/cognitive-os.yaml" ] && _CONFIG_FILE="$_PROJECT_DIR/cognitive-os.yaml"

# ─── require_tool ────────────────────────────────────────────────────────────
# Usage: require_tool "Agent"
# Usage: require_tool "Bash"
# Usage: require_tool "Agent" "task" "delegate"   (multiple allowed)
# Exits 0 (skip hook) if the tool doesn't match any of the provided names.
# Reads TOOL_NAME from cached stdin JSON if not set as env var.

require_tool() {
  local tool_name="${TOOL_NAME:-}"

  # If TOOL_NAME not in env, try to extract from stdin JSON
  if [ -z "$tool_name" ]; then
    read_stdin_json
    tool_name=$(echo "$_STDIN_JSON" | jq -r '.tool_name // empty' 2>/dev/null)
  fi

  for allowed in "$@"; do
    [ "$tool_name" = "$allowed" ] && return 0
  done

  exit 0
}

# ─── resolve_session_dir ─────────────────────────────────────────────────────
# Echoes the session-scoped metrics directory if a session is active,
# otherwise echoes the global metrics directory.
# Creates the directory if it doesn't exist.

resolve_session_dir() {
  local metrics_dir="$_PROJECT_DIR/.cognitive-os/metrics"
  local session_id="${COGNITIVE_OS_SESSION_ID:-}"

  if [ -z "$session_id" ]; then
    local session_file="$_PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
    [ -f "$session_file" ] && session_id=$(cat "$session_file" 2>/dev/null)
  fi

  if [ -n "$session_id" ] && [ -d "$_PROJECT_DIR/.cognitive-os/sessions/$session_id" ]; then
    local session_metrics="$_PROJECT_DIR/.cognitive-os/sessions/$session_id/metrics"
    mkdir -p "$session_metrics" 2>/dev/null
    echo "$session_metrics"
  else
    mkdir -p "$metrics_dir" 2>/dev/null
    echo "$metrics_dir"
  fi
}

# ─── get_phase ───────────────────────────────────────────────────────────────
# Echoes the current project phase from cognitive-os.yaml.
# Falls back to "reconstruction" if not found.

get_phase() {
  local default="${1:-reconstruction}"

  if [ -f "$_CONFIG_FILE" ]; then
    local parsed
    parsed=$(grep -E '^\s*phase:' "$_CONFIG_FILE" 2>/dev/null | head -1 \
      | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
    [ -n "$parsed" ] && echo "$parsed" && return 0
  fi

  echo "$default"
}

# ─── check_private_mode ──────────────────────────────────────────────────────
# Exits 0 (skip hook) if private mode is active.

check_private_mode() {
  if [ -f "/tmp/claude-private-mode-active" ]; then
    exit 0
  fi
}

# ─── read_stdin_json / stdin_field ───────────────────────────────────────────
# Reads stdin once and caches it in $_STDIN_JSON.
# Subsequent calls return the cached value.
# stdin_field extracts a jq path from the cached JSON.

# ─── check_capability_level ─────────────────────────────────────────────────
# Checks if the current hook should run based on the model capability level.
# If the hook's name is in the auto_disable list for the current level, exit 0.
#
# Usage: check_capability_level "clarification-gate"
# Call this at the top of any hook that should respect capability levels.

check_capability_level() {
  local component_name="$1"
  [ -z "$component_name" ] && return 0

  # Read capability level from config
  local level=""
  if [ -f "$_CONFIG_FILE" ]; then
    level=$(grep -A1 'model_capability:' "$_CONFIG_FILE" 2>/dev/null \
      | grep 'level:' | head -1 \
      | sed 's/.*level:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  fi
  [ -z "$level" ] && level="3"

  # Use the Python module if available, otherwise use inline logic
  local disabled=""
  if command -v python3 >/dev/null 2>&1; then
    disabled=$(python3 -c "
import sys
sys.path.insert(0, '$_PROJECT_DIR')
try:
    from lib.capability_levels import should_component_run
    if not should_component_run('$component_name', $level, '$_CONFIG_FILE'):
        print('disabled')
except Exception:
    pass
" 2>/dev/null)
  else
    # Fallback: hardcoded check for common disabled components
    case "$level" in
      4)
        case "$component_name" in
          context-management|clarification-gate|assumption-tracking|confidence-gate|model-routing|blast-radius)
            disabled="disabled"
            ;;
        esac
        ;;
      3)
        case "$component_name" in
          context-management)
            disabled="disabled"
            ;;
        esac
        ;;
    esac
  fi

  if [ "$disabled" = "disabled" ]; then
    exit 0
  fi
}

_STDIN_JSON=""
_STDIN_READ="false"

read_stdin_json() {
  if [ "$_STDIN_READ" = "false" ]; then
    _STDIN_JSON=$(cat)
    _STDIN_READ="true"
  fi
}

# Usage: stdin_field '.tool_input.command' 'default_value'
stdin_field() {
  local path="$1"
  local default="${2:-}"

  read_stdin_json

  local val
  val=$(echo "$_STDIN_JSON" | jq -r "$path // empty" 2>/dev/null)
  if [ -z "$val" ] || [ "$val" = "null" ]; then
    echo "$default"
  else
    echo "$val"
  fi
}
