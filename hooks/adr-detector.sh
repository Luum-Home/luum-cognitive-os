#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: architecture, governance, documentation
# ADR auto-detector — PostToolUse hook on Bash
# Fires on git commit commands, analyzes the commit for architectural
# significance, and generates draft ADR documents when threshold is met.
#
# ASYNC: true (non-blocking — must never slow down commits)
# Always exits 0.  Errors are logged, never propagated.
#
# Author: luum
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
RATE_LIMIT_FILE="$METRICS_DIR/.adr-session-count"
MAX_PER_SESSION=3

# Read stdin (PostToolUse JSON payload)
INPUT=$(cat)

# --- Quick exit: only fire on git commit commands ---
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$COMMAND" ] && exit 0

# Match "git commit" anywhere in the command
if ! echo "$COMMAND" | grep -qE 'git\s+commit'; then
    exit 0
fi

# --- Rate limit: max N ADR drafts per session ---
mkdir -p "$METRICS_DIR"
SESSION_COUNT=0
if [ -f "$RATE_LIMIT_FILE" ]; then
    SESSION_COUNT=$(cat "$RATE_LIMIT_FILE" 2>/dev/null || echo "0")
    SESSION_COUNT=${SESSION_COUNT:-0}
fi
if [ "$SESSION_COUNT" -ge "$MAX_PER_SESSION" ]; then
    exit 0
fi

# --- Extract commit hash from tool output ---
TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
[ -z "$TOOL_OUTPUT" ] && exit 0

# Try to extract a short commit hash from typical git commit output
# Patterns: "[main abc1234]", "[branch abc1234]", "abc1234 commit msg"
COMMIT_HASH=""
COMMIT_HASH=$(echo "$TOOL_OUTPUT" | grep -oE '\b[0-9a-f]{7,40}\b' | head -1)

# If no hash found, try the bracketed format: [branch hash]
if [ -z "$COMMIT_HASH" ]; then
    COMMIT_HASH=$(echo "$TOOL_OUTPUT" | grep -oE '\[.+ [0-9a-f]{7,}\]' | grep -oE '[0-9a-f]{7,}' | head -1)
fi

[ -z "$COMMIT_HASH" ] && exit 0

# --- Verify commit exists ---
if ! git -C "$PROJECT_DIR" cat-file -t "$COMMIT_HASH" >/dev/null 2>&1; then
    exit 0
fi

# --- Check for ADR-only changes (avoid recursive detection) ---
CHANGED_FILES=$(git -C "$PROJECT_DIR" diff-tree --no-commit-id -r --name-only "$COMMIT_HASH" 2>/dev/null)
NON_ADR_FILES=$(echo "$CHANGED_FILES" | grep -v '^docs/architecture/adrs/' || true)
if [ -z "$NON_ADR_FILES" ]; then
    exit 0
fi

# --- Run the Python analyzer ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/../lib"

# Resolve symlinks for worktree compatibility
if [ -L "$LIB_DIR/adr_detector.py" ]; then
    LIB_DIR=$(readlink -f "$LIB_DIR")
fi

RESULT=$(timeout 30 python3 -c "
import json, sys
sys.path.insert(0, '$(dirname "$LIB_DIR")')
from lib.adr_detector import analyze_commit, generate_adr_draft, log_detection

result = analyze_commit('$COMMIT_HASH', '$PROJECT_DIR')
adr_path = None

if result['triggered']:
    adr_path = generate_adr_draft('$COMMIT_HASH', result['signals'], '$PROJECT_DIR')

log_detection(result, adr_path, '$PROJECT_DIR')

print(json.dumps({'triggered': result['triggered'], 'score': result['total_score'], 'adr_path': adr_path}))
" 2>/dev/null) || exit 0

# --- Update rate limit counter if ADR was generated ---
TRIGGERED=$(echo "$RESULT" | jq -r '.triggered // false' 2>/dev/null)
if [ "$TRIGGERED" = "true" ]; then
    NEW_COUNT=$((SESSION_COUNT + 1))
    echo "$NEW_COUNT" > "$RATE_LIMIT_FILE"

    ADR_PATH=$(echo "$RESULT" | jq -r '.adr_path // empty' 2>/dev/null)
    SCORE=$(echo "$RESULT" | jq -r '.score // 0' 2>/dev/null)

    # Emit a notice for the AI agent
    echo "---"
    echo "ADR_NOTICE: Auto-detected architecturally significant commit."
    echo "  Score: $SCORE (threshold: 0.70)"
    echo "  Draft ADR written to: $ADR_PATH"
    echo "  Status: Draft — requires human review."
    echo "---"
fi

exit 0
