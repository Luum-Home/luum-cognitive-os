#!/usr/bin/env bash
# SCOPE: project
# content-policy.sh — PostToolUse hook on Edit|Write
# CONCERNS: compliance, content-policy, quality
#
# Scans every file modification for prohibited terms and patterns
# defined in .cognitive-os/content-policy.yaml.
#
# Exit codes:
#   0 — no violations
#   2 — violations found (BLOCK)
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/cache.sh"

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

# Only check on Edit and Write
case "$TOOL_NAME" in
    Edit|Write) ;;
    *) exit 0 ;;
esac

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // ""')
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Skip if file does not exist (Write may not have completed yet)
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Determine project dir
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
elif [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$COGNITIVE_OS_PROJECT_DIR"
else
    PROJECT_DIR="."
fi

# Load content policy
POLICY_FILE="$PROJECT_DIR/.cognitive-os/content-policy.yaml"
if [ ! -f "$POLICY_FILE" ]; then
    exit 0
fi

# SHA-256 cache: skip files that haven't changed since last scan
# Invalidate when content-policy.yaml changes (rules changed)
_CP_RULES_HASH=$(shasum -a 256 "$POLICY_FILE" 2>/dev/null | cut -d' ' -f1 || echo "none")
if cache_hit "$FILE_PATH" "$_CP_RULES_HASH"; then
    exit 0
fi

VIOLATIONS=0
VIOLATION_DETAILS=""

# Extract prohibited terms from YAML (bash 3.x compatible)
# Parse lines matching "  - term:" and extract the value
TERMS=""
while IFS= read -r line; do
    # Match lines like '  - term: "something"' or "  - term: 'something'" or '  - term: something'
    term_val=$(echo "$line" | sed -n 's/^[[:space:]]*- term:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/p')
    if [ -z "$term_val" ]; then
        term_val=$(echo "$line" | sed -n "s/^[[:space:]]*- term:[[:space:]]*'\{0,1\}\([^']*\)'\{0,1\}[[:space:]]*$/\1/p")
    fi
    if [ -n "$term_val" ]; then
        TERMS="$TERMS
$term_val"
    fi
done < "$POLICY_FILE"

# Check each prohibited term
echo "$TERMS" | while IFS= read -r term; do
    if [ -z "$term" ]; then
        continue
    fi
    if grep -qi "$term" "$FILE_PATH" 2>/dev/null; then
        # Get the reason from the next line in the policy
        reason=$(grep -A1 "term:.*$term" "$POLICY_FILE" 2>/dev/null | grep "reason:" | head -1 | sed 's/.*reason:[[:space:]]*//' | tr -d '"' | tr -d "'")
        echo "CONTENT POLICY VIOLATION: '$term' found in $FILE_PATH" >&2
        echo "  Reason: $reason" >&2
        # Signal violation via temp file (subshell workaround)
        echo "1" >> "/tmp/content-policy-violations-$$"
    fi
done

# Extract prohibited patterns from YAML
while IFS= read -r line; do
    pattern_val=$(echo "$line" | sed -n 's/^[[:space:]]*- pattern:[[:space:]]*"\([^"]*\)"[[:space:]]*$/\1/p')
    if [ -z "$pattern_val" ]; then
        pattern_val=$(echo "$line" | sed -n "s/^[[:space:]]*- pattern:[[:space:]]*'\([^']*\)'[[:space:]]*$/\1/p")
    fi
    if [ -n "$pattern_val" ]; then
        if grep -qiE "$pattern_val" "$FILE_PATH" 2>/dev/null; then
            reason=$(grep -A1 "pattern:.*$(echo "$pattern_val" | head -c 30)" "$POLICY_FILE" 2>/dev/null | grep "reason:" | head -1 | sed 's/.*reason:[[:space:]]*//' | tr -d '"' | tr -d "'")
            echo "CONTENT POLICY VIOLATION: pattern '$pattern_val' matched in $FILE_PATH" >&2
            echo "  Reason: $reason" >&2
            echo "1" >> "/tmp/content-policy-violations-$$"
        fi
    fi
done < "$POLICY_FILE"

# Count violations from temp file
if [ -f "/tmp/content-policy-violations-$$" ]; then
    VIOLATIONS=$(wc -l < "/tmp/content-policy-violations-$$" | tr -d ' ')
    rm -f "/tmp/content-policy-violations-$$"
fi

if [ "$VIOLATIONS" -gt 0 ]; then
    echo "CONTENT POLICY: $VIOLATIONS violation(s) in $FILE_PATH" >&2

    # Log to metrics
    METRICS_DIR="${COGNITIVE_OS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
    mkdir -p "$METRICS_DIR"
    echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"file\":\"$FILE_PATH\",\"violations\":$VIOLATIONS}" >> "$METRICS_DIR/content-policy.jsonl"

    exit 2  # BLOCK
fi

# Update cache — file passed content policy scan
cache_update "$FILE_PATH" "$_CP_RULES_HASH"

exit 0
