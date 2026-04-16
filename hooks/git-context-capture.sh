#!/usr/bin/env bash
# git-context-capture.sh — Stop hook
# CONCERNS: audit, git-context, session-tracking
#
# Captures git context at session end: branch, commits, diff stat.
# Writes to sessions/{id}/git-context.json and enriches meta.json.
#
# Exit codes:
#   0 — always (never blocks session end)

set -uo pipefail

# Stop hooks do not receive stdin tool JSON.

# Determine project dir
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
elif [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
else
    PROJECT_DIR="$(pwd)"
fi

# Resolve session ID
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
    exit 0
fi

SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"

# Read start_commit from meta.json
COMMIT_START=""
META_FILE="$SESSION_DIR/meta.json"
if [ -f "$META_FILE" ] && command -v jq &>/dev/null; then
    COMMIT_START=$(jq -r '.start_commit // ""' "$META_FILE" 2>/dev/null || echo "")
fi

# Fall back to current HEAD if no start_commit
if [ -z "$COMMIT_START" ]; then
    COMMIT_START=$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo "")
fi

# Capture git context via Python lib
GIT_CONTEXT_JSON=$(python3 -c "
import json, sys
sys.path.insert(0, '$PROJECT_DIR')
from lib.git_context import capture_session_git_context

project_dir = '$PROJECT_DIR'
commit_start = '$COMMIT_START'

try:
    ctx = capture_session_git_context(project_dir, commit_start)
    print(json.dumps({
        'branch': ctx.branch,
        'commit_start': ctx.commit_start,
        'commit_end': ctx.commit_end,
        'commits': [
            {
                'sha': c.sha,
                'message': c.message,
                'author': c.author,
                'files_changed': c.files_changed,
            }
            for c in ctx.commits
        ],
        'diff_stat': ctx.diff_stat,
        'files_added': ctx.files_added,
        'files_modified': ctx.files_modified,
        'files_deleted': ctx.files_deleted,
    }))
except Exception as e:
    print(json.dumps({
        'branch': 'unknown',
        'commit_start': '',
        'commit_end': '',
        'commits': [],
        'diff_stat': '',
        'files_added': 0,
        'files_modified': 0,
        'files_deleted': 0,
        'error': str(e),
    }))
" 2>/dev/null) || GIT_CONTEXT_JSON="{}"

if [ -z "$GIT_CONTEXT_JSON" ] || [ "$GIT_CONTEXT_JSON" = "null" ]; then
    GIT_CONTEXT_JSON="{}"
fi

# Write git-context.json
mkdir -p "$SESSION_DIR"
echo "$GIT_CONTEXT_JSON" > "$SESSION_DIR/git-context.json"

# Enrich meta.json with git fields
if [ -f "$META_FILE" ] && command -v jq &>/dev/null; then
    GIT_BRANCH=$(echo "$GIT_CONTEXT_JSON" | jq -r '.branch // "unknown"' 2>/dev/null || echo "unknown")
    GIT_COMMIT_START=$(echo "$GIT_CONTEXT_JSON" | jq -r '.commit_start // ""' 2>/dev/null || echo "")
    GIT_COMMIT_END=$(echo "$GIT_CONTEXT_JSON" | jq -r '.commit_end // ""' 2>/dev/null || echo "")

    UPDATED_META=$(jq \
        --arg branch "$GIT_BRANCH" \
        --arg cs "$GIT_COMMIT_START" \
        --arg ce "$GIT_COMMIT_END" \
        '. + {git_branch: $branch, commit_start: $cs, commit_end: $ce}' \
        "$META_FILE" 2>/dev/null) || UPDATED_META=""

    if [ -n "$UPDATED_META" ]; then
        echo "$UPDATED_META" > "$META_FILE"
    fi
fi

# Append to session-audit.jsonl
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$METRICS_DIR"

BRANCH=$(echo "$GIT_CONTEXT_JSON" | jq -r '.branch // "unknown"' 2>/dev/null || echo "unknown")
COMMITS_COUNT=$(echo "$GIT_CONTEXT_JSON" | jq '.commits | length' 2>/dev/null || echo "0")
FILES_ADDED=$(echo "$GIT_CONTEXT_JSON" | jq '.files_added // 0' 2>/dev/null || echo "0")
FILES_MODIFIED=$(echo "$GIT_CONTEXT_JSON" | jq '.files_modified // 0' 2>/dev/null || echo "0")
FILES_DELETED=$(echo "$GIT_CONTEXT_JSON" | jq '.files_deleted // 0' 2>/dev/null || echo "0")
FILES_CHANGED=$(( FILES_ADDED + FILES_MODIFIED + FILES_DELETED ))

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "")
printf '{"timestamp":"%s","session_id":"%s","branch":"%s","commits":%s,"files_changed":%s}\n' \
    "$TIMESTAMP" "$SESSION_ID" "$BRANCH" "$COMMITS_COUNT" "$FILES_CHANGED" \
    >> "$METRICS_DIR/session-audit.jsonl" 2>/dev/null || true

exit 0
