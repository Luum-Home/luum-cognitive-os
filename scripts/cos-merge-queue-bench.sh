#!/usr/bin/env bash
# SCOPE: both
# scope: both
# cos-merge-queue-bench.sh — Throughput benchmark CLI for the merge queue (ADR-116 P2.2).
#
# Thin wrapper around scripts/queue_throughput_bench.py that provides a
# familiar bash interface consistent with other COS scripts.
#
# Usage:
#   bash scripts/cos-merge-queue-bench.sh [OPTIONS]
#
# Options:
#   --sessions N              Number of synthetic sessions (default: 5)
#   --commits-per-session M   Commits per session branch (default: 3)
#   --conflict-scenario       All sessions modify the same file (conflict test)
#   --report <path>           Write JSON report to this path
#   --help                    Show this help
#
# Environment:
#   COS_QUEUE_AUTO_REBASE=0   Disable auto-rebase (behind sessions fail)
#   COS_SKIP_GATES=1          Skip composable gate stack in worker (speed)
#
# Exit codes:
#   0 — benchmark completed (may include failed entries; see report)
#   1 — benchmark script error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SESSIONS=5
COMMITS_PER_SESSION=3
CONFLICT_SCENARIO=0
REPORT_PATH=""

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

usage() {
    grep '^#' "$0" | grep -v '^#!/' | sed 's/^# \{0,1\}//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sessions)
            SESSIONS="$2"; shift 2 ;;
        --commits-per-session)
            COMMITS_PER_SESSION="$2"; shift 2 ;;
        --conflict-scenario)
            CONFLICT_SCENARIO=1; shift ;;
        --report)
            REPORT_PATH="$2"; shift 2 ;;
        --help|-h)
            usage ;;
        *)
            echo "[bench] Unknown option: $1" >&2
            exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Build Python args
# ---------------------------------------------------------------------------

py_args=(
    --sessions "${SESSIONS}"
    --commits-per-session "${COMMITS_PER_SESSION}"
)

if [[ "${CONFLICT_SCENARIO}" == "1" ]]; then
    py_args+=(--conflict-scenario)
fi

if [[ -n "${REPORT_PATH}" ]]; then
    py_args+=(--report "${REPORT_PATH}")
fi

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

echo "[bench] Starting merge-queue throughput benchmark"
echo "[bench] sessions=${SESSIONS}, commits-per-session=${COMMITS_PER_SESSION}, conflict=${CONFLICT_SCENARIO}"
[[ -n "${REPORT_PATH}" ]] && echo "[bench] report -> ${REPORT_PATH}"

PYTHONPATH="${REPO_ROOT}" python3 "${SCRIPT_DIR}/queue_throughput_bench.py" "${py_args[@]}"

echo "[bench] Done"
