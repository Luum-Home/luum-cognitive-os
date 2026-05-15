#!/usr/bin/env bash
# SCOPE: both
# @on-demand: invoked via /semgrep-scan skill; not a global default hook
# PostToolUse hook: Semgrep SAST Scanner
# Fires on "Agent" tool use — runs Semgrep on changed files after sdd-apply
# Advisory only (exit 0) — reports findings but does not block
# OFF by default — set SEMGREP_ENABLED=true to activate
#
# PURPOSE: Adds static analysis security testing (SAST) to the SDD pipeline.
# After sdd-apply produces code changes, Semgrep scans for security issues
# and reports findings using the adversarial review format (BLOCKER/CONCERN/SUGGESTION).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="semgrep-scan"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"
# Runtime disable: DISABLE_HOOK_SEMGREP_SCAN=true skips this hook for the session
check_disabled_env "semgrep-scan"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
FINDINGS_LOG="$METRICS_DIR/semgrep-findings.jsonl"

# --- Feature gate: OFF by default ---
if [ "${SEMGREP_ENABLED:-false}" != "true" ]; then
  exit 0
fi

# Check private mode
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Require semgrep — graceful degradation if not installed
if ! command -v semgrep &>/dev/null; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Read stdin (JSON with tool_name, tool_result)
INPUT=$(cat)

# Only process Agent tool results
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# Get agent output
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .tool_response // .output // empty' 2>/dev/null)
if [ -z "$AGENT_OUTPUT" ]; then
  exit 0
fi

# Only fire after sdd-apply completes
if ! echo "$AGENT_OUTPUT" | grep -qiE '(sdd-apply|sdd.apply|apply.*(phase|complete|finished))'; then
  exit 0
fi

# --- Determine scan scope ---
# Get list of changed files from git
CHANGED_FILES=$(cd "$PROJECT_DIR" && git diff --name-only HEAD 2>/dev/null | head -50)
if [ -z "$CHANGED_FILES" ]; then
  # Try staged files
  CHANGED_FILES=$(cd "$PROJECT_DIR" && git diff --cached --name-only 2>/dev/null | head -50)
fi
if [ -z "$CHANGED_FILES" ]; then
  # Try untracked files
  CHANGED_FILES=$(cd "$PROJECT_DIR" && git ls-files --others --exclude-standard 2>/dev/null | head -50)
fi

if [ -z "$CHANGED_FILES" ]; then
  exit 0
fi

# Filter to source code files only
SCAN_FILES=""
while IFS= read -r file; do
  case "$file" in
    *.go|*.ts|*.js|*.py|*.java|*.rb|*.rs|*.c|*.cpp|*.cs)
      if [ -f "$PROJECT_DIR/$file" ]; then
        SCAN_FILES="$SCAN_FILES $PROJECT_DIR/$file"
      fi
      ;;
  esac
done <<< "$CHANGED_FILES"

if [ -z "$SCAN_FILES" ]; then
  exit 0
fi

# --- Run Semgrep ---
SEMGREP_OUTPUT=$(semgrep scan --config auto --config p/ai-best-practices --json $SCAN_FILES 2>/dev/null) || true

if [ -z "$SEMGREP_OUTPUT" ]; then
  exit 0
fi

# --- Parse results ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

TOTAL_FINDINGS=$(echo "$SEMGREP_OUTPUT" | jq '.results | length' 2>/dev/null || echo "0")

if [ "$TOTAL_FINDINGS" -eq 0 ]; then
  exit 0
fi

# Classify and output findings
BLOCKERS=0
CONCERNS=0
SUGGESTIONS=0

echo ""
echo "=== SEMGREP SAST SCAN: $TOTAL_FINDINGS finding(s) ==="
echo ""

echo "$SEMGREP_OUTPUT" | jq -c '.results[]' 2>/dev/null | while IFS= read -r finding; do
  SEVERITY=$(echo "$finding" | jq -r '.extra.severity // "INFO"')
  CHECK_ID=$(echo "$finding" | jq -r '.check_id // "unknown"')
  MESSAGE=$(echo "$finding" | jq -r '.extra.message // "No message"' | head -c 200)
  FILE_PATH=$(echo "$finding" | jq -r '.path // "unknown"')
  LINE=$(echo "$finding" | jq -r '.start.line // 0')

  # Map Semgrep severity to adversarial review format
  case "$SEVERITY" in
    ERROR)
      TIER="BLOCKER"
      ;;
    WARNING)
      TIER="CONCERN"
      ;;
    *)
      TIER="SUGGESTION"
      ;;
  esac

  echo "### [$TIER] $CHECK_ID"
  echo ""
  echo "**Location**: $FILE_PATH:$LINE"
  echo "**What**: $MESSAGE"
  echo "**Severity**: $SEVERITY"
  echo ""

  # Log each finding to JSONL
  ENTRY=$(jq -c -n \
    --arg ts "$TIMESTAMP" \
    --arg tier "$TIER" \
    --arg check_id "$CHECK_ID" \
    --arg message "$(echo "$MESSAGE" | head -c 200)" \
    --arg file "$FILE_PATH" \
    --argjson line "$LINE" \
    --arg severity "$SEVERITY" \
    '{timestamp: $ts, tier: $tier, check_id: $check_id, message: $message, file: $file, line: $line, severity: $severity}')
  safe_jsonl_append "$FINDINGS_LOG" "$ENTRY"
done

# Count by tier
BLOCKERS=$(echo "$SEMGREP_OUTPUT" | jq '[.results[] | select(.extra.severity == "ERROR")] | length' 2>/dev/null || echo "0")
CONCERNS=$(echo "$SEMGREP_OUTPUT" | jq '[.results[] | select(.extra.severity == "WARNING")] | length' 2>/dev/null || echo "0")
SUGGESTIONS=$(echo "$SEMGREP_OUTPUT" | jq '[.results[] | select(.extra.severity != "ERROR" and .extra.severity != "WARNING")] | length' 2>/dev/null || echo "0")

echo "---"
echo "Summary: $BLOCKERS BLOCKER(s), $CONCERNS CONCERN(s), $SUGGESTIONS SUGGESTION(s)"

if [ "$BLOCKERS" -gt 0 ]; then
  echo ""
  echo "ORCHESTRATOR ACTION REQUIRED: $BLOCKERS BLOCKER-level security finding(s) detected."
  echo "Review and address before proceeding."
fi

echo ""
echo "=== END SEMGREP SCAN ==="
echo ""

exit 0
