#!/usr/bin/env bash
# SCOPE: both
# Serialize landing to main through a single-writer merge queue.
set -euo pipefail

REPO="${COS_MERGE_REPO:-$(pwd)}"
REMOTE="${COS_MERGE_REMOTE:-origin}"
MAIN_BRANCH="${COS_MAIN_BRANCH:-main}"
VALIDATE_CMD="${COS_MERGE_VALIDATE_CMD:-python3 scripts/derived_artifact_gate.py}"
DRY_RUN=false
RECOMMENDED_LANE=""
EXECUTED_LANE="${COS_MERGE_EXECUTED_LANE:-landing}"
VALIDATION_RATIONALE_JSON="[]"
CHANGED_FILES_JSON="[]"

usage() {
  cat <<'EOF'
Usage: scripts/merge_to_main.sh [--repo PATH] [--remote origin] [--main main] [--validate CMD] [--recommended-lane LANE] [--executed-lane LANE] [--dry-run]

Acquires .cognitive-os/runtime/main-merge.lock, rebases the current branch on
REMOTE/MAIN, runs validation, fast-forwards main, and pushes. This is the
single-writer path for agent landings to main.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --remote) REMOTE="${2:-}"; shift 2 ;;
    --main) MAIN_BRANCH="${2:-}"; shift 2 ;;
    --validate) VALIDATE_CMD="${2:-}"; shift 2 ;;
    --recommended-lane) RECOMMENDED_LANE="${2:-}"; shift 2 ;;
    --recommended-lane=*) RECOMMENDED_LANE="${1#--recommended-lane=}"; shift ;;
    --executed-lane) EXECUTED_LANE="${2:-}"; shift 2 ;;
    --executed-lane=*) EXECUTED_LANE="${1#--executed-lane=}"; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

REPO="$(cd "$REPO" && pwd -P)"
LOCK_DIR="$REPO/.cognitive-os/runtime/main-merge.lock"
QUEUE_FILE="$REPO/.cognitive-os/runtime/main-merge-queue.jsonl"
MERGE_LANDED=false
mkdir -p "$(dirname "$LOCK_DIR")"


compute_validation_lane() {
  local base_ref="$1"
  local head_ref="$2"
  local payload
  payload=$(PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}" python3 - "$REPO" "$base_ref" "$head_ref" "$RECOMMENDED_LANE" "$EXECUTED_LANE" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1])
base_ref = sys.argv[2]
head_ref = sys.argv[3]
forced_recommended = sys.argv[4] or None
executed = sys.argv[5] or "landing"
proc = subprocess.run(
    ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
    cwd=repo,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
files = [line for line in proc.stdout.splitlines() if line.strip()]
try:
    from lib.validation_lanes import recommend_lane

    rec = recommend_lane(files)
    recommended = forced_recommended or rec.recommended_lane
    rationale = rec.rationale
except Exception:
    recommended = forced_recommended or "landing"
    rationale = ["validation lane recommendation unavailable; defaulting to landing"]
print(json.dumps({
    "changed_files": files,
    "recommended_lane": recommended,
    "executed_lane": executed,
    "validation_rationale": rationale,
}, separators=(",", ":")))
PY
)
  RECOMMENDED_LANE=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)["recommended_lane"])')
  EXECUTED_LANE=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)["executed_lane"])')
  VALIDATION_RATIONALE_JSON=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["validation_rationale"]))')
  CHANGED_FILES_JSON=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["changed_files"]))')
}

append_queue_event() {
  local status="$1"
  python3 - "$QUEUE_FILE" "$branch" "$$" "$status" "$RECOMMENDED_LANE" "$EXECUTED_LANE" "$VALIDATION_RATIONALE_JSON" "$CHANGED_FILES_JSON" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

queue = Path(sys.argv[1])
branch = sys.argv[2]
pid = int(sys.argv[3])
status = sys.argv[4]
recommended = sys.argv[5]
executed = sys.argv[6]
rationale = json.loads(sys.argv[7] or "[]")
files = json.loads(sys.argv[8] or "[]")
queue.parent.mkdir(parents=True, exist_ok=True)
row = {
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "branch": branch,
    "pid": pid,
    "status": status,
    "recommended_lane": recommended,
    "executed_lane": executed,
    "validation_rationale": rationale,
    "changed_files": files,
}
with queue.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
PY
}

emit_merge_receipt() {
  local event_type="$1"
  local trust="$2"
  local outcome="$3"
  local receipt_script="$REPO/scripts/cos-action-receipt"
  [ -x "$receipt_script" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  local current_branch head_sha evidence_json
  current_branch="$(git -C "$REPO" branch --show-current 2>/dev/null || echo "${branch:-unknown}")"
  head_sha="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"
  evidence_json=$(
    COS_RECEIPT_OUTCOME="$outcome" \
    COS_RECEIPT_REMOTE="$REMOTE" \
    COS_RECEIPT_MAIN="$MAIN_BRANCH" \
    python3 - <<'PY' 2>/dev/null || true
import json
import os
print(json.dumps({
    "script": "merge-to-main.sh",
    "outcome": os.environ.get("COS_RECEIPT_OUTCOME", ""),
    "remote": os.environ.get("COS_RECEIPT_REMOTE", ""),
    "main_branch": os.environ.get("COS_RECEIPT_MAIN", ""),
}))
PY
  )
  [ -n "$evidence_json" ] || evidence_json='{"script":"merge-to-main.sh"}'
  local args
  args=("$receipt_script" emit "$event_type" \
    --provider cos-merge-queue \
    --source merge-queue \
    --trust "$trust" \
    --project-dir "$REPO" \
    --branch "$current_branch" \
    --remote "$REMOTE" \
    --governed-path merge-to-main \
    --evidence-json "$evidence_json" \
    --append)
  [ -n "$head_sha" ] && args+=(--commit-sha "$head_sha")
  "${args[@]}" >/dev/null 2>&1 || true
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "main merge already in progress: $LOCK_DIR" >&2
  exit 75
fi
cleanup() {
  local status=$?
  if [ "$status" -ne 0 ] && [ "$MERGE_LANDED" != true ]; then
    emit_merge_receipt "vcs.merge.fail" "verified" "merge-to-main-failed"
  fi
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT

branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
if [ "$branch" = "$MAIN_BRANCH" ]; then
  echo "Refusing to land from $MAIN_BRANCH directly; use a session branch." >&2
  exit 2
fi
if [ -n "$(git -C "$REPO" status --porcelain=v1 --untracked-files=no)" ]; then
  echo "Refusing merge queue landing with tracked dirty worktree." >&2
  exit 3
fi

git -C "$REPO" fetch "$REMOTE" "$MAIN_BRANCH"
compute_validation_lane "$REMOTE/$MAIN_BRANCH" "HEAD"
append_queue_event "started"
emit_merge_receipt "vcs.merge.enqueue" "verified" "merge-to-main-started"

git -C "$REPO" rebase "$REMOTE/$MAIN_BRANCH"
(
  cd "$REPO"
  eval "$VALIDATE_CMD"
)
if [ -n "$(git -C "$REPO" status --porcelain=v1 --untracked-files=no)" ]; then
  echo "Refusing merge queue landing because validation dirtied tracked worktree." >&2
  echo "Commit or restore validation-generated artifacts before landing." >&2
  git -C "$REPO" status --short --untracked-files=no >&2
  exit 4
fi
if [ "$DRY_RUN" = true ]; then
  echo "merge_to_main: dry-run passed for $branch onto $REMOTE/$MAIN_BRANCH"
  exit 0
fi
git -C "$REPO" switch "$MAIN_BRANCH"
git -C "$REPO" merge --ff-only "$branch"
COS_MERGE_TO_MAIN=1 git -C "$REPO" push "$REMOTE" "$MAIN_BRANCH"
MERGE_LANDED=true
emit_merge_receipt "vcs.merge.land" "authoritative" "merge-to-main-pushed"
append_queue_event "pushed"
