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

is_gitignored_destination() {
    local path="$1"
    local project="$2"
    if ! command -v git >/dev/null 2>&1; then
        return 1
    fi
    if ! git -C "$project" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        return 1
    fi
    local rel_path
    rel_path=$(python3 - "$path" "$project" <<'PYEOF' 2>/dev/null
import os
import sys

path = os.path.abspath(sys.argv[1])
project = os.path.abspath(sys.argv[2])
try:
    print(os.path.relpath(path, project))
except ValueError:
    print(path)
PYEOF
)
    case "$rel_path" in
        ../*|/*) return 1 ;;
    esac
    git -C "$project" check-ignore -q -- "$rel_path"
}

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
    ONLY_OPERATOR_ABSOLUTE_PATHS=$(echo "$PYTHON_OUTPUT" | python3 -c '
import json
import sys

rows = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        print("false")
        raise SystemExit(0)

if rows and all(row.get("type") == "external_path" for row in rows):
    print("true")
else:
    print("false")
')

    if [ "$ONLY_OPERATOR_ABSOLUTE_PATHS" = "true" ] && is_gitignored_destination "$FILE_PATH" "$PROJECT_DIR"; then
        echo "CONFIDENTIALITY WARNING: operator absolute path found in gitignored destination $FILE_PATH" >&2
        echo "$PYTHON_OUTPUT" | while IFS= read -r line; do
            if [ -n "$line" ]; then
                VTYPE=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('type','?'))" 2>/dev/null || echo "?")
                VTEXT=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('text','?'))" 2>/dev/null || echo "?")
                VLINE=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('line',0))" 2>/dev/null || echo "0")
                echo "  Line $VLINE [$VTYPE downgraded-to-warn]: $VTEXT" >&2
            fi
        done

        VIOLATION_COUNT=$(printf '%s\n' "$PYTHON_OUTPUT" | awk '/^\{/ { count++ } END { print count ? count : 1 }')
        METRICS_DIR="${COGNITIVE_OS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
        mkdir -p "$METRICS_DIR"
        echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"file\":\"$FILE_PATH\",\"violations\":$VIOLATION_COUNT,\"action\":\"warn\",\"downgrade_reason\":\"operator_absolute_path_gitignored_destination\"}" >> "$METRICS_DIR/confidentiality-enforcer.jsonl"
        cache_update "$FILE_PATH" "$_CONF_RULES_HASH"
        exit 0
    fi

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
    VIOLATION_COUNT=$(printf '%s\n' "$PYTHON_OUTPUT" | awk '/^\{/ { count++ } END { print count ? count : 1 }')

    # Log to metrics
    METRICS_DIR="${COGNITIVE_OS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
    mkdir -p "$METRICS_DIR"
    echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"file\":\"$FILE_PATH\",\"violations\":$VIOLATION_COUNT}" >> "$METRICS_DIR/confidentiality-enforcer.jsonl"

    exit 2  # BLOCK
fi

# Update cache — file passed confidentiality scan
cache_update "$FILE_PATH" "$_CONF_RULES_HASH"

exit 0
