#!/usr/bin/env bash
# SCOPE: project
# confidentiality-enforcer.sh — PostToolUse hook on Edit|Write
# CONCERNS: confidentiality, ip-protection
#
# Scans file writes for confidentiality violations:
# - References to external project paths
# - Attribution phrases mentioning internal projects
# - Protected terms from confidentiality.yaml
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

# Skip if file does not exist
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

# Load confidentiality config
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/confidentiality.yaml"

# SHA-256 cache: skip files that haven't changed since last scan
# Invalidate when confidentiality.yaml changes (config changed)
_CONF_RULES_HASH=$(shasum -a 256 "$CONFIG_FILE" 2>/dev/null | cut -d' ' -f1 || echo "none")
if cache_hit "$FILE_PATH" "$_CONF_RULES_HASH"; then
    exit 0
fi

# Run the Python scanner
PYTHON_OUTPUT=$(python3 - "$FILE_PATH" "$PROJECT_DIR" "$CONFIG_FILE" <<'PYEOF' 2>&1
import json, sys
from lib.confidentiality_scanner import scan_file, load_protected_terms, is_scannable_path

file_path = sys.argv[1]
project_dir = sys.argv[2]
config_path = sys.argv[3]

if not is_scannable_path(file_path):
    sys.exit(0)

terms = load_protected_terms(config_path)
violations = scan_file(file_path, project_dir, terms)

if violations:
    for v in violations:
        print(json.dumps({"line": v.line_number, "text": v.matched_text, "type": v.pattern_type}))
    sys.exit(1)
sys.exit(0)
PYEOF
)
PYTHON_EXIT=$?

if [ $PYTHON_EXIT -eq 1 ]; then
    echo "CONFIDENTIALITY VIOLATION: prohibited content found in $FILE_PATH" >&2
    echo "$PYTHON_OUTPUT" | while IFS= read -r line; do
        if [ -n "$line" ]; then
            VTYPE=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('type','?'))" 2>/dev/null || echo "?")
            VTEXT=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('text','?'))" 2>/dev/null || echo "?")
            VLINE=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('line',0))" 2>/dev/null || echo "0")
            echo "  Line $VLINE [$VTYPE]: $VTEXT" >&2
        fi
    done

    # Count violations
    VIOLATION_COUNT=$(echo "$PYTHON_OUTPUT" | grep -c '{' 2>/dev/null || echo "1")

    # Log to metrics
    METRICS_DIR="${COGNITIVE_OS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
    mkdir -p "$METRICS_DIR"
    echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"file\":\"$FILE_PATH\",\"violations\":$VIOLATION_COUNT}" >> "$METRICS_DIR/confidentiality-enforcer.jsonl"

    exit 2  # BLOCK
fi

# Update cache — file passed confidentiality scan
cache_update "$FILE_PATH" "$_CONF_RULES_HASH"

exit 0
