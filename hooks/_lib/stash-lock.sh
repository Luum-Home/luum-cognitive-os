#!/usr/bin/env bash
# SCOPE: both
# stash-lock.sh — Flock coordinator library for git stash operations.
#
# PROBLEM: Multiple OS hooks (auto-checkpoint, pre-agent-snapshot,
# post-agent-snapshot-restore) touch git stash concurrently. Even with named
# stashes (R2 fix), there is a window where two hooks mutate the stash list
# simultaneously, producing torn state.
#
# SOLUTION: Exclusive advisory lock on .cognitive-os/runtime/stash.lock.
# All stash-mutating hooks MUST acquire this lock before touching git stash.
#
# FUTURE CONSUMER WIRING (R3-Phase2 — do NOT wire in this batch):
#   - hooks/auto-checkpoint.sh
#   - hooks/pre-agent-snapshot.sh
#   - hooks/post-agent-snapshot-restore.sh
#
# LOCK STRATEGY:
#   1. flock(1) — preferred; uses kernel advisory lock fd; available on Linux
#      and via Homebrew on macOS. Detected via `command -v flock`.
#   2. mkdir-based CAS lock — portable fallback; mkdir is atomic on POSIX;
#      PID written inside so staleness can be detected.
#
# LOCK FILE: .cognitive-os/runtime/stash.lock
# FORMAT (JSON): {"pid": <int>, "hook_name": "<str>", "acquired_at_epoch": <int>}
#
# ENVIRONMENT OVERRIDES:
#   COS_STASH_LOCK_TIMEOUT   — seconds to wait for lock (default 10)
#   COS_STASH_LOCK_STALE_AGE — seconds before a lock is considered stale (default 30)
#   COS_DISABLE_STASH_LOCK=1 — bypass all locking (emergency only)
#
# Guard: only load once
[ "${_STASH_LOCK_SH_LOADED:-}" = "true" ] && return 0
_STASH_LOCK_SH_LOADED="true"

# ─── Internal paths ──────────────────────────────────────────────────────────

_stash_lock_project_dir() {
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    echo "$COGNITIVE_OS_PROJECT_DIR"
  elif [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    echo "$CODEX_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    echo "$CLAUDE_PROJECT_DIR"
  else
    git rev-parse --show-toplevel 2>/dev/null || pwd
  fi
}

_stash_lock_file() {
  local project_dir
  project_dir="$(_stash_lock_project_dir)"
  mkdir -p "$project_dir/.cognitive-os/runtime" 2>/dev/null || true
  echo "$project_dir/.cognitive-os/runtime/stash.lock"
}

# ─── Internal: write lock metadata ──────────────────────────────────────────

_stash_lock_write_meta() {
  local lock_file="$1"
  local hook_name="$2"
  local pid="$$"
  local epoch
  epoch=$(date +%s)
  printf '{"pid":%s,"hook_name":"%s","acquired_at_epoch":%s}\n' \
    "$pid" "$hook_name" "$epoch" > "$lock_file"
}

# ─── Internal: is PID alive? ────────────────────────────────────────────────

_stash_lock_pid_alive() {
  local pid="$1"
  [ "$pid" -le 0 ] 2>/dev/null && return 1
  kill -0 "$pid" 2>/dev/null
}

# ─── Internal: check for stale lock ─────────────────────────────────────────
# Returns 0 (is stale) or 1 (still valid).

_stash_lock_is_stale() {
  local lock_file="$1"
  local stale_age="${COS_STASH_LOCK_STALE_AGE:-30}"
  [ -f "$lock_file" ] || return 0  # missing = treat as stale

  local pid=0
  local acquired_at=0

  if command -v python3 >/dev/null 2>&1; then
    read -r pid acquired_at < <(python3 - "$lock_file" <<'PY'
import json, sys
from pathlib import Path
try:
    d = json.loads(Path(sys.argv[1]).read_text())
    print(d.get("pid", 0), d.get("acquired_at_epoch", 0))
except Exception:
    print(0, 0)
PY
)
  else
    # Minimal fallback: grep numeric fields
    pid=$(grep -o '"pid":[0-9]*' "$lock_file" 2>/dev/null | grep -o '[0-9]*$' || echo 0)
    acquired_at=$(grep -o '"acquired_at_epoch":[0-9]*' "$lock_file" 2>/dev/null | grep -o '[0-9]*$' || echo 0)
  fi

  local now
  now=$(date +%s)

  # Stale if PID is dead
  if ! _stash_lock_pid_alive "$pid"; then
    return 0
  fi

  # Stale if lock is older than stale_age
  if [ "$acquired_at" -gt 0 ] 2>/dev/null; then
    local age=$(( now - acquired_at ))
    if [ "$age" -gt "$stale_age" ]; then
      return 0
    fi
  fi

  return 1
}

# ─── Internal: mkdir-based CAS acquire (one attempt) ────────────────────────
# Returns 0 on success, 1 on failure (lock already held).

_stash_lock_mkdir_try() {
  local lock_dir="$1"
  local hook_name="$2"
  if mkdir "$lock_dir" 2>/dev/null; then
    _stash_lock_write_meta "$lock_dir/meta" "$hook_name"
    return 0
  fi
  return 1
}

# ─── Internal: flock-based acquire (with timeout) ───────────────────────────
# Uses a dedicated fd stored in _STASH_LOCK_FD. Caller must close on release.

_STASH_LOCK_FD=""
_STASH_LOCK_FLOCK_FILE=""

_stash_lock_flock_acquire() {
  local lock_file="$1"
  local hook_name="$2"
  local timeout="${COS_STASH_LOCK_TIMEOUT:-10}"

  # Open a dedicated fd for flock
  local fd=200
  # Try to open fd; increment if already open
  while { true >&"$fd"; } 2>/dev/null; do
    (( fd++ ))
    [ "$fd" -gt 250 ] && return 1
  done

  # Open the lock file on the chosen fd
  eval "exec $fd>\"$lock_file\"" 2>/dev/null || return 1

  if flock --timeout "$timeout" "$fd" 2>/dev/null; then
    _stash_lock_write_meta "$lock_file" "$hook_name"
    _STASH_LOCK_FD="$fd"
    _STASH_LOCK_FLOCK_FILE="$lock_file"
    return 0
  fi

  eval "exec $fd>&-" 2>/dev/null || true
  return 1
}

_stash_lock_flock_release() {
  if [ -n "${_STASH_LOCK_FD:-}" ]; then
    local fd="$_STASH_LOCK_FD"
    flock -u "$fd" 2>/dev/null || true
    eval "exec $fd>&-" 2>/dev/null || true
    _STASH_LOCK_FD=""
    # Remove lock file content so status shows clean
    [ -f "${_STASH_LOCK_FLOCK_FILE:-}" ] && rm -f "$_STASH_LOCK_FLOCK_FILE" 2>/dev/null || true
    _STASH_LOCK_FLOCK_FILE=""
  fi
}

# ─── Internal state for mkdir fallback ──────────────────────────────────────

_STASH_LOCK_DIR=""
_STASH_LOCK_USE_FLOCK=0

# ─── Public: cos_stash_lock_acquire ─────────────────────────────────────────
# Usage: cos_stash_lock_acquire <hook_name>
#
# Acquires exclusive lock. Prints warning to stderr and exits non-zero on
# timeout. On stale lock, auto-cleans and retries once.
#
# Sets internal state used by cos_stash_lock_release.

cos_stash_lock_acquire() {
  local hook_name="${1:-unknown}"
  local timeout="${COS_STASH_LOCK_TIMEOUT:-10}"

  if [ "${COS_DISABLE_STASH_LOCK:-0}" = "1" ]; then
    return 0
  fi

  local lock_file
  lock_file="$(_stash_lock_file)"
  local lock_dir="${lock_file}.d"

  # ── Strategy selection ────────────────────────────────────────────────────
  if command -v flock >/dev/null 2>&1; then
    _STASH_LOCK_USE_FLOCK=1

    # Check for stale lock file before trying flock
    if [ -f "$lock_file" ] && _stash_lock_is_stale "$lock_file"; then
      echo "[stash-lock] stale lock detected, cleaning up: $lock_file" >&2
      rm -f "$lock_file" 2>/dev/null || true
    fi

    if _stash_lock_flock_acquire "$lock_file" "$hook_name"; then
      return 0
    fi

    echo "[stash-lock] WARN: could not acquire stash lock within ${timeout}s (hook=$hook_name)" >&2
    return 1

  else
    # mkdir-based fallback
    _STASH_LOCK_USE_FLOCK=0
    local deadline=$(( $(date +%s) + timeout ))
    local acquired=0
    local retried=0

    while true; do
      if _stash_lock_mkdir_try "$lock_dir" "$hook_name"; then
        _STASH_LOCK_DIR="$lock_dir"
        _stash_lock_write_meta "$lock_file" "$hook_name"
        acquired=1
        break
      fi

      # Check for stale lock (dead PID or old age)
      local meta_file="$lock_dir/meta"
      if [ -f "$meta_file" ] && _stash_lock_is_stale "$meta_file" && [ "$retried" -eq 0 ]; then
        echo "[stash-lock] stale mkdir lock detected, cleaning up: $lock_dir" >&2
        rm -rf "$lock_dir" 2>/dev/null || true
        retried=1
        continue
      fi

      local now
      now=$(date +%s)
      if [ "$now" -ge "$deadline" ]; then
        echo "[stash-lock] WARN: could not acquire stash lock within ${timeout}s (hook=$hook_name)" >&2
        return 1
      fi

      sleep 0.2
    done

    return $(( 1 - acquired ))
  fi
}

# ─── Public: cos_stash_lock_release ─────────────────────────────────────────
# Releases the lock held by this process. Safe to call even if bypass is active.

cos_stash_lock_release() {
  if [ "${COS_DISABLE_STASH_LOCK:-0}" = "1" ]; then
    return 0
  fi

  if [ "${_STASH_LOCK_USE_FLOCK:-0}" = "1" ]; then
    _stash_lock_flock_release
  else
    if [ -n "${_STASH_LOCK_DIR:-}" ]; then
      local lock_file
      lock_file="$(_stash_lock_file)"
      rm -rf "$_STASH_LOCK_DIR" 2>/dev/null || true
      rm -f "$lock_file" 2>/dev/null || true
      _STASH_LOCK_DIR=""
    fi
  fi
}

# ─── Public: cos_stash_lock_with ────────────────────────────────────────────
# Usage: cos_stash_lock_with <hook_name> <command> [args...]
#
# Acquires lock, runs <command> [args...], releases lock on EXIT/INT/TERM.
# If lock acquisition fails, exits non-zero without running the command.

cos_stash_lock_with() {
  local hook_name="${1:-unknown}"
  shift

  cos_stash_lock_acquire "$hook_name" || return $?

  # Ensure release on any exit
  trap 'cos_stash_lock_release' EXIT INT TERM

  local rc=0
  "$@" || rc=$?

  cos_stash_lock_release
  # Restore default trap
  trap - EXIT INT TERM

  return "$rc"
}

# ─── Public: cos_stash_lock_status ──────────────────────────────────────────
# Diagnostic for `cos validation status`-style introspection.
# Prints structured info to stdout.

cos_stash_lock_status() {
  local lock_file
  lock_file="$(_stash_lock_file)"
  local lock_dir="${lock_file}.d"

  echo "stash-lock-file=$lock_file"
  echo "flock-available=$(command -v flock >/dev/null 2>&1 && echo yes || echo no)"
  echo "bypass-active=$([ "${COS_DISABLE_STASH_LOCK:-0}" = "1" ] && echo yes || echo no)"
  echo "timeout=${COS_STASH_LOCK_TIMEOUT:-10}s"
  echo "stale-age=${COS_STASH_LOCK_STALE_AGE:-30}s"

  # Check flock lock file
  if [ -f "$lock_file" ]; then
    echo "flock-lock=present"
    if command -v python3 >/dev/null 2>&1; then
      python3 - "$lock_file" <<'PY'
import json, os, sys, time
from pathlib import Path
try:
    d = json.loads(Path(sys.argv[1]).read_text())
    pid = d.get("pid", 0)
    hook = d.get("hook_name", "?")
    epoch = d.get("acquired_at_epoch", 0)
    age = int(time.time()) - int(epoch) if epoch else -1
    alive = "yes"
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        alive = "no (dead)"
    except PermissionError:
        alive = "yes (permission denied to signal)"
    print(f"flock-lock-pid={pid} alive={alive} hook={hook} age={age}s")
except Exception as e:
    print(f"flock-lock=corrupt ({e})")
PY
    else
      echo "flock-lock-meta=cannot parse (python3 missing)"
    fi
  else
    echo "flock-lock=absent"
  fi

  # Check mkdir lock dir
  if [ -d "$lock_dir" ]; then
    echo "mkdir-lock=present"
    local meta="$lock_dir/meta"
    if [ -f "$meta" ]; then
      echo "mkdir-lock-meta=$(cat "$meta" 2>/dev/null || echo unreadable)"
    fi
  else
    echo "mkdir-lock=absent"
  fi
}
