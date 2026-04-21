#!/usr/bin/env bash
# sprint-test-summary.sh — ADR-036 Wave 1 CLI wrapper for lib.sprint_test_aggregator
#
# Usage:
#   sprint-test-summary.sh                       # auto-detect 5 most-recent sessions
#   sprint-test-summary.sh <sid1> [<sid2> ...]   # explicit session ids
#   sprint-test-summary.sh --json [ids...]       # machine-readable JSON output
#   sprint-test-summary.sh --limit N             # auto-detect N recent sessions
#
# Exit codes:
#   0 — success, no failures detected
#   1 — success, failures present in aggregated totals
#   2 — usage / environment error
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

JSON_MODE=0
LIMIT=5
SESSION_IDS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)
            JSON_MODE=1
            shift
            ;;
        --limit)
            LIMIT="${2:-5}"
            shift 2
            ;;
        -h|--help)
            sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "error: unknown flag: $1" >&2
            exit 2
            ;;
        *)
            SESSION_IDS+=("$1")
            shift
            ;;
    esac
done

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

python3 - "$JSON_MODE" "$LIMIT" "${SESSION_IDS[@]+"${SESSION_IDS[@]}"}" <<'PY'
import json
import sys

from lib.sprint_test_aggregator import aggregate, detect_recent_sessions, render_text

json_mode = sys.argv[1] == "1"
limit = int(sys.argv[2])
session_ids = sys.argv[3:]

if not session_ids:
    session_ids = detect_recent_sessions(limit=limit)
    if not session_ids:
        print("error: no sessions found under .cognitive-os/sessions/", file=sys.stderr)
        sys.exit(2)

summary = aggregate(session_ids)

if json_mode:
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
else:
    print(render_text(summary))

sys.exit(0 if summary["status"] == "pass" else 1)
PY
