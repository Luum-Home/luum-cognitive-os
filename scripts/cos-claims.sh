#!/usr/bin/env bash
# SCOPE: both
# cos-claims.sh — CLI for engram-backed task claims (P5.1 / ADR-116).
#
# Usage:
#   bash scripts/cos-claims.sh claim  <task-id> <session-id> [--files f1,f2] [--fingerprint sha]
#   bash scripts/cos-claims.sh find   <task-id>
#   bash scripts/cos-claims.sh complete <task-id> <session-id> <evidence>
#   bash scripts/cos-claims.sh release  <task-id> <session-id>
#
# All heavy lifting is delegated to packages/agent-coordination/lib/engram_claims.py
# (symlinked as lib/engram_claims.py).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${PYTHON:-python3}"

_usage() {
  cat <<'EOF'
Usage: cos-claims.sh <subcommand> [args]

Subcommands:
  claim <task-id> <session-id> [--files f1,f2,...] [--fingerprint <sha>]
        Declare that <session-id> will work on <task-id>.
        Prints the claim record as JSON.
        Exit 0 = claimed (or refreshed).
        Exit 1 = already claimed by a different session (prints existing claim).

  find <task-id>
        Print the current claim for <task-id> as JSON, or nothing if unclaimed.
        Exit 0 = claim found.  Exit 1 = no claim.

  complete <task-id> <session-id> <evidence>
        Mark <task-id> as complete. <evidence> is a plain string or JSON object.
        Prints the updated claim record.

  release <task-id> <session-id>
        Cancel the claim without completing.
        No-op if not the owner (exits 0 either way).

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
  claim|find|complete|release) ;;
  --help|-h) _usage; exit 0 ;;
  "")
    echo "cos-claims: subcommand required" >&2
    _usage >&2
    exit 2
    ;;
  *)
    echo "cos-claims: unknown subcommand '${SUBCOMMAND}'" >&2
    _usage >&2
    exit 2
    ;;
esac

# --------------------------------------------------------------------------
# Python inline runner — delegates to lib/engram_claims.py
# --------------------------------------------------------------------------

run_python() {
  PYTHONPATH="${REPO_ROOT}" "${PYTHON}" -c "$1"
}

# --------------------------------------------------------------------------
# Subcommand implementations
# --------------------------------------------------------------------------

cmd_claim() {
  local task_id="${1:-}"
  local session_id="${2:-}"
  if [[ -z "${task_id}" || -z "${session_id}" ]]; then
    echo "cos-claims claim: requires <task-id> <session-id>" >&2
    exit 2
  fi
  shift 2

  local files=""
  local fingerprint=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --files)       files="${2:-}"; shift 2 ;;
      --fingerprint) fingerprint="${2:-}"; shift 2 ;;
      *) echo "cos-claims claim: unknown option '$1'" >&2; exit 2 ;;
    esac
  done

  run_python "
import sys, json
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_claims

files = [f.strip() for f in '${files}'.split(',') if f.strip()] or None
fp = '${fingerprint}' or None

record = engram_claims.claim_task('${task_id}', '${session_id}',
                                   expected_files=files, fingerprint=fp)
print(json.dumps(record, indent=2))

# Exit 1 if a different session already owns the task
if record.get('session_id') != '${session_id}':
    sys.exit(1)
"
}

cmd_find() {
  local task_id="${1:-}"
  if [[ -z "${task_id}" ]]; then
    echo "cos-claims find: requires <task-id>" >&2
    exit 2
  fi

  run_python "
import sys, json
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_claims

record = engram_claims.find_claim('${task_id}')
if record is None:
    sys.exit(1)
print(json.dumps(record, indent=2))
"
}

cmd_complete() {
  local task_id="${1:-}"
  local session_id="${2:-}"
  local evidence="${3:-}"
  if [[ -z "${task_id}" || -z "${session_id}" || -z "${evidence}" ]]; then
    echo "cos-claims complete: requires <task-id> <session-id> <evidence>" >&2
    exit 2
  fi

  run_python "
import sys, json
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_claims

evidence_raw = '''${evidence}'''
try:
    evidence = json.loads(evidence_raw)
except (json.JSONDecodeError, ValueError):
    evidence = evidence_raw

record = engram_claims.complete_task('${task_id}', '${session_id}', evidence)
print(json.dumps(record, indent=2))
"
}

cmd_release() {
  local task_id="${1:-}"
  local session_id="${2:-}"
  if [[ -z "${task_id}" || -z "${session_id}" ]]; then
    echo "cos-claims release: requires <task-id> <session-id>" >&2
    exit 2
  fi

  run_python "
import sys
sys.path.insert(0, '${REPO_ROOT}/lib')
import engram_claims

engram_claims.release_claim('${task_id}', '${session_id}')
print('released')
"
}

# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

case "${SUBCOMMAND}" in
  claim)    cmd_claim    "$@" ;;
  find)     cmd_find     "$@" ;;
  complete) cmd_complete "$@" ;;
  release)  cmd_release  "$@" ;;
esac
