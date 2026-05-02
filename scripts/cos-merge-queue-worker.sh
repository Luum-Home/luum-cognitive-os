#!/usr/bin/env bash
# SCOPE: both
# scope: both
# cos-merge-queue-worker.sh — Single-writer merge-queue worker (ADR-116 P2.2).
#
# Acquires an exclusive flock on the queue lock file, dequeues one entry at a
# time, runs the composable gate stack, ff-merges to main, pushes, and runs a
# post-merge verification.  If post-merge verify fails, auto-reverts the merge.
#
# Environment:
#   COS_MERGE_QUEUE_DRY=1   — dry-run: print what would happen, do NOT merge/push
#   COS_SKIP_SMOKE=1        — skip pytest smoke gate (for portability / unit testing)
#   COS_SKIP_GATES=1        — skip the composable gate stack (tests only)
#   MERGE_QUEUE_PATH        — override the queue JSONL file location
#   COGNITIVE_OS_SESSION_ID — worker session identifier
#   MERGE_TARGET_BRANCH     — branch to merge into (default: main)
#   MERGE_REMOTE            — remote name (default: origin)
#   PYTEST_SMOKE_ARGS       — extra args forwarded to the pytest smoke step
#
# Exit codes:
#   0 — queue was empty, or entry processed successfully
#   1 — gate failure or unexpected error
#   2 — lock already held by another worker (don't retry immediately)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DRY_RUN="${COS_MERGE_QUEUE_DRY:-0}"
TARGET_BRANCH="${MERGE_TARGET_BRANCH:-main}"
REMOTE="${MERGE_REMOTE:-origin}"
WORKER_SESSION="${COGNITIVE_OS_SESSION_ID:-worker-$$}"
PYTEST_SMOKE_ARGS="${PYTEST_SMOKE_ARGS:--q}"
# COS_QUEUE_AUTO_REBASE=1  — attempt git rebase when session is behind main
# COS_QUEUE_AUTO_REBASE=0  — skip rebase; behind branches fail immediately
COS_QUEUE_AUTO_REBASE="${COS_QUEUE_AUTO_REBASE:-1}"
# Populated by gate_ancestry on rebase conflict; read by main() for dequeue notes.
REBASE_CONFLICT_FILES=""

# Derive queue paths.
if [[ -n "${MERGE_QUEUE_PATH:-}" ]]; then
    QUEUE_FILE="${MERGE_QUEUE_PATH}"
else
    QUEUE_FILE="${REPO_ROOT}/.cognitive-os/sessions/merge-queue.jsonl"
fi
# Keep the worker single-writer lock separate from lib.merge_queue's
# read-modify-write lock.  Reusing the same file self-deadlocks when this
# process holds the worker lock and a Python subprocess calls dequeue().
WORKER_LOCK="${QUEUE_FILE%.jsonl}.worker.lock"

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

log()  { echo "[worker] $*"; }
warn() { echo "[worker] WARN: $*" >&2; }
die()  { echo "[worker] ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Python helper: run a one-liner against the merge_queue module
# ---------------------------------------------------------------------------

mq_python() {
    PYTHONPATH="${REPO_ROOT}" python3 - "$@"
}

# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

step_peek() {
    mq_python <<'PYEOF'
import json, sys
from lib.merge_queue import peek
e = peek()
if e is None:
    print("")
else:
    print(json.dumps(e))
PYEOF
}

step_mark_in_progress() {
    local entry_id="$1"
    mq_python <<PYEOF
import sys
from lib.merge_queue import dequeue
# We can't mark in-progress via the public dequeue (only terminal statuses).
# Update the JSONL directly under a lock via internal helper.
import json, fcntl, os
from pathlib import Path
from lib.merge_queue import _resolve_queue_path, _read_all, _write_all, _now_iso

path = _resolve_queue_path()
lock_file = path.with_suffix(".lock")

with lock_file.open("a", encoding="utf-8") as lf:
    fcntl.flock(lf, fcntl.LOCK_EX)
    try:
        entries = _read_all(path)
        for e in entries:
            if e.get("id") == "${entry_id}":
                e["status"] = "in-progress"
                break
        _write_all(path, entries)
    finally:
        fcntl.flock(lf, fcntl.LOCK_UN)
PYEOF
}

step_dequeue() {
    local entry_id="$1"
    local entry_status="$2"
    local notes="$3"
    mq_python <<PYEOF
from lib.merge_queue import dequeue
dequeue("${entry_id}", status="${entry_status}", notes="""${notes}""" or None)
PYEOF
}

# ---------------------------------------------------------------------------
# Gate: ensure session branch is descended from origin/main
# (auto-rebase if behind and COS_QUEUE_AUTO_REBASE=1)
# ---------------------------------------------------------------------------

gate_ancestry() {
    local branch="$1"
    log "Gate: ancestry check — ${branch} must be ahead of ${REMOTE}/${TARGET_BRANCH}"

    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] would run: git fetch ${REMOTE} ${TARGET_BRANCH}"
        log "[DRY-RUN] would run: git merge-base --is-ancestor ${REMOTE}/${TARGET_BRANCH} ${branch}"
        return 0
    fi

    git fetch "${REMOTE}" "${TARGET_BRANCH}" 2>&1 | sed 's/^/    fetch: /'

    if git merge-base --is-ancestor "${REMOTE}/${TARGET_BRANCH}" "${branch}" 2>/dev/null; then
        log "Gate PASS: ${branch} contains ${REMOTE}/${TARGET_BRANCH}"
        return 0
    fi

    # Session branch is behind target — attempt auto-rebase if enabled.
    local auto_rebase="${COS_QUEUE_AUTO_REBASE:-1}"
    if [[ "$auto_rebase" == "0" ]]; then
        die "Gate FAIL: ${branch} is behind ${REMOTE}/${TARGET_BRANCH} and COS_QUEUE_AUTO_REBASE=0."
    fi

    log "Gate: ${branch} is behind ${REMOTE}/${TARGET_BRANCH} — attempting auto-rebase"
    local rebase_out
    rebase_out=$(PYTHONPATH="${REPO_ROOT}" python3 - <<PYEOF
import json, sys
from pathlib import Path
from lib.queue_rebase import rebase_onto
result = rebase_onto("${branch}", "${REMOTE}/${TARGET_BRANCH}", Path("${REPO_ROOT}"))
print(json.dumps({
    "success":   result.success,
    "new_sha":   result.new_sha,
    "conflicts": result.conflicts,
    "aborted":   result.aborted,
}))
PYEOF
)
    local success
    success=$(echo "$rebase_out" | python3 -c 'import sys,json; print(json.load(sys.stdin)["success"])')

    if [[ "$success" == "True" ]]; then
        log "Gate PASS: rebase succeeded — ${branch} is now ahead of ${REMOTE}/${TARGET_BRANCH}"
        return 0
    fi

    # Rebase failed — extract conflict list and surface it.
    local conflicts
    conflicts=$(echo "$rebase_out" | python3 -c 'import sys,json; print(", ".join(json.load(sys.stdin)["conflicts"]) or "<none parsed>")')
    # Mark entry failed-conflict in caller via non-zero exit.
    # Capture notes for step_dequeue in main().
    REBASE_CONFLICT_FILES="${conflicts}"
    die "Gate FAIL: rebase conflict on ${branch} — conflicting files: ${conflicts}"
}

# ---------------------------------------------------------------------------
# Gate: composable gate stack (replaces ad-hoc smoke gate)
# ---------------------------------------------------------------------------

gate_stack_run() {
    local branch="$1"
    log "Gate stack: running composable gate stack on '${branch}'"

    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] would run gate stack: bash scripts/cos-gate-stack.sh run ${branch}"
        return 0
    fi

    if [[ "${COS_SKIP_GATES:-0}" == "1" ]]; then
        log "Gate stack SKIPPED (COS_SKIP_GATES=1)"
        return 0
    fi

    bash "${SCRIPT_DIR}/cos-gate-stack.sh" run "${branch}" \
        2>&1 | sed 's/^/    gate: /' \
        || die "Gate stack FAIL: one or more gates failed on '${branch}'"

    log "Gate stack PASS"
}

# ---------------------------------------------------------------------------
# Gate: pytest smoke on the session branch tip (kept for explicit invocation)
# ---------------------------------------------------------------------------

gate_smoke_tests() {
    local branch="$1"
    log "Gate: pytest smoke — tests/unit/ on ${branch}"

    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] would run: python3 -m pytest tests/unit/ ${PYTEST_SMOKE_ARGS}"
        return 0
    fi

    if [[ "${COS_SKIP_SMOKE:-0}" == "1" ]]; then
        log "Gate SKIP: pytest smoke skipped (COS_SKIP_SMOKE=1)"
        return 0
    fi

    (
        cd "${REPO_ROOT}"
        PYTHONPATH="${REPO_ROOT}" python3 -m pytest tests/unit/ ${PYTEST_SMOKE_ARGS} \
            2>&1 | sed 's/^/    pytest: /'
    ) || die "Gate FAIL: pytest smoke tests failed on ${branch}"

    log "Gate PASS: pytest smoke"
}

# ---------------------------------------------------------------------------
# Merge step — returns merged SHA via MERGED_SHA global
# ---------------------------------------------------------------------------

MERGED_SHA=""

step_merge() {
    local branch="$1"
    log "Merge: ff-only ${branch} -> ${TARGET_BRANCH} and push"

    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] would run: git checkout ${TARGET_BRANCH}"
        log "[DRY-RUN] would run: git merge --ff-only ${branch}"
        log "[DRY-RUN] would run: git push ${REMOTE} ${TARGET_BRANCH}"
        log "[DRY-RUN] would run: git branch -d ${branch}"
        log "[DRY-RUN] would run post-merge verify"
        return 0
    fi

    git checkout "${TARGET_BRANCH}"
    git merge --ff-only "${branch}" \
        || die "Merge FAIL: --ff-only failed for ${branch} (branch is not fast-forwardable)"
    # Capture the merged SHA before push.
    MERGED_SHA="$(git rev-parse HEAD)"
    git push "${REMOTE}" "${TARGET_BRANCH}"
    # Clean up the remote session branch; best-effort.
    git push "${REMOTE}" --delete "${branch}" 2>/dev/null \
        || warn "Could not delete remote branch ${branch} (may not exist remotely)"
    git branch -d "${branch}" 2>/dev/null \
        || warn "Could not delete local branch ${branch}"
    log "Merge SUCCESS: ${branch} -> ${TARGET_BRANCH} (sha=${MERGED_SHA})"
}

# ---------------------------------------------------------------------------
# Post-merge verification + auto-revert
# ---------------------------------------------------------------------------

step_post_merge_verify() {
    local merged_sha="$1"

    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] would run post-merge verify on sha=${merged_sha}"
        return 0
    fi

    if [[ "${COS_SKIP_GATES:-0}" == "1" ]]; then
        log "Post-merge verify SKIPPED (COS_SKIP_GATES=1)"
        return 0
    fi

    log "Post-merge verify: running on sha=${merged_sha}"
    local verify_ok=0
    PYTHONPATH="${REPO_ROOT}" python3 - "${merged_sha}" "${REPO_ROOT}" <<'PYEOF' || verify_ok=$?
import sys
merged_sha = sys.argv[1]
repo_root  = sys.argv[2]

from lib.merge_rollback import verify_post_merge
ok = verify_post_merge(merged_sha, repo_root)
sys.exit(0 if ok else 1)
PYEOF

    if [[ $verify_ok -ne 0 ]]; then
        log "Post-merge verify FAILED for sha=${merged_sha} — triggering auto-revert"
        PYTHONPATH="${REPO_ROOT}" python3 - "${merged_sha}" "${REPO_ROOT}" "${REMOTE}" "${TARGET_BRANCH}" <<'PYEOF'
import sys
merged_sha    = sys.argv[1]
repo_root     = sys.argv[2]
remote        = sys.argv[3]
target_branch = sys.argv[4]

from lib.merge_rollback import auto_revert
result = auto_revert(
    merged_sha=merged_sha,
    reason="post-merge verify failed",
    repo_root=repo_root,
    remote=remote,
    target_branch=target_branch,
)
if result["reverted"]:
    print(f"[worker] Auto-revert succeeded: revert_sha={result['revert_sha']}")
else:
    print(f"[worker] Auto-revert FAILED: {result.get('error')}", file=sys.stderr)
    sys.exit(1)
PYEOF
        return 1
    fi

    log "Post-merge verify PASSED for sha=${merged_sha}"
    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    mkdir -p "$(dirname "${WORKER_LOCK}")"

    # Acquire the exclusive worker lock (non-blocking: exit 2 if held).
    exec 9>"${WORKER_LOCK}"
    if ! flock -n 9; then
        log "Another worker holds the lock — exiting (exit 2)"
        exit 2
    fi
    log "Acquired worker lock: ${WORKER_LOCK}"

    # Peek the queue.
    entry_json="$(step_peek)"
    if [[ -z "$entry_json" ]]; then
        log "Queue is empty — nothing to do"
        exit 0
    fi

    entry_id="$(echo "$entry_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
    session_branch="$(echo "$entry_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["session_branch"])')"
    session_id="$(echo "$entry_json"  | python3 -c 'import sys,json; print(json.load(sys.stdin)["session_id"])')"

    log "Processing entry ${entry_id}: branch=${session_branch} session=${session_id}"

    # Mark in-progress.
    if [[ "$DRY_RUN" != "1" ]]; then
        step_mark_in_progress "${entry_id}"
    else
        log "[DRY-RUN] would mark ${entry_id} in-progress"
    fi

    # Run gate stack + merge — capture failures for clean dequeue.
    failure_notes=""
    (
        set -e
        gate_ancestry    "${session_branch}"
        gate_stack_run   "${session_branch}"
        step_merge       "${session_branch}"
    ) || {
        failure_notes="worker step failed (see worker log for details)"
    }

    if [[ -n "$failure_notes" ]]; then
        log "Processing FAILED for ${entry_id}: ${failure_notes}"
        # Distinguish rebase-conflict failures so consumers can act on them.
        # status is always "failed" (schema constraint); conflict detail goes in notes.
        local fail_notes="${failure_notes}"
        if [[ -n "${REBASE_CONFLICT_FILES}" ]]; then
            fail_notes="failed-conflict: rebase conflict — files: ${REBASE_CONFLICT_FILES}"
        fi
        if [[ "$DRY_RUN" != "1" ]]; then
            step_dequeue "${entry_id}" "failed" "${fail_notes}"
        else
            log "[DRY-RUN] would mark ${entry_id} failed: ${fail_notes}"
        fi
        exit 1
    fi

    # Post-merge verification + auto-revert.
    if [[ "$DRY_RUN" != "1" ]] && [[ -n "${MERGED_SHA}" ]]; then
        if ! step_post_merge_verify "${MERGED_SHA}"; then
            local revert_notes="post-merge verify failed — auto-reverted sha=${MERGED_SHA}"
            log "${revert_notes}"
            step_dequeue "${entry_id}" "failed" "${revert_notes}"
            exit 1
        fi
    elif [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] would run post-merge verify"
    fi

    # Success.
    notes="merged ${session_branch} into ${TARGET_BRANCH} (sha=${MERGED_SHA})"
    if [[ "$DRY_RUN" != "1" ]]; then
        step_dequeue "${entry_id}" "completed" "${notes}"
    else
        log "[DRY-RUN] would mark ${entry_id} completed: ${notes}"
    fi

    log "Done: ${entry_id} -> completed"
}

main "$@"
