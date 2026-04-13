#!/usr/bin/env bash
# SCOPE: both
# PostToolUse hook: Verify that files agents claim to have created actually exist
# Fires on Agent completion. Advisory only (exit 0 always).
set -uo pipefail

# Read stdin
INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
OUTPUT=$(echo "$INPUT" | jq -r '.tool_output.result // .tool_output // empty' 2>/dev/null)
[ -z "$OUTPUT" ] && exit 0

# Extract file paths from common patterns in agent output:
# - "File created at /path/to/file"
# - "File written to /path/to/file"
# - "Created /path/to/file"
# - "Wrote /path/to/file"
# - "`/path/to/file`" (backtick-quoted absolute paths)
# - "'/path/to/file'" (single-quoted absolute paths)
CLAIMED_FILES=$(echo "$OUTPUT" \
    | grep -oE '(File (created|written) (at|to)|Created|Wrote) [`'"'"'"]?(/[^ `'"'"'"]+)' \
    | grep -oE '/[^ `'"'"'"]+' \
    | sed 's/[`'"'"'"]//g' \
    | sort -u)

# Also check for Write tool call results that mention file_path
WRITE_FILES=$(echo "$OUTPUT" \
    | grep -oE '"file_path"\s*:\s*"(/[^"]+)"' \
    | grep -oE '/[^"]+' \
    | sort -u)

ALL_FILES=$(printf '%s\n%s\n' "$CLAIMED_FILES" "$WRITE_FILES" \
    | sort -u \
    | grep -v '^$' \
    | grep -v '\*' \
    | grep -v '\.\.' \
    || true)

[ -z "$ALL_FILES" ] && exit 0

# Verify each claimed file exists
MISSING=0
VERIFIED=0
MISSING_LIST=""

while IFS= read -r filepath; do
    [ -z "$filepath" ] && continue
    if [ -f "$filepath" ]; then
        VERIFIED=$((VERIFIED + 1))
    else
        MISSING=$((MISSING + 1))
        MISSING_LIST="$MISSING_LIST\n  - $filepath"
    fi
done <<< "$ALL_FILES"

TOTAL=$((VERIFIED + MISSING))

# Log results
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$METRICS_DIR"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if command -v jq &>/dev/null; then
    jq -c -n \
        --arg ts "$TIMESTAMP" \
        --argjson verified "$VERIFIED" \
        --argjson missing "$MISSING" \
        --argjson total "$TOTAL" \
        '{timestamp: $ts, verified: $verified, missing: $missing, total: $total}' \
        >> "$METRICS_DIR/agent-verification.jsonl" 2>/dev/null || true
fi

# Warn if files are missing
if [ "$MISSING" -gt 0 ]; then
    echo "" >&2
    echo "=== AGENT OUTPUT VERIFICATION WARNING ===" >&2
    echo "Agent claimed to create/modify $TOTAL files." >&2
    echo "Verified: $VERIFIED | MISSING: $MISSING" >&2
    printf "Missing files:%b\n" "$MISSING_LIST" >&2
    echo "" >&2
    echo "The agent may have failed silently. Re-run the task or" >&2
    echo "verify manually with: ls -la <path>" >&2
    echo "=== END VERIFICATION ===" >&2
fi

exit 0
