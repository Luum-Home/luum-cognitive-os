#!/usr/bin/env bash
# SCOPE: os-only
# agnix-lint.sh — PostToolUse hook on Edit|Write
# CONCERNS: quality, linting, agent-config
#
# Runs agnix linter on modified agent configuration files (.claude/, rules/,
# skills/, agents/). Gracefully skips if agnix is not installed.
#
# Exit codes:
#   0 — no issues or advisory warning (reconstruction/stabilization)
#   2 — errors found (BLOCK in production/maintenance)
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="agnix-lint"
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

# --- Capability level check ---
check_capability_level "agnix-lint"

# --- Private mode check ---
check_private_mode

# --- Read stdin and gate on tool type ---
read_stdin_json
require_tool "Edit" "Write"

# --- Extract file path ---
FILE_PATH=$(stdin_field '.tool_input.file_path // .tool_input.filePath // empty')
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# --- Only trigger on agent config files ---
# Match .claude/, rules/, skills/, agents/ paths
case "$FILE_PATH" in
  */.claude/*|*/rules/*|*/skills/*|*/agents/*)
    ;;
  *)
    exit 0
    ;;
esac

# --- Graceful degradation: skip if agnix not installed ---
if ! command -v agnix &>/dev/null; then
  exit 0
fi

# --- Require jq ---
if ! command -v jq &>/dev/null; then
  exit 0
fi

# --- Verify file exists ---
if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# --- Resolve project dir and config ---
PROJECT_DIR="$_PROJECT_DIR"
AGNIX_CONFIG="$PROJECT_DIR/.agnix.toml"
METRICS_DIR="$(_resolve_metrics_dir)"
AGNIX_LOG="$METRICS_DIR/agnix-findings.jsonl"

# --- Run agnix ---
AGNIX_OUTPUT=""
if [ -f "$AGNIX_CONFIG" ]; then
  AGNIX_OUTPUT=$(agnix --format json "$FILE_PATH" 2>/dev/null) || true
else
  AGNIX_OUTPUT=$(agnix --format json "$FILE_PATH" 2>/dev/null) || true
fi

if [ -z "$AGNIX_OUTPUT" ]; then
  exit 0
fi

# --- Parse results ---
TOTAL_FINDINGS=$(echo "$AGNIX_OUTPUT" | jq 'if type == "array" then length else (.results // .findings // []) | length end' 2>/dev/null || echo "0")

if [ "$TOTAL_FINDINGS" -eq 0 ] || [ "$TOTAL_FINDINGS" = "0" ]; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

# --- Classify findings ---
ERRORS=0
WARNINGS=0

# Try to count errors/warnings from the JSON output
ERRORS=$(echo "$AGNIX_OUTPUT" | jq '[if type == "array" then .[] else (.results // .findings // [])[] end | select(.severity == "error" or .level == "error")] | length' 2>/dev/null || echo "0")
WARNINGS=$(echo "$AGNIX_OUTPUT" | jq '[if type == "array" then .[] else (.results // .findings // [])[] end | select(.severity == "warning" or .level == "warning")] | length' 2>/dev/null || echo "0")

# --- Output findings ---
echo "" >&2
echo "=== AGNIX LINT: $TOTAL_FINDINGS finding(s) in $(basename "$FILE_PATH") ===" >&2
echo "  Errors: $ERRORS | Warnings: $WARNINGS" >&2

# Log each finding summary
echo "$AGNIX_OUTPUT" | jq -c 'if type == "array" then .[] else (.results // .findings // [])[] end' 2>/dev/null | head -20 | while IFS= read -r finding; do
  RULE=$(echo "$finding" | jq -r '.rule // .check_id // .code // "unknown"' 2>/dev/null)
  MSG=$(echo "$finding" | jq -r '.message // .description // "No message"' 2>/dev/null | head -c 200)
  SEV=$(echo "$finding" | jq -r '.severity // .level // "info"' 2>/dev/null)
  LINE=$(echo "$finding" | jq -r '.line // .start_line // 0' 2>/dev/null)

  echo "  [$SEV] $RULE (line $LINE): $MSG" >&2

  # Log to JSONL
  ENTRY=$(jq -c -n \
    --arg ts "$TIMESTAMP" \
    --arg rule "$RULE" \
    --arg message "$(echo "$MSG" | head -c 200)" \
    --arg file "$FILE_PATH" \
    --argjson line "${LINE:-0}" \
    --arg severity "$SEV" \
    '{timestamp: $ts, rule: $rule, message: $message, file: $file, line: $line, severity: $severity}')
  safe_jsonl_append "$AGNIX_LOG" "$ENTRY"
done

echo "=== END AGNIX LINT ===" >&2
echo "" >&2

# --- Phase-aware exit code ---
PHASE=$(get_phase "reconstruction")

if [ "$ERRORS" -gt 0 ]; then
  case "$PHASE" in
    production|maintenance)
      echo "AGNIX LINT: BLOCKING — $ERRORS error(s) in production/maintenance phase." >&2
      exit 2
      ;;
    *)
      echo "AGNIX LINT: WARNING — $ERRORS error(s) found (advisory in $PHASE phase)." >&2
      exit 0
      ;;
  esac
fi

exit 0
