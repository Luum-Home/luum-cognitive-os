#!/usr/bin/env bash
# SCOPE: both
# cos-locks.sh — CLI for engram-backed cross-session advisory locks (P5.2 / ADR-116).
#
# Usage:
#   bash scripts/cos-locks.sh acquire   <resource> <session-id> [<ttl-seconds>]
#   bash scripts/cos-locks.sh release   <resource> <session-id>
#   bash scripts/cos-locks.sh heartbeat <resource> <session-id>
#   bash scripts/cos-locks.sh find      <resource>
#
# All heavy lifting is delegated to packages/agent-coordination/lib/engram_locks.py
# (symlinked as lib/engram_locks.py).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python3}"

_usage() {
  cat <<'EOF'
Usage: cos-locks.sh <subcommand> [args]

Subcommands:
  acquire <resource> <session-id> [<ttl-seconds>]
        Acquire an advisory lock on <resource> for <session-id>.
        <ttl-seconds> defaults to 300.
        Prints the lock record as JSON.
        Exit 0 = acquired (or refreshed for same session).
        Exit 1 = locked by a different live session.

  release <resource> <session-id>
        Release the lock if held by <session-id>.
        Exit 0 = released (or not held — no-op).
        Exit 1 = lock held by a different session.

  heartbeat <resource> <session-id>
        Extend the lock's effective TTL.
        Exit 0 = heartbeat written.
        Exit 1 = not the lock owner or lock does not exist.

  find <resource>
        Print the current lock record as JSON, or nothing if free.
        Exit 0 = lock found.  Exit 1 = no live lock.

Options:
  --help, -h    Show this message.
EOF
}

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------

SUBCOMMAND="${1:-}"
shift || true

case "${SUBCOMMAND}" in
  acquire|release|heartbeat|find) ;;
  --help|-h) _usage; exit 0 ;;
  "")
    echo "cos-locks: subcommand required" >&2
    _usage >&2
    exit 2
    ;;
  *)
    echo "cos-locks: unknown subcommand '${SUBCOMMAND}'" >&2
    _usage >&2
    exit 2
    ;;
esac

# --------------------------------------------------------------------------
# Python inline runner — delegates to lib/engram_locks.py
# --------------------------------------------------------------------------

run_python() {
  PYTHONPATH="${REPO_ROOT}" "${PYTHON}" -c "$1"
}

# --------------------------------------------------------------------------
# Subcommand implementations
# --------------------------------------------------------------------------

cmd_acquire() {
  local resource="${1:-}"
  local session_id="${2:-}"
  local ttl="${3:-300}"
  if [[ -z "${resource}" || -z "${session_id}" ]]; then
    echo "cos-locks acquire: requires <resource> <session-id>" >&2
    exit 2
  fi

  run_python "
import sys, json
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_locks

result = engram_locks.acquire_lock('${resource}', '${session_id}', ttl_seconds=${ttl})
if result is None:
    # Locked by another session — find and print it so caller knows who holds it
    existing = engram_locks.find_lock('${resource}')
    if existing:
        print(json.dumps(existing, indent=2), file=sys.stderr)
    print('locked', file=sys.stderr)
    sys.exit(1)

print(json.dumps(result, indent=2))
"
}

cmd_release() {
  local resource="${1:-}"
  local session_id="${2:-}"
  if [[ -z "${resource}" || -z "${session_id}" ]]; then
    echo "cos-locks release: requires <resource> <session-id>" >&2
    exit 2
  fi

  run_python "
import sys
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_locks

ok = engram_locks.release_lock('${resource}', '${session_id}')
if ok:
    print('released')
else:
    print('not-owner-or-absent', file=sys.stderr)
    sys.exit(1)
"
}

cmd_heartbeat() {
  local resource="${1:-}"
  local session_id="${2:-}"
  if [[ -z "${resource}" || -z "${session_id}" ]]; then
    echo "cos-locks heartbeat: requires <resource> <session-id>" >&2
    exit 2
  fi

  run_python "
import sys
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_locks

ok = engram_locks.heartbeat_lock('${resource}', '${session_id}')
if ok:
    print('ok')
else:
    print('not-owner-or-absent', file=sys.stderr)
    sys.exit(1)
"
}

cmd_find() {
  local resource="${1:-}"
  if [[ -z "${resource}" ]]; then
    echo "cos-locks find: requires <resource>" >&2
    exit 2
  fi

  run_python "
import sys, json
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_locks

lock = engram_locks.find_lock('${resource}')
if lock is None:
    sys.exit(1)
print(json.dumps(lock, indent=2))
"
}

# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

case "${SUBCOMMAND}" in
  acquire)   cmd_acquire   "$@" ;;
  release)   cmd_release   "$@" ;;
  heartbeat) cmd_heartbeat "$@" ;;
  find)      cmd_find      "$@" ;;
esac
