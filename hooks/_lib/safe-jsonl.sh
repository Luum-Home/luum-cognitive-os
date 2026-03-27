#!/usr/bin/env bash
# safe-jsonl.sh — Shared library for safe JSONL writes with flock + hook health heartbeats
# Part of: auto-repair-system (ARS-1-01)
#
# Usage: source this file at the top of any hook that writes JSONL.
#   source "$(dirname "$0")/_lib/safe-jsonl.sh"
#
# Provides:
#   safe_jsonl_append <file> <json_line>   — flock-protected append
#   _resolve_metrics_dir                    — returns session-aware metrics path
#   _emit_heartbeat                         — writes hook health entry (auto on EXIT)

set -uo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────

_FLOCK_TIMEOUT="${COGNITIVE_OS_FLOCK_TIMEOUT:-5}"        # seconds to wait for lock
_HEARTBEAT_ENABLED="${COGNITIVE_OS_HOOK_HEARTBEAT:-true}" # set false to disable
_HOOK_NAME="${_HOOK_NAME:-$(basename "${BASH_SOURCE[1]:-unknown}" .sh)}"
_HOOK_START_EPOCH=$(date +%s)
_HOOK_EXIT_CODE=0

# ─── Metrics directory resolution ────────────────────────────────────────────

_resolve_metrics_dir() {
  local project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local metrics_dir="$project_dir/.cognitive-os/metrics"
  local session_id="${COGNITIVE_OS_SESSION_ID:-}"

  if [ -z "$session_id" ]; then
    local session_file="$project_dir/.cognitive-os/sessions/.current-session-$$"
    [ -f "$session_file" ] && session_id=$(cat "$session_file" 2>/dev/null)
  fi

  if [ -n "$session_id" ] && [ -d "$project_dir/.cognitive-os/sessions/$session_id" ]; then
    local session_metrics="$project_dir/.cognitive-os/sessions/$session_id/metrics"
    mkdir -p "$session_metrics" 2>/dev/null
    echo "$session_metrics"
  else
    mkdir -p "$metrics_dir" 2>/dev/null
    echo "$metrics_dir"
  fi
}

# ─── Safe JSONL append with flock ────────────────────────────────────────────

safe_jsonl_append() {
  local target_file="$1"
  local json_line="$2"

  # Validate JSON before writing (fail fast on malformed data)
  if command -v jq >/dev/null 2>&1; then
    if ! echo "$json_line" | jq -e . >/dev/null 2>&1; then
      echo "[safe-jsonl] WARNING: Invalid JSON from $_HOOK_NAME, skipping write" >&2
      return 1
    fi
  fi

  # Ensure parent directory exists
  local parent_dir
  parent_dir=$(dirname "$target_file")
  mkdir -p "$parent_dir" 2>/dev/null

  # Lock file: same path with .lock suffix in a locks subdir
  local lock_dir="$parent_dir/.locks"
  mkdir -p "$lock_dir" 2>/dev/null
  local lock_file="$lock_dir/$(basename "$target_file").lock"

  # Atomic append under lock
  # mkdir-based lock is portable across macOS and Linux (no flock dependency)
  {
    local retries=0
    local max_retries=$(( _FLOCK_TIMEOUT * 10 ))
    while ! mkdir "$lock_file.d" 2>/dev/null; do
      retries=$((retries + 1))
      if [ "$retries" -ge "$max_retries" ]; then
        echo "[safe-jsonl] WARNING: lock timeout after ${_FLOCK_TIMEOUT}s for $target_file" >&2
        # Force-remove stale lock if older than 30s
        if [ -d "$lock_file.d" ]; then
          local lock_age
          lock_age=$(( $(date +%s) - $(stat -f %m "$lock_file.d" 2>/dev/null || stat -c %Y "$lock_file.d" 2>/dev/null || echo 0) ))
          if [ "$lock_age" -gt 30 ]; then
            rmdir "$lock_file.d" 2>/dev/null
            continue
          fi
        fi
        return 1
      fi
      sleep 0.1
    done
    echo "$json_line" >> "$target_file"
    rmdir "$lock_file.d" 2>/dev/null
  }
}

# ─── Hook health heartbeat ──────────────────────────────────────────────────

_emit_heartbeat() {
  [ "$_HEARTBEAT_ENABLED" = "true" ] || return 0

  local project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local health_file="$project_dir/.cognitive-os/metrics/hook-health.jsonl"
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local duration_ms=$(( ($(date +%s) - _HOOK_START_EPOCH) * 1000 ))

  local entry
  if command -v jq >/dev/null 2>&1; then
    entry=$(jq -c -n \
      --arg hook "$_HOOK_NAME" \
      --arg ts "$now" \
      --argjson exit_code "$_HOOK_EXIT_CODE" \
      --argjson duration_ms "$duration_ms" \
      '{timestamp: $ts, hook: $hook, exit_code: $exit_code, duration_ms: $duration_ms}')
  else
    entry="{\"timestamp\":\"$now\",\"hook\":\"$_HOOK_NAME\",\"exit_code\":$_HOOK_EXIT_CODE,\"duration_ms\":$duration_ms}"
  fi

  # Write heartbeat directly (avoid recursive lock if safe_jsonl_append has issues)
  mkdir -p "$(dirname "$health_file")" 2>/dev/null
  echo "$entry" >> "$health_file" 2>/dev/null
}

# ─── Auto-heartbeat on EXIT ─────────────────────────────────────────────────

_on_hook_exit() {
  _HOOK_EXIT_CODE=$?
  _emit_heartbeat
}

# Only install trap if we're being sourced by a hook (not by another lib)
if [ "${_SAFE_JSONL_LOADED:-}" != "true" ]; then
  _SAFE_JSONL_LOADED="true"
  trap _on_hook_exit EXIT
fi
