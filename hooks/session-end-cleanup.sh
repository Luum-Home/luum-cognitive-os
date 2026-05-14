#!/usr/bin/env bash
# SCOPE: os-only
# session-end-cleanup.sh — runs `cos-cleanup --tier=1 --apply` quietly.
#
# Idempotent. Quiet by default; verbose with COS_CLEANUP_VERBOSE=1.
# NOT registered in settings.json — operator decision (separate task).
set -u
set -o pipefail

SCRIPT_PATH="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
CMD="${ROOT}/scripts/cos-cleanup.sh"

if [[ ! -x "$CMD" ]]; then
  exit 0
fi

if [[ "${COS_CLEANUP_VERBOSE:-0}" == "1" ]]; then
  "$CMD" --tier=1 --apply
  rc=$?
else
  "$CMD" --tier=1 --apply >/dev/null 2>&1
  rc=$?
fi

# Tier-1 should never produce tier-3 candidates; treat any rc<=1 as success.
if (( rc > 1 )); then
  exit "$rc"
fi
exit 0
