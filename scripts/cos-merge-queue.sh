#!/usr/bin/env bash
# SCOPE: both
# scope: both
# cos-merge-queue.sh — CLI for the P2.2 file-based merge queue (ADR-116).
#
# Usage:
#   cos-merge-queue.sh enqueue <session_branch> <session_id> [--recommended-lane LANE] [--executed-lane LANE] [expected_file ...]
#   cos-merge-queue.sh peek
#   cos-merge-queue.sh status <entry_id>
#   cos-merge-queue.sh list
#   cos-merge-queue.sh dequeue <entry_id> [completed|failed] [notes]
#
# Environment:
#   MERGE_QUEUE_PATH  — override the queue file location
#   COGNITIVE_OS_SESSION_ID — used as session_id when not supplied explicitly
#
# Exit codes:
#   0 — success
#   1 — usage error or Python error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
    cat >&2 <<EOF
Usage:
  $(basename "$0") enqueue  <session_branch> <session_id> [--recommended-lane LANE] [--executed-lane LANE] [expected_file ...]
  $(basename "$0") peek
  $(basename "$0") status   <entry_id>
  $(basename "$0") list
  $(basename "$0") dequeue  <entry_id> [completed|failed] [notes]
EOF
    exit 1
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

run_python() {
    # Run a snippet against the merge_queue module located in packages/.
    PYTHONPATH="${REPO_ROOT}" python3 - "$@"
}

# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

cmd_enqueue() {
    local session_branch="${1:-}"
    local session_id="${2:-${COGNITIVE_OS_SESSION_ID:-}}"
    shift 2 2>/dev/null || true

    [[ -z "$session_branch" ]] && die "enqueue requires <session_branch>"
    [[ -z "$session_id" ]]    && die "enqueue requires <session_id> (or set COGNITIVE_OS_SESSION_ID)"

    local recommended_lane=""
    local executed_lane=""
    local files=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --recommended-lane) recommended_lane="${2:-}"; shift 2 ;;
            --recommended-lane=*) recommended_lane="${1#--recommended-lane=}"; shift ;;
            --executed-lane) executed_lane="${2:-}"; shift 2 ;;
            --executed-lane=*) executed_lane="${1#--executed-lane=}"; shift ;;
            --changed-file) files+=("${2:-}"); shift 2 ;;
            --changed-file=*) files+=("${1#--changed-file=}"); shift ;;
            *) files+=("$1"); shift ;;
        esac
    done

    # Build a JSON array of expected/changed files from remaining args.
    local files_json="[]"
    if [[ ${#files[@]} -gt 0 ]]; then
        files_json="$(python3 -c "import sys,json; print(json.dumps(sys.argv[1:]))" "${files[@]}")"
    fi

    PYTHONPATH="${REPO_ROOT}" python3 - \
        "${session_branch}" "${session_id}" "${files_json}" "${recommended_lane}" "${executed_lane}" <<'PYEOF'
import sys, json
from lib.merge_queue import enqueue  # noqa: E402
session_branch = sys.argv[1]
session_id     = sys.argv[2]
expected_files = json.loads(sys.argv[3])
recommended_lane = sys.argv[4] or None
executed_lane = sys.argv[5] or None
entry_id = enqueue(
    session_branch=session_branch,
    session_id=session_id,
    expected_files=expected_files,
    recommended_lane=recommended_lane,
    executed_lane=executed_lane,
)
print(entry_id)
PYEOF
}

cmd_peek() {
    run_python <<'PYEOF'
import sys, json
from lib.merge_queue import peek  # noqa: E402

entry = peek()
if entry is None:
    print("(queue is empty)")
else:
    print(json.dumps(entry, indent=2))
PYEOF
}

cmd_status() {
    local entry_id="${1:-}"
    [[ -z "$entry_id" ]] && die "status requires <entry_id>"

    PYTHONPATH="${REPO_ROOT}" python3 - "${entry_id}" <<'PYEOF'
import sys, json
from lib.merge_queue import status  # noqa: E402

entry = status(sys.argv[1])
if entry is None:
    print("(not found)")
    sys.exit(1)
else:
    print(json.dumps(entry, indent=2))
PYEOF
}

cmd_list() {
    run_python <<'PYEOF'
import sys, json
from lib.merge_queue import list_pending  # noqa: E402

entries = list_pending()
if not entries:
    print("(no pending entries)")
else:
    for e in entries:
        print(json.dumps(e))
PYEOF
}

cmd_dequeue() {
    local entry_id="${1:-}"
    local entry_status="${2:-completed}"
    local notes="${3:-}"

    [[ -z "$entry_id" ]] && die "dequeue requires <entry_id>"

    PYTHONPATH="${REPO_ROOT}" python3 - \
        "${entry_id}" "${entry_status}" "${notes}" <<'PYEOF'
import sys
from lib.merge_queue import dequeue  # noqa: E402

entry_id     = sys.argv[1]
entry_status = sys.argv[2]
notes        = sys.argv[3] if sys.argv[3] else None

ok = dequeue(entry_id, status=entry_status, notes=notes)
if ok:
    print(f"OK: {entry_id} -> {entry_status}")
else:
    print(f"WARN: entry not found: {entry_id}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

CMD="${1:-}"
shift || true

case "$CMD" in
    enqueue)  cmd_enqueue  "$@" ;;
    peek)     cmd_peek           ;;
    status)   cmd_status   "$@" ;;
    list)     cmd_list           ;;
    dequeue)  cmd_dequeue  "$@" ;;
    *)        usage              ;;
esac
