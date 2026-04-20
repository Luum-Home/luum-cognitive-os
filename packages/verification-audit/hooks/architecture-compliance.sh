#!/usr/bin/env bash
# PostToolUse hook on Agent — checks agent output for architecture violations in Go files.
# Reads project phase from cognitive-os.yaml and logs violations accordingly.

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="architecture-compliance"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "architecture-compliance"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
COGNITIVE_OS_YAML="$PROJECT_DIR/cognitive-os.yaml"
VIOLATIONS_LOG="$PROJECT_DIR/.cognitive-os/metrics/architecture-violations.jsonl"

# Read agent result from stdin
INPUT=$(cat)

# Extract tool name — only process Agent results
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Get agent output text
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .result // empty' 2>/dev/null)
if [[ -z "$AGENT_OUTPUT" ]]; then
  exit 0
fi

# Read current phase from cognitive-os.yaml
PHASE="reconstruction"
if [[ -f "$COGNITIVE_OS_YAML" ]]; then
  PHASE=$(grep -E '^\s+phase:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*phase:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "reconstruction")
fi

# Extract Go file paths from agent output (created/modified files)
GO_FILES=$(echo "$AGENT_OUTPUT" | grep -oE '[a-zA-Z0-9_/./-]+\.go' | sort -u || true)

if [[ -z "$GO_FILES" ]]; then
  exit 0
fi

VIOLATIONS=""
WARNINGS=""
VIOLATION_COUNT=0
WARNING_COUNT=0
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

while IFS= read -r go_file; do
  [[ -z "$go_file" ]] && continue

  # Check for huma import
  if echo "$AGENT_OUTPUT" | grep -q "danielgtaylor/huma"; then
    VIOLATIONS="${VIOLATIONS}VIOLATION: $go_file uses non-standard framework (huma) instead of the declared framework\n"
    VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
  fi

  # Check for chi import
  if echo "$AGENT_OUTPUT" | grep -q "go-chi/chi"; then
    WARNINGS="${WARNINGS}WARNING: $go_file uses chi directly instead of the declared framework router\n"
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi

  # Check for DTOs in wrong layer
  if echo "$go_file" | grep -q "domain/dtos/"; then
    VIOLATIONS="${VIOLATIONS}VIOLATION: $go_file — DTOs should be in application/dtos/, not domain/dtos/\n"
    VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
  fi

  # Check for missing internal/ prefix
  if echo "$go_file" | grep -qE "^(cmd|pkg)/" || echo "$go_file" | grep -q "internal/"; then
    : # acceptable paths
  elif echo "$go_file" | grep -qE "^[a-z]"; then
    WARNINGS="${WARNINGS}WARNING: $go_file should use internal/ prefix\n"
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi

done <<< "$GO_FILES"

# If violations or warnings found, log and output
if [[ $VIOLATION_COUNT -gt 0 || $WARNING_COUNT -gt 0 ]]; then
  # Ensure metrics directory exists
  mkdir -p "$(dirname "$VIOLATIONS_LOG")"

  # Log to JSONL
  ENTRY=$(jq -c -n \
    --arg timestamp "$TIMESTAMP" \
    --arg phase "$PHASE" \
    --argjson violations "$VIOLATION_COUNT" \
    --argjson warnings "$WARNING_COUNT" \
    --arg details "$(echo -e "${VIOLATIONS}${WARNINGS}")" \
    '{timestamp: $timestamp, phase: $phase, violations: $violations, warnings: $warnings, details: $details}')
  safe_jsonl_append "$VIOLATIONS_LOG" "$ENTRY"

  # Output warning text for orchestrator
  if [[ $VIOLATION_COUNT -gt 0 ]]; then
    echo ""
    echo "=== ARCHITECTURE COMPLIANCE CHECK ==="
    echo "Phase: $PHASE | Violations: $VIOLATION_COUNT | Warnings: $WARNING_COUNT"
    echo ""
    echo -e "$VIOLATIONS"

    if [[ "$PHASE" == "reconstruction" ]]; then
      echo "ACTION REQUIRED: In reconstruction phase, violations are BLOCKERS."
      echo "The agent MUST fix these before the task is considered complete."
    elif [[ "$PHASE" == "stabilization" ]]; then
      echo "ACTION: Create a task to fix these violations."
    else
      echo "INFO: Logged for tracking. No immediate action required."
    fi
  fi

  if [[ $WARNING_COUNT -gt 0 ]]; then
    echo -e "$WARNINGS"
  fi

  echo "=== END COMPLIANCE CHECK ==="
fi

exit 0
