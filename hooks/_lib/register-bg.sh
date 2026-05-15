#!/usr/bin/env bash
# SCOPE: os-only
# register-bg.sh — ADR-028 D1.B  Process Registry helper
#
# Usage:
#   source "$(dirname "$0")/_lib/register-bg.sh"
#   _register_bg <owner> <ttl_seconds> <kind> <command...>
#
# Runs <command...> in the background, registers the resulting PID with
# lib/process_registry so the reaper can distinguish managed processes from
# orphans.
#
# Arguments:
#   owner        — human-readable label, e.g. "skill-usage-tracker"
#   ttl_seconds  — max lifetime before reaper may SIGTERM (integer)
#   kind         — "short_lived" or "detached_daemon"
#   command...   — the command to background
#
# Returns the background PID via stdout; exits 0 on success.
#
# Constraints:
#   - Never blocks the caller; register call itself is also backgrounded.
#   - Silent on errors — telemetry must never break tool execution.
#   - Requires python3 on PATH; skips registration gracefully if absent.
#   - Respects COGNITIVE_OS_PROJECT_DIR / CLAUDE_PROJECT_DIR for path resolution.

_register_bg() {
  local owner="$1" ttl="$2" kind="$3"
  shift 3

  # Execute the caller's command in the background.
  "$@" &
  local pid=$!

  # Register with the process_registry — also backgrounded so we add < 1 ms
  # overhead to the calling hook.
  local _py
  _py=$(command -v python3 || command -v python || true)
  if [ -n "$_py" ]; then
    (
      local _root="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
      COGNITIVE_OS_PROJECT_DIR="$_root" \
        "$_py" - "$pid" "$owner" "$ttl" "$kind" <<'PYEOF' >/dev/null 2>&1
import sys, os
root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()
sys.path.insert(0, root)
try:
    import lib.process_registry as process_registry
    process_registry.register(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4])
except Exception:
    pass  # Registry must never break the caller
PYEOF
    ) &
  fi

  echo "$pid"
}
