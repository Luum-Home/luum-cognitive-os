#!/usr/bin/env bash
# edit-coop.sh — ADR-098 Layer 4: file-level edit coordination
#
# Builds on ADR-089 Layer 2 primitives (git-coop.sh atomic mkdir + PID-based
# stale detection) but locks a SPECIFIC FILE rather than the git index.
#
# USAGE (standalone):
#   scripts/edit-coop.sh acquire <file-path> [--purpose "..."] [--intent exclusive-edit|shared-read|append-only]
#   scripts/edit-coop.sh release <file-path>
#   scripts/edit-coop.sh check <file-path>           # exit 0 if lockable, 2 if held by other
#   scripts/edit-coop.sh status                      # print all active locks as JSON
#   scripts/edit-coop.sh heartbeat <file-path>       # refresh own lock TTL
#   scripts/edit-coop.sh release-mine                # release every lock owned by this session
#
# LOCK LOCATION:
#   .cognitive-os/runtime/edit-locks/<safe-path>/         (POSIX-atomic mkdir)
#   .cognitive-os/runtime/edit-locks/<safe-path>/meta.yaml (rich data — see schema)
#
# RICH SCHEMA (so other agents can introspect and respond):
#   session_id, agent_id, agent_role, worktree
#   target_file, intent, since, heartbeat, expires_at
#   purpose, related_adr, related_files
#   allows_concurrent_read, allows_concurrent_edit_below_line
#   on_conflict_other_agent_should   (park | retry | negotiate | escalate)
#   status (active | parking | released | stale)
#
# STALE DETECTION (same rule as git-coop.sh):
#   - timestamp older than COS_EDIT_LOCK_TTL (default 1800s = 30min), OR
#   - PID is not running on this machine
#
# IDEMPOTENT:
#   Re-acquiring own lock refreshes heartbeat + expires_at, succeeds.
#
# ESCAPE HATCH:
#   COS_BYPASS_EDIT_LOCK=1 — skip all locks (emergency only; logged to history).
#
# POSIX / macOS compatible.
set -uo pipefail

LOCK_TTL_SECONDS="${COS_EDIT_LOCK_TTL:-1800}"      # 30 minutes
LOCK_HEARTBEAT_SECONDS="${COS_EDIT_LOCK_HEARTBEAT:-300}"  # refresh every 5min

# ── Path resolution ─────────────────────────────────────────────────────────

_resolve_project_dir() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s' "$CLAUDE_PROJECT_DIR"
    return
  fi
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    printf '%s' "$COGNITIVE_OS_PROJECT_DIR"
    return
  fi
  local dir
  dir="$(pwd)"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/cognitive-os.yaml" ] || [ -d "$dir/.claude" ]; then
      printf '%s' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  printf '%s' "$(pwd)"
}

_locks_root() {
  printf '%s/.cognitive-os/runtime/edit-locks' "$(_resolve_project_dir)"
}

# Convert "tests/conftest.py" → "tests--conftest.py" (filesystem-safe key).
_safe_path() {
  printf '%s' "$1" | sed 's|/|--|g; s|\.\.||g'
}

_lock_dir_for() {
  printf '%s/%s' "$(_locks_root)" "$(_safe_path "$1")"
}

_meta_file_for() {
  printf '%s/meta.yaml' "$(_lock_dir_for "$1")"
}

# ── Identity ────────────────────────────────────────────────────────────────

_session_id() {
  if [ -n "${COGNITIVE_OS_SESSION_ID:-}" ]; then printf '%s' "$COGNITIVE_OS_SESSION_ID"; return; fi
  if [ -n "${CODEX_SESSION_ID:-}" ]; then printf '%s' "$CODEX_SESSION_ID"; return; fi
  if [ -n "${CLAUDE_SESSION_ID:-}" ]; then printf '%s' "$CLAUDE_SESSION_ID"; return; fi
  printf 'shell-%s' "${PPID:-$$}"
}

_agent_id() {
  printf '%s' "${COS_AGENT_ID:-${CLAUDE_AGENT_ID:-unknown-agent}}"
}

_agent_role() {
  printf '%s' "${COS_AGENT_ROLE:-orchestrator}"
}

_worktree() {
  git -C "$(_resolve_project_dir)" rev-parse --show-toplevel 2>/dev/null \
    || _resolve_project_dir
}

_iso8601() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

_iso8601_plus() {
  # Add N seconds to current UTC time. POSIX-portable.
  local seconds="$1"
  local now_epoch
  now_epoch=$(date -u +%s)
  local target=$(( now_epoch + seconds ))
  date -u -r "$target" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
    || date -u -d "@$target" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
    || _iso8601
}

_pid_alive() {
  kill -0 "$1" 2>/dev/null
}

# ── Stale detection ─────────────────────────────────────────────────────────

_lock_is_stale() {
  local file_path="$1"
  local meta_file
  meta_file="$(_meta_file_for "$file_path")"
  [ -f "$meta_file" ] || return 0

  local pid timestamp_raw
  pid=$(sed -n 's/^pid: *\([0-9]*\)$/\1/p' "$meta_file" | head -1)
  timestamp_raw=$(sed -n 's/^heartbeat: *"\(.*\)"$/\1/p' "$meta_file" | head -1)
  [ -z "$timestamp_raw" ] && timestamp_raw=$(sed -n 's/^since: *"\(.*\)"$/\1/p' "$meta_file" | head -1)

  [ -z "$pid" ] && return 0
  # Skip PID liveness when explicitly disabled (used by unit tests where each
  # bash invocation is a fresh subprocess that exits immediately, making every
  # lock look stale by PID). Production keeps the check.
  if [ "${COS_EDIT_LOCK_NO_PID_CHECK:-}" != "1" ]; then
    _pid_alive "$pid" || return 0
  fi
  [ -z "$timestamp_raw" ] && return 0

  local now lock_time
  now=$(date -u +%s)
  lock_time=$(date -d "$timestamp_raw" +%s 2>/dev/null) \
    || lock_time=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$timestamp_raw" +%s 2>/dev/null) \
    || return 0
  local age=$(( now - lock_time ))
  [ "$age" -gt "$LOCK_TTL_SECONDS" ] && return 0
  return 1
}

# ── Lock metadata read helpers (for introspection by sub-agents) ────────────

_read_field() {
  local file="$1" field="$2"
  sed -n "s/^${field}: *\"\\(.*\\)\"\$/\\1/p" "$file" | head -1
}

# Returns the session_id holding the lock, or empty string.
_lock_holder() {
  local meta_file
  meta_file="$(_meta_file_for "$1")"
  [ -f "$meta_file" ] || { printf ''; return; }
  _read_field "$meta_file" "session_id"
}

# ── Public commands ─────────────────────────────────────────────────────────

cmd_acquire() {
  if [ "${COS_BYPASS_EDIT_LOCK:-}" = "1" ]; then
    echo "[edit-coop] BYPASS: COS_BYPASS_EDIT_LOCK=1, no lock taken on $1" >&2
    return 0
  fi

  local file_path="$1" purpose="${2:-unspecified}" intent="${3:-exclusive-edit}"
  local lock_dir meta_file
  lock_dir="$(_lock_dir_for "$file_path")"
  meta_file="$(_meta_file_for "$file_path")"

  mkdir -p "$(_locks_root)"

  # Stale auto-clear before attempting acquire.
  if [ -d "$lock_dir" ] && _lock_is_stale "$file_path"; then
    echo "[edit-coop] auto-clearing stale lock on $file_path" >&2
    rm -rf "$lock_dir"
  fi

  # Atomic acquire via mkdir.
  if mkdir "$lock_dir" 2>/dev/null; then
    _write_meta "$file_path" "$purpose" "$intent" "active"
    echo "[edit-coop] acquired $file_path (intent=$intent)" >&2
    return 0
  fi

  # Already exists. Check if it's ours.
  if [ -f "$meta_file" ]; then
    local holder
    holder="$(_lock_holder "$file_path")"
    if [ "$holder" = "$(_session_id)" ]; then
      _write_meta "$file_path" "$purpose" "$intent" "active"
      echo "[edit-coop] re-acquired (own lock) $file_path" >&2
      return 0
    fi
    # Held by other session.
    echo "[edit-coop] BLOCKED — $file_path held by session=$holder" >&2
    return 2
  fi
  return 2
}

_write_meta() {
  local file_path="$1" purpose="$2" intent="$3" status="$4"
  local meta_file
  meta_file="$(_meta_file_for "$file_path")"
  cat > "$meta_file" <<EOF
session_id: "$(_session_id)"
agent_id: "$(_agent_id)"
agent_role: "$(_agent_role)"
worktree: "$(_worktree)"
pid: $$
target_file: "$file_path"
intent: "$intent"
since: "$(_iso8601)"
heartbeat: "$(_iso8601)"
expires_at: "$(_iso8601_plus "$LOCK_TTL_SECONDS")"
purpose: "$purpose"
related_adr: "${COS_RELATED_ADR:-}"
related_files: []
allows_concurrent_read: true
on_conflict_other_agent_should: "park"
status: "$status"
EOF
}

cmd_release() {
  local file_path="$1"
  local lock_dir meta_file
  lock_dir="$(_lock_dir_for "$file_path")"
  meta_file="$(_meta_file_for "$file_path")"

  [ -d "$lock_dir" ] || { echo "[edit-coop] no lock on $file_path" >&2; return 0; }

  local holder
  holder="$(_lock_holder "$file_path")"
  if [ -n "$holder" ] && [ "$holder" != "$(_session_id)" ]; then
    echo "[edit-coop] refusing to release $file_path — held by $holder, not us" >&2
    return 2
  fi
  rm -rf "$lock_dir"
  echo "[edit-coop] released $file_path" >&2
}

cmd_check() {
  local file_path="$1"
  local lock_dir
  lock_dir="$(_lock_dir_for "$file_path")"

  if [ ! -d "$lock_dir" ]; then
    echo "[edit-coop] FREE — no lock on $file_path"
    return 0
  fi
  if _lock_is_stale "$file_path"; then
    echo "[edit-coop] STALE — lock on $file_path is stale, will be auto-cleared on next acquire"
    return 0
  fi
  local holder
  holder="$(_lock_holder "$file_path")"
  if [ "$holder" = "$(_session_id)" ]; then
    echo "[edit-coop] OWN — you hold the lock on $file_path"
    return 0
  fi
  echo "[edit-coop] HELD — $file_path locked by session=$holder"
  cat "$(_meta_file_for "$file_path")" 2>/dev/null
  return 2
}

cmd_status() {
  local locks_root
  locks_root="$(_locks_root)"
  [ -d "$locks_root" ] || { echo "{}"; return 0; }

  printf '{"locks":['
  local first=1
  for d in "$locks_root"/*/; do
    [ -d "$d" ] || continue
    local meta="$d/meta.yaml"
    [ -f "$meta" ] || continue
    [ "$first" -eq 1 ] || printf ','
    first=0
    printf '\n  {'
    printf '"target":"%s","session":"%s","agent":"%s","intent":"%s","since":"%s","heartbeat":"%s","purpose":"%s","status":"%s"' \
      "$(_read_field "$meta" target_file)" \
      "$(_read_field "$meta" session_id)" \
      "$(_read_field "$meta" agent_id)" \
      "$(_read_field "$meta" intent)" \
      "$(_read_field "$meta" since)" \
      "$(_read_field "$meta" heartbeat)" \
      "$(_read_field "$meta" purpose)" \
      "$(_read_field "$meta" status)"
    printf '}'
  done
  printf '\n]}\n'
}

cmd_heartbeat() {
  local file_path="$1"
  local meta_file
  meta_file="$(_meta_file_for "$file_path")"
  [ -f "$meta_file" ] || { echo "[edit-coop] no lock to heartbeat on $file_path" >&2; return 1; }
  local holder
  holder="$(_lock_holder "$file_path")"
  [ "$holder" = "$(_session_id)" ] || { echo "[edit-coop] cannot heartbeat — not owner" >&2; return 2; }

  # Refresh heartbeat + expires_at lines in place.
  local now expires
  now="$(_iso8601)"
  expires="$(_iso8601_plus "$LOCK_TTL_SECONDS")"
  local tmp="$meta_file.tmp"
  awk -v now="$now" -v expires="$expires" '
    /^heartbeat: / { print "heartbeat: \"" now "\""; next }
    /^expires_at: / { print "expires_at: \"" expires "\""; next }
    { print }
  ' "$meta_file" > "$tmp" && mv "$tmp" "$meta_file"
  echo "[edit-coop] heartbeat refreshed on $file_path" >&2
}

cmd_release_mine() {
  local locks_root
  locks_root="$(_locks_root)"
  [ -d "$locks_root" ] || return 0
  local me released=0
  me="$(_session_id)"
  for d in "$locks_root"/*/; do
    [ -d "$d" ] || continue
    local meta="$d/meta.yaml"
    [ -f "$meta" ] || continue
    local holder
    holder="$(_read_field "$meta" session_id)"
    if [ "$holder" = "$me" ]; then
      rm -rf "$d"
      released=$(( released + 1 ))
    fi
  done
  echo "[edit-coop] released $released own lock(s)" >&2
}

# ── Entry point ─────────────────────────────────────────────────────────────

cmd="${1:-}"
shift || true
case "$cmd" in
  acquire)        cmd_acquire "$@" ;;
  release)        cmd_release "$@" ;;
  check)          cmd_check "$@" ;;
  status)         cmd_status ;;
  heartbeat)      cmd_heartbeat "$@" ;;
  release-mine|release_mine) cmd_release_mine ;;
  *)
    cat <<EOF >&2
edit-coop.sh — file-level edit coordination (ADR-098)
Usage:
  edit-coop.sh acquire <file> [purpose] [intent]
  edit-coop.sh release <file>
  edit-coop.sh check <file>          (exit 0 lockable, 2 held)
  edit-coop.sh status                (JSON of all active locks)
  edit-coop.sh heartbeat <file>      (refresh own lock TTL)
  edit-coop.sh release-mine          (release every lock owned by this session)
EOF
    exit 64
    ;;
esac
