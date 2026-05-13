#!/usr/bin/env bash
# SCOPE: both
# PURPOSE: Crystallise over-represented topic_keys at session end
# EVENT: Stop
# EXIT_CODES: 0=always (advisory — crystallisation failure must not interrupt session shutdown)
#
# Behavior:
#   Fires when a Claude session ends (Stop event).
#   Calls EngramCrystallizer.crystallize_all() to synthesise digest observations
#   for any topic_key that meets the crystallisation thresholds (≥5 recent obs
#   within 30 days OR ≥10 total observations).
#   Logs a JSONL event to .cognitive-os/metrics/crystallization-events.jsonl.
#   Short-circuits immediately when there are no candidates (target latency ≤500ms).
#
# Latency budget:
#   When candidate list is empty: Python startup ~150ms total.
#   When candidates exist: ~150ms per digest save (dominated by engram subprocess).
#
# Input: JSON on stdin per Claude Code hook contract (not used by this hook).
#
# Bash 3.x compatible; kebab-case filename per rules/bash-naming.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${HOOK_REPO_ROOT}}}}"
METRICS_DIR="${PROJECT_DIR}/.cognitive-os/metrics"
LOG_FILE="${METRICS_DIR}/crystallization-events.jsonl"

run_crystallizer() {
  if [ "${COS_SKIP_ENGRAM_CRYSTALLIZER:-0}" = "1" ]; then
    echo "0"
    return 0
  fi
  local count
  count=$(python3 -c "
import sys
sys.path.insert(0, '${HOOK_REPO_ROOT}')
from lib.engram_crystallizer import EngramCrystallizer
digests = EngramCrystallizer().crystallize_all()
print(len(digests))
" 2>/dev/null) || count=0
  echo "${count:-0}"
}

log_event() {
  local count="$1"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u)"
  mkdir -p "${METRICS_DIR}"
  printf '{"event":"crystallization_session_end","digests_created":%s,"timestamp":"%s"}\n' \
    "${count}" "${ts}" >> "${LOG_FILE}" 2>/dev/null || true
}

main() {
  local digest_count
  digest_count="$(run_crystallizer)"
  log_event "${digest_count}"
}

main
exit 0
