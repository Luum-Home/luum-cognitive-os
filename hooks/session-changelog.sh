#!/usr/bin/env bash
# SCOPE: os-only
# session-changelog.sh — Stop hook
# CONCERNS: audit, changelog, session-tracking
#
# Generates a session changelog at session end.
# Writes to .cognitive-os/changelogs/{session_id}.md
#
# Exit codes:
#   0 — always (never blocks session end)

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Stop hooks do not receive stdin tool JSON.

# Determine project dir
if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
elif [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CODEX_PROJECT_DIR"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
    PROJECT_DIR="$(pwd)"
fi

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-}}}"
if [ -z "$SESSION_ID" ]; then
    exit 0
fi

CHANGELOGS_DIR="$PROJECT_DIR/.cognitive-os/changelogs"
mkdir -p "$CHANGELOGS_DIR"

# Generate session changelog via Python lib
CHANGELOG_MD=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from lib.changelog_generator import generate_session_changelog, format_changelog_md

project_dir = '$PROJECT_DIR'
session_id = '$SESSION_ID'

try:
    changelog = generate_session_changelog(project_dir, session_id)
    print(format_changelog_md(changelog))
except Exception as e:
    print('# Session Changelog: ' + session_id)
    print('')
    print('_Error generating changelog: ' + str(e) + '_')
" 2>/dev/null) || CHANGELOG_MD="# Session Changelog: $SESSION_ID

_Changelog generation skipped._
"

# Write session changelog
echo "$CHANGELOG_MD" > "$CHANGELOGS_DIR/$SESSION_ID.md"

# If sprint-status.yaml exists, append summary to sprint changelog
SPRINT_STATUS="$PROJECT_DIR/.cognitive-os/workflows/state/sprint-status.yaml"
if [ -f "$SPRINT_STATUS" ]; then
    SPRINT_ID=$(grep 'sprint_id' "$SPRINT_STATUS" 2>/dev/null \
        | head -1 \
        | sed 's/.*sprint_id[[:space:]]*:[[:space:]]*//' \
        | tr -d '"'"'"'[:space:]') || SPRINT_ID=""

    if [ -n "$SPRINT_ID" ]; then
        SPRINT_CHANGELOG="$CHANGELOGS_DIR/sprint-$SPRINT_ID.md"
        TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "")

        # Append session summary line to sprint changelog
        if [ ! -f "$SPRINT_CHANGELOG" ]; then
            printf '# Sprint Changelog: %s\n\n' "$SPRINT_ID" > "$SPRINT_CHANGELOG"
        fi
        printf '\n## Session: %s (%s)\n\n' "$SESSION_ID" "$TIMESTAMP" >> "$SPRINT_CHANGELOG"

        # Extract Tasks Completed count from session changelog
        TASKS_LINE=$(echo "$CHANGELOG_MD" | grep -E '^## Tasks Completed' | head -1 || echo "## Tasks Completed (0)")
        printf '%s\n\n' "$TASKS_LINE" >> "$SPRINT_CHANGELOG"
        printf '[Full session changelog](./%s.md)\n' "$SESSION_ID" >> "$SPRINT_CHANGELOG"
    fi
fi

exit 0
