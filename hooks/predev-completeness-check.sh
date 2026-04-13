#!/usr/bin/env bash
# SCOPE: project
# predev-completeness-check.sh — PreToolUse hook on Agent
# CONCERNS: pre-development, readiness, completeness
#
# Before launching implementation agents, verify pre-dev artifacts exist.
# Only triggers for implementation-related prompts.
#
# Exit codes:
#   0 — artifacts present or prompt is not implementation-related
#   2 — critical artifacts missing (production/maintenance phase only)
set -uo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

# Only check on Agent tool
if [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
fi

PROMPT=$(echo "$INPUT" | jq -r '.tool_input.prompt // ""')
if [ -z "$PROMPT" ]; then
    exit 0
fi

# Check if prompt is implementation-related (case-insensitive)
IMPL_MATCH=$(echo "$PROMPT" | grep -iE "sdd-apply|implement|write code|build the|create the endpoint|add the feature" || true)
if [ -z "$IMPL_MATCH" ]; then
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

# Read phase from cognitive-os.yaml (grep for 'phase:')
PHASE="reconstruction"
YAML_FILE="$PROJECT_DIR/cognitive-os.yaml"
if [ -f "$YAML_FILE" ]; then
    PHASE_LINE=$(grep -m1 'phase:' "$YAML_FILE" 2>/dev/null || true)
    if [ -n "$PHASE_LINE" ]; then
        PHASE=$(echo "$PHASE_LINE" | sed 's/.*phase:[[:space:]]*//' | tr -d '"' | tr -d "'" | tr -d ' ')
    fi
fi

# Run the Python completeness checker
PYTHON_OUTPUT=$(python3 - "$PROJECT_DIR" <<'PYEOF' 2>&1
import sys
sys.path.insert(0, '.')
from lib.completeness_checker import check_predev_artifacts, format_report

project_dir = sys.argv[1]
report = check_predev_artifacts(project_dir)
print(f"VERDICT:{report.verdict}")
print(format_report(report))
PYEOF
)
PYTHON_EXIT=$?

VERDICT=$(echo "$PYTHON_OUTPUT" | grep -m1 '^VERDICT:' | sed 's/^VERDICT://')

if [ "$VERDICT" = "READY" ]; then
    exit 0
fi

# NOT_READY or PARTIAL
REPORT=$(echo "$PYTHON_OUTPUT" | grep -v '^VERDICT:')

case "$PHASE" in
    production|maintenance)
        echo "PREDEV COMPLETENESS: BLOCK — implementation cannot proceed without required artifacts." >&2
        echo "Phase: $PHASE | Verdict: $VERDICT" >&2
        echo "" >&2
        echo "$REPORT" >&2

        # Log to metrics
        METRICS_DIR="${COGNITIVE_OS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
        mkdir -p "$METRICS_DIR"
        echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"phase\":\"$PHASE\",\"verdict\":\"$VERDICT\",\"action\":\"block\"}" >> "$METRICS_DIR/predev-completeness.jsonl"

        exit 2  # BLOCK
        ;;
    *)
        # reconstruction / stabilization — warn only
        echo "PREDEV COMPLETENESS WARNING: Artifacts incomplete (verdict: $VERDICT). Phase: $PHASE allows proceeding." >&2
        echo "" >&2
        echo "$REPORT" >&2

        # Log to metrics
        METRICS_DIR="${COGNITIVE_OS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
        mkdir -p "$METRICS_DIR"
        echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"phase\":\"$PHASE\",\"verdict\":\"$VERDICT\",\"action\":\"warn\"}" >> "$METRICS_DIR/predev-completeness.jsonl"

        exit 0  # WARN but pass
        ;;
esac
