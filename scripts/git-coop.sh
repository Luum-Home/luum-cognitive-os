#!/usr/bin/env bash
# git-coop.sh — ADR-089 Layer 2: cooperative session lock for git index operations
#
# Provides atomic acquire/release of a per-project git-index lock so concurrent
# COS sessions serialise staged-index mutations without corrupting each other's
# commit scope.
#
# USAGE (as a standalone command):
#   scripts/git-coop.sh acquire [operation-name]
#   scripts/git-coop.sh release
#   scripts/git-coop.sh force_unlock
#   scripts/git-coop.sh status
#
# USAGE (sourced into another script):
#   source scripts/git-coop.sh
#   cos_git_acquire "git commit --only -- path/to/file"
#   cos_git_release
#
# LOCK FILE:
#   .cognitive-os/runtime/git-index.lock/  (directory — mkdir is POSIX-atomic)
#   .cognitive-os/runtime/git-index.lock/meta.json  (lock metadata)
#
# STALE DETECTION:
#   A lock is stale when:
#     - its timestamp is older than LOCK_TTL_SECONDS (default 300), OR
#     - its PID is not a running process on this machine
#   Stale locks are auto-cleared before retrying.
#
# IDEMPOTENT:
#   A session re-acquiring a lock it already holds succeeds immediately (no-op).
#
# ESCAPE HATCH:
#   COS_BYPASS_GIT_LOCK=1 — skip lock acquisition (emergency use only)
#
# LATENCY TARGET: acquire < 50 ms in the uncontended case
#   (two mkdir calls + one JSON write, no flock dependency)
#
# POSIX / macOS compatible — no flock, no inotify, no bash-4-only features.
#
# shellcheck disable=SC2155

set -uo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────

LOCK_TTL_SECONDS="${COS_GIT_LOCK_TTL:-300}"      # 5 minutes
LOCK_TIMEOUT_SECONDS="${COS_GIT_LOCK_TIMEOUT:-30}" # give up after 30s
LOCK_RETRY_SLEEP=2                                 # seconds between retries

_resolve_project_dir() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s' "$CLAUDE_PROJECT_DIR"
    return
  fi
  # Walk up from cwd to find cognitive-os.yaml or .claude/
  local dir
  dir="$(pwd)"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/cognitive-os.yaml" ] || [ -d "$dir/.claude" ]; then
      printf '%s' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  # Fallback to cwd
  printf '%s' "$(pwd)"
}

_lock_dir() {
  printf '%s/.cognitive-os/runtime/git-index.lock' "$(_resolve_project_dir)"
}

_meta_file() {
  printf '%s/meta.json' "$(_lock_dir)"
}

_session_id() {
  # Use the explicit session env var when available (real COS operation).
  if [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]; then
    printf '%s' "$COGNITIVE_OS_SESSION_ID"
    return
  fi
  if [ -n "${CODEX_SESSION_ID:-}" ]; then
    printf '%s' "$CODEX_SESSION_ID"
    return
  fi
  if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
    printf '%s' "$CLAUDE_SESSION_ID"
    return
  fi
  # Fallback: use PPID (the parent shell that invoked this script) so that
  # acquire and release calls within the same shell session share a stable ID.
  printf 'shell-%s' "${PPID:-$$}"
}

_iso8601() {
  date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ"
}

_pid_alive() {
  local pid="$1"
  # kill -0 checks existence without sending a signal (POSIX-compatible)
  kill -0 "$pid" 2>/dev/null
}

# ── Lock stale check ──────────────────────────────────────────────────────────

# Returns 0 if the lock is stale (should be auto-cleared), 1 if still live.
_lock_is_stale() {
  local lock_dir meta_file timestamp_raw pid now age
  lock_dir="$(_lock_dir)"
  meta_file="$(_meta_file)"

  # No meta → treat as stale directory artifact
  [ -f "$meta_file" ] || return 0

  # Parse PID and timestamp from JSON using sed (no jq dependency)
  pid=$(sed -n 's/.*"pid"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$meta_file" | head -1)
  timestamp_raw=$(sed -n 's/.*"timestamp"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)

  # If PID field is missing/unparseable → stale
  [ -z "$pid" ] && return 0

  # If PID is not running → stale
  _pid_alive "$pid" || return 0

  # If timestamp field is missing → stale
  [ -z "$timestamp_raw" ] && return 0

  # Check age: convert ISO8601 to epoch seconds.
  # 'date -d' works on Linux; macOS needs '-j -f'.
  now=$(date -u +%s 2>/dev/null)
  # macOS: date -j -f "%Y-%m-%dT%H:%M:%SZ" "$timestamp_raw" +%s
  # Linux: date -d "$timestamp_raw" +%s
  # Try Linux form first, then macOS form.
  local lock_time
  lock_time=$(date -d "$timestamp_raw" +%s 2>/dev/null) \
    || lock_time=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$timestamp_raw" +%s 2>/dev/null) \
    || { return 0; }  # unparseable → stale

  age=$(( now - lock_time ))
  [ "$age" -gt "$LOCK_TTL_SECONDS" ] && return 0

  # Lock is live
  return 1
}

# ── Core functions (exported for source usage) ────────────────────────────────

cos_git_acquire() {
  local operation="${1:-git-index-operation}"
  local lock_dir meta_file session pid start elapsed

  # Emergency bypass
  if [ "${COS_BYPASS_GIT_LOCK:-}" = "1" ]; then
    echo "[git-coop] COS_BYPASS_GIT_LOCK=1 — skipping lock acquisition" >&2
    return 0
  fi

  lock_dir="$(_lock_dir)"
  meta_file="$(_meta_file)"
  session="$(_session_id)"
  pid=$$

  # Ensure runtime dir exists
  mkdir -p "$(dirname "$lock_dir")"

  # Idempotency: if we already hold the lock, succeed immediately.
  if [ -d "$lock_dir" ] && [ -f "$meta_file" ]; then
    local holder_session
    holder_session=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
    if [ "$holder_session" = "$session" ]; then
      echo "[git-coop] acquired (already held by this session)" >&2
      return 0
    fi
  fi

  start=$(date -u +%s 2>/dev/null || echo 0)

  while true; do
    # Stale check before attempting acquire (clear stale locks)
    if [ -d "$lock_dir" ] && _lock_is_stale; then
      local stale_holder=""
      [ -f "$meta_file" ] && stale_holder=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
      echo "[git-coop] clearing stale lock (held by session=${stale_holder:-unknown})" >&2
      rm -rf "$lock_dir"
    fi

    # Atomic acquire via mkdir (POSIX: mkdir fails if dir already exists)
    if mkdir "$lock_dir" 2>/dev/null; then
      # We own the directory — write metadata
      cat > "$meta_file" <<EOF
{
  "session_id": "$session",
  "pid": $pid,
  "timestamp": "$(_iso8601)",
  "operation": "$operation"
}
EOF
      echo "[git-coop] acquired (session=$session operation=$operation)" >&2
      return 0
    fi

    # Lock is held by someone else — check timeout
    elapsed=$(( $(date -u +%s 2>/dev/null || echo 0) - start ))
    if [ "$elapsed" -ge "$LOCK_TIMEOUT_SECONDS" ]; then
      local holder_session holder_op
      holder_session="unknown"
      holder_op="unknown"
      if [ -f "$meta_file" ]; then
        holder_session=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
        holder_op=$(sed -n 's/.*"operation"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
      fi
      echo "[git-coop] ERROR: timed out after ${LOCK_TIMEOUT_SECONDS}s waiting for git-index lock" >&2
      echo "[git-coop] lock held by: session=${holder_session} operation=${holder_op}" >&2
      echo "[git-coop] use 'scripts/git-coop.sh force_unlock' to clear manually, or set COS_BYPASS_GIT_LOCK=1" >&2
      return 1
    fi

    # Wait and retry
    echo "[git-coop] lock contention — waiting ${LOCK_RETRY_SLEEP}s (elapsed=${elapsed}s/${LOCK_TIMEOUT_SECONDS}s)" >&2
    sleep "$LOCK_RETRY_SLEEP"
  done
}

cos_git_release() {
  local lock_dir meta_file session holder_session

  if [ "${COS_BYPASS_GIT_LOCK:-}" = "1" ]; then
    return 0
  fi

  lock_dir="$(_lock_dir)"
  meta_file="$(_meta_file)"
  session="$(_session_id)"

  if [ ! -d "$lock_dir" ]; then
    echo "[git-coop] released (lock not held)" >&2
    return 0
  fi

  if [ -f "$meta_file" ]; then
    holder_session=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
    if [ "$holder_session" != "$session" ]; then
      echo "[git-coop] ERROR: refusing to release lock held by session=${holder_session} (caller is session=${session})" >&2
      return 1
    fi
  fi

  rm -rf "$lock_dir"
  echo "[git-coop] released (session=$session)" >&2
  return 0
}

cos_git_force_unlock() {
  local lock_dir
  lock_dir="$(_lock_dir)"
  if [ -d "$lock_dir" ]; then
    local holder_session=""
    local meta_file="$(_meta_file)"
    [ -f "$meta_file" ] && holder_session=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
    rm -rf "$lock_dir"
    echo "[git-coop] force_unlock: removed lock (was held by session=${holder_session:-unknown})" >&2
  else
    echo "[git-coop] force_unlock: no lock present" >&2
  fi
  return 0
}

cos_git_status() {
  local lock_dir meta_file
  lock_dir="$(_lock_dir)"
  meta_file="$(_meta_file)"

  if [ ! -d "$lock_dir" ]; then
    echo "[git-coop] status: UNLOCKED" >&2
    return 0
  fi

  if [ -f "$meta_file" ]; then
    local session op timestamp pid
    session=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
    op=$(sed -n 's/.*"operation"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
    timestamp=$(sed -n 's/.*"timestamp"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$meta_file" | head -1)
    pid=$(sed -n 's/.*"pid"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$meta_file" | head -1)

    local stale_label=""
    _lock_is_stale && stale_label=" [STALE]"

    echo "[git-coop] status: LOCKED${stale_label}" >&2
    echo "[git-coop]   session=${session}" >&2
    echo "[git-coop]   pid=${pid}" >&2
    echo "[git-coop]   timestamp=${timestamp}" >&2
    echo "[git-coop]   operation=${op}" >&2
  else
    echo "[git-coop] status: LOCKED (no metadata)" >&2
  fi
  return 0
}

# ── CLI dispatch (only when run as a script, not sourced) ─────────────────────

# Detect whether we are being sourced or executed.
# When sourced, $0 is the sourcing shell; when executed, $0 is this file.
_GIT_COOP_SOURCED=0
# bash: BASH_SOURCE[0] != $0 when sourced
if [ "${BASH_SOURCE[0]:-}" != "$0" ]; then
  _GIT_COOP_SOURCED=1
fi

if [ "$_GIT_COOP_SOURCED" -eq 0 ]; then
  # Running as a script
  subcmd="${1:-}"
  shift 2>/dev/null || true

  case "$subcmd" in
    acquire)
      cos_git_acquire "${1:-git-index-operation}"
      ;;
    release)
      cos_git_release
      ;;
    force_unlock)
      cos_git_force_unlock
      ;;
    status)
      cos_git_status
      ;;
    *)
      echo "Usage: git-coop.sh <acquire|release|force_unlock|status> [operation-name]" >&2
      echo "" >&2
      echo "  acquire [op]   — acquire git-index lock (blocks up to ${LOCK_TIMEOUT_SECONDS}s)" >&2
      echo "  release        — release lock held by current session" >&2
      echo "  force_unlock   — unconditionally remove lock (emergency use)" >&2
      echo "  status         — show current lock state" >&2
      exit 1
      ;;
  esac
fi
