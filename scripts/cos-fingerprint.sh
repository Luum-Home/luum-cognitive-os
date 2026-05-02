#!/usr/bin/env bash
# SCOPE: both
# cos-fingerprint.sh — Work-identity fingerprint CLI (ADR-116 P1.2).
#
# Subcommands:
#   compute   <description> [output1 output2 ...]  → print fingerprint
#   find      <fingerprint> [repo_root]            → search active-claims + git log
#   embed     <fingerprint> <commit_msg_file>      → add trailer in-place
#
# Exit codes:
#   0  success / found
#   1  usage error
#   2  not found (find subcommand only)
#   3  python3 not available
#
# Requirements: python3 with packages/agent-coordination/lib/work_identity.py
#               (or the lib/work_identity.py symlink) on PYTHONPATH.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve repo root
# ---------------------------------------------------------------------------

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${_SCRIPT_DIR}/.." && pwd)"

# Make sure work_identity is importable even without installation
export PYTHONPATH="${REPO_ROOT}/packages/agent-coordination/lib:${REPO_ROOT}/lib:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

_require_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'ERROR: python3 not found\n' >&2
    exit 3
  fi
}

_usage() {
  cat <<'EOF'
Usage:
  cos-fingerprint.sh compute <description> [output ...]
      Compute and print a 16-char work fingerprint.

  cos-fingerprint.sh find <fingerprint> [repo_root]
      Search active-claims.json and recent git log for matching fingerprint.
      Exits 0 and prints JSON on match; exits 2 on no match.

  cos-fingerprint.sh embed <fingerprint> <commit_msg_file>
      Add X-COS-Work-Fingerprint trailer to the commit message file in-place.
      Idempotent: running twice produces the same result.
EOF
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_compute() {
  local description="${1:-}"
  shift || true
  local outputs=("$@")

  if [[ -z "$description" ]]; then
    _die "compute requires a description argument"
  fi

  _require_python

  python3 - "$description" "${outputs[@]}" <<'PYEOF'
import sys
sys.path.insert(0, '')

# Allow import from PYTHONPATH set above
from work_identity import compute_fingerprint

description = sys.argv[1]
outputs = sys.argv[2:]
print(compute_fingerprint(description, outputs))
PYEOF
}

cmd_find() {
  local fingerprint="${1:-}"
  local repo_root="${2:-${REPO_ROOT}}"

  if [[ -z "$fingerprint" ]]; then
    _die "find requires a fingerprint argument"
  fi

  _require_python

  python3 - "$fingerprint" "$repo_root" <<'PYEOF'
import json
import sys
from pathlib import Path

sys.path.insert(0, '')
from work_identity import find_existing_work

fingerprint = sys.argv[1]
repo_root = Path(sys.argv[2])

result = find_existing_work(fingerprint, repo_root)
if result is None:
    sys.exit(2)

print(json.dumps(result, indent=2))
sys.exit(0)
PYEOF
}

cmd_embed() {
  local fingerprint="${1:-}"
  local msg_file="${2:-}"

  if [[ -z "$fingerprint" || -z "$msg_file" ]]; then
    _die "embed requires <fingerprint> <commit_msg_file>"
  fi
  if [[ ! -f "$msg_file" ]]; then
    _die "commit message file not found: $msg_file"
  fi

  _require_python

  python3 - "$fingerprint" "$msg_file" <<'PYEOF'
import sys
from pathlib import Path

sys.path.insert(0, '')
from work_identity import embed_in_commit_msg

fingerprint = sys.argv[1]
msg_file = Path(sys.argv[2])

original = msg_file.read_text(encoding="utf-8")
updated = embed_in_commit_msg(original, fingerprint)
msg_file.write_text(updated, encoding="utf-8")
print(updated, end="")
PYEOF
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

SUBCOMMAND="${1:-}"
shift || true

case "$SUBCOMMAND" in
  compute) cmd_compute "$@" ;;
  find)    cmd_find    "$@" ;;
  embed)   cmd_embed   "$@" ;;
  help|--help|-h) _usage ;;
  "")      _usage; exit 1 ;;
  *)       _die "Unknown subcommand: $SUBCOMMAND"; _usage; exit 1 ;;
esac
