#!/usr/bin/env bash
# SCOPE: os-only
# safe-jsonl.sh — Shared library for safe JSONL writes + hook health heartbeats
#
# PERFORMANCE CONTRACT:
#   - Source time: 0 subprocesses (uses caller's cached vars)
#   - safe_jsonl_append: 0 subprocesses (no jq validation — caller's responsibility)
#   - _emit_heartbeat: 1 subprocess (date) — down from 5 (git, date x2, jq, mkdir)
#   - Total overhead per hook: <50ms (was 1-3 seconds)
#
# PLATFORM: bash 3.2+ (macOS default). No bash 4/5 features.
#
# Usage: source "$(dirname "$0")/_lib/safe-jsonl.sh"
#
# Provides:
#   safe_jsonl_append <file> <json_line>   — append with mkdir-based lock
#   _emit_heartbeat                         — writes hook health (auto on EXIT)

set -uo pipefail

# ─── Portable helpers ─────────────────────────────────────────────────────────
# Source portable.sh if not already loaded (safe-jsonl is itself in _lib/).
if [ "${_PORTABLE_SH_LOADED:-}" != "true" ]; then
  _SAFE_JSONL_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  source "${_SAFE_JSONL_LIB_DIR}/portable.sh"
fi

# ─── Configuration (0 subprocesses) ──────────────────────────────────────────

_FLOCK_TIMEOUT="${COGNITIVE_OS_FLOCK_TIMEOUT:-5}"
_HEARTBEAT_ENABLED="${COGNITIVE_OS_HOOK_HEARTBEAT:-true}"
_HOOK_NAME="${_HOOK_NAME:-$(basename "${BASH_SOURCE[1]:-unknown}" .sh)}"
_HOOK_EXIT_CODE=0

# Cache project dir once at source time. Priority: env var > CLAUDE_PROJECT_DIR > cwd
# git rev-parse only runs if no env var is set (rare in hook context)
_SAFE_JSONL_PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
_SAFE_JSONL_METRICS_DIR="$_SAFE_JSONL_PROJECT_DIR/.cognitive-os/metrics"

# Single date call at source time — reused by heartbeat for duration calc
_HOOK_START_EPOCH=$(date +%s)

# Ensure metrics dir exists once (not on every heartbeat)
[ -d "$_SAFE_JSONL_METRICS_DIR" ] || mkdir -p "$_SAFE_JSONL_METRICS_DIR" 2>/dev/null

# ─── Safe JSONL append ───────────────────────────────────────────────────────
# No jq validation — callers construct JSON, callers own correctness.
# Spawning jq to validate 1 line costs more than the line is worth.

safe_jsonl_append() {
  local target_file="$1"
  local json_line="$2"
  local parent_dir="${target_file%/*}"

  # Ensure parent dir exists (cheap stat check before mkdir)
  [ -d "$parent_dir" ] || mkdir -p "$parent_dir" 2>/dev/null

  # mkdir-based lock (portable macOS + Linux, no flock dependency)
  local lock_dir="$parent_dir/.locks"
  [ -d "$lock_dir" ] || mkdir -p "$lock_dir" 2>/dev/null
  local lock_path="$lock_dir/${target_file##*/}.lock.d"

  local retries=0
  local max_retries=$(( _FLOCK_TIMEOUT * 10 ))
  while ! mkdir "$lock_path" 2>/dev/null; do
    retries=$((retries + 1))
    if [ "$retries" -ge "$max_retries" ]; then
      # Force-remove stale lock (>30s old)
      if [ -d "$lock_path" ]; then
        local lock_age=$(( $(date +%s) - $(portable_stat_mtime "$lock_path" 2>/dev/null || echo 0) ))
        [ "$lock_age" -gt 30 ] && rmdir "$lock_path" 2>/dev/null && continue
      fi
      return 1
    fi
    sleep 0.1
  done

  echo "$json_line" >> "$target_file"
  rmdir "$lock_path" 2>/dev/null
}

# ─── Metrics directory (cached, 0 subprocesses) ─────────────────────────────

_resolve_metrics_dir() {
  echo "$_SAFE_JSONL_METRICS_DIR"
}

# ─── Hook health heartbeat (1 subprocess: date) ─────────────────────────────

_emit_heartbeat() {
  [ "$_HEARTBEAT_ENABLED" = "true" ] || return 0

  local now_epoch
  now_epoch=$(date +%s)
  local duration_ms=$(( (now_epoch - _HOOK_START_EPOCH) * 1000 ))
  # ISO timestamp from epoch — macOS date uses -r, GNU uses -d @
  local ts
  ts=$(date -u -r "$now_epoch" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "@$now_epoch" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)

  echo "{\"timestamp\":\"$ts\",\"hook\":\"$_HOOK_NAME\",\"exit_code\":$_HOOK_EXIT_CODE,\"duration_ms\":$duration_ms}" >> "$_SAFE_JSONL_METRICS_DIR/hook-health.jsonl" 2>/dev/null
}

# ─── Auto-heartbeat on EXIT ─────────────────────────────────────────────────

_on_hook_exit() {
  _HOOK_EXIT_CODE=$?
  _emit_heartbeat
}

if [ "${_SAFE_JSONL_LOADED:-}" != "true" ]; then
  _SAFE_JSONL_LOADED="true"
  trap _on_hook_exit EXIT
fi
