#!/usr/bin/env bash
# SCOPE: both
# hook-pipe.sh — Inter-hook data sharing within an event chain
#
# Usage:
#   source "$(dirname "$0")/_lib/hook-pipe.sh"
#   hook_emit "score" "72"            # write a value for downstream hooks
#   hook_read "clarification_score"   # read a value emitted by a prior hook
#
# Pipe directory: .cognitive-os/.hook-pipe/
# Pipe files:     <event>-<key>.val  (one value per key per event invocation)
#
# Lifecycle:
#   - Values persist within a single event chain invocation.
#   - The pipe directory is cleared at PreToolUse start by the rate-limiter.sh
#     (or any hook that runs first). To clear manually: hook_pipe_clear.
#   - Values are NOT cleared between different event types (e.g. PreToolUse does
#     not clear PostToolUse pipe data). Each event has its own namespace.
#
# Author: luum

# Guard: only load once
[ "${_HOOK_PIPE_SH_LOADED:-}" = "true" ] && return 0
_HOOK_PIPE_SH_LOADED="true"

# Resolve project directory (reuse common.sh resolution if already loaded)
if [ -z "${_PROJECT_DIR:-}" ]; then
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    _PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
  elif [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    _PROJECT_DIR="$CODEX_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    _PROJECT_DIR="$CLAUDE_PROJECT_DIR"
  else
    _PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  fi
fi

_HOOK_PIPE_DIR="$_PROJECT_DIR/.cognitive-os/.hook-pipe"

# ─── hook_emit ────────────────────────────────────────────────────────────────
# Write a key-value pair to the pipe for the current event.
#
# Usage: hook_emit <key> <value> [event_override]
#
# Arguments:
#   key            — alphanumeric + underscore identifier (e.g. "score", "clarification_score")
#   value          — value to store (string; newlines are collapsed to spaces)
#   event_override — optional event name (default: $CLAUDE_HOOK_EVENT or "unknown")
#
# The file is written atomically via a temp file to avoid partial reads.

hook_emit() {
  local key="$1"
  local value="$2"
  local event="${3:-${CLAUDE_HOOK_EVENT:-unknown}}"

  # Validate key: alphanumeric + underscore only
  if ! echo "$key" | grep -qE '^[a-zA-Z_][a-zA-Z0-9_]*$'; then
    return 1
  fi

  mkdir -p "$_HOOK_PIPE_DIR" 2>/dev/null || return 0

  local pipe_file="$_HOOK_PIPE_DIR/${event}-${key}.val"
  local tmp_file="${pipe_file}.tmp.$$"

  # Collapse newlines to spaces for single-line storage
  printf '%s' "$value" | tr '\n' ' ' > "$tmp_file" 2>/dev/null && \
    mv "$tmp_file" "$pipe_file" 2>/dev/null || \
    rm -f "$tmp_file" 2>/dev/null

  return 0
}

# ─── hook_read ────────────────────────────────────────────────────────────────
# Read a value emitted by a prior hook in the same event chain.
#
# Usage: hook_read <key> [default] [event_override]
#
# Returns the stored value via stdout, or the default if not found.
# Returns exit code 0 if found, 1 if not found (default returned regardless).

hook_read() {
  local key="$1"
  local default="${2:-}"
  local event="${3:-${CLAUDE_HOOK_EVENT:-unknown}}"

  local pipe_file="$_HOOK_PIPE_DIR/${event}-${key}.val"

  if [ -f "$pipe_file" ]; then
    cat "$pipe_file" 2>/dev/null
    return 0
  else
    echo "$default"
    return 1
  fi
}

# ─── hook_pipe_clear ─────────────────────────────────────────────────────────
# Clear all pipe values for a specific event (or all events).
#
# Usage:
#   hook_pipe_clear                    # clear all events
#   hook_pipe_clear "PreToolUse"       # clear only PreToolUse pipe values

hook_pipe_clear() {
  local event="${1:-}"

  if [ -d "$_HOOK_PIPE_DIR" ]; then
    if [ -n "$event" ]; then
      rm -f "$_HOOK_PIPE_DIR/${event}-"*.val 2>/dev/null || true
    else
      rm -f "$_HOOK_PIPE_DIR/"*.val 2>/dev/null || true
    fi
  fi
}
