#!/usr/bin/env bash
# SessionStart hook: MCP-Scan — MCP Server Configuration Scanner
# Scans .claude/settings.json MCP server definitions for tool poisoning and injection
# Advisory only (exit 0) — never blocks session start
# Requires: mcp-scan (pip install mcp-scan or npx @invariantlabs/mcp-scan)
#
# PURPOSE: Detects tool poisoning, prompt injection, and cross-origin violations
# in MCP server configurations. Runs at session start to catch misconfigurations
# before any MCP tools are invoked.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="mcp-scan"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
FINDINGS_LOG="$METRICS_DIR/mcp-scan-findings.jsonl"

# Check private mode
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Require mcp-scan — graceful degradation if not installed
# Check for both pip-installed and npx-available versions
MCP_SCAN_CMD=""
if command -v mcp-scan &>/dev/null; then
  MCP_SCAN_CMD="mcp-scan"
elif command -v npx &>/dev/null && npx --yes @invariantlabs/mcp-scan --help &>/dev/null 2>&1; then
  MCP_SCAN_CMD="npx --yes @invariantlabs/mcp-scan"
else
  exit 0
fi

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Find MCP settings files to scan
SETTINGS_FILES=""
for candidate in \
  "$PROJECT_DIR/.claude/settings.json" \
  "$PROJECT_DIR/.claude/settings.local.json" \
  "$HOME/.claude/settings.json" \
  "$HOME/.claude/settings.local.json"; do
  if [ -f "$candidate" ]; then
    # Check if file actually has mcpServers section
    if jq -e '.mcpServers // empty' "$candidate" &>/dev/null; then
      SETTINGS_FILES="$SETTINGS_FILES $candidate"
    fi
  fi
done

if [ -z "$SETTINGS_FILES" ]; then
  exit 0
fi

# --- Run MCP-Scan ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mkdir -p "$METRICS_DIR" 2>/dev/null

TOTAL_FINDINGS=0
HAS_OUTPUT=false

for settings_file in $SETTINGS_FILES; do
  SCAN_OUTPUT=$($MCP_SCAN_CMD scan --json "$settings_file" 2>/dev/null) || true

  if [ -z "$SCAN_OUTPUT" ]; then
    continue
  fi

  # Extract findings count
  FILE_FINDINGS=$(echo "$SCAN_OUTPUT" | jq '.findings // .results // .issues // [] | length' 2>/dev/null || echo "0")

  if [ "$FILE_FINDINGS" -eq 0 ]; then
    continue
  fi

  TOTAL_FINDINGS=$((TOTAL_FINDINGS + FILE_FINDINGS))

  if [ "$HAS_OUTPUT" = false ]; then
    echo ""
    echo "=== MCP-SCAN: MCP Server Configuration Scan ==="
    echo ""
    HAS_OUTPUT=true
  fi

  echo "File: $settings_file ($FILE_FINDINGS finding(s))"
  echo ""

  # Process each finding
  echo "$SCAN_OUTPUT" | jq -c '(.findings // .results // .issues // [])[]' 2>/dev/null | while IFS= read -r finding; do
    SEVERITY=$(echo "$finding" | jq -r '.severity // .level // .risk // "INFO"' | tr '[:lower:]' '[:upper:]')
    TOOL_NAME=$(echo "$finding" | jq -r '.tool // .server // .name // "unknown"')
    MESSAGE=$(echo "$finding" | jq -r '.message // .description // "No description"' | head -c 300)
    CATEGORY=$(echo "$finding" | jq -r '.category // .type // "unknown"')

    # Map severity to adversarial review format
    case "$SEVERITY" in
      CRITICAL|ERROR|HIGH)
        TIER="BLOCKER"
        ;;
      WARNING|MEDIUM)
        TIER="CONCERN"
        ;;
      *)
        TIER="SUGGESTION"
        ;;
    esac

    echo "### [$TIER] $TOOL_NAME"
    echo ""
    echo "**Category**: $CATEGORY"
    echo "**What**: $MESSAGE"
    echo "**Severity**: $SEVERITY"
    echo ""

    # Log each finding to JSONL
    ENTRY=$(jq -c -n \
      --arg ts "$TIMESTAMP" \
      --arg tier "$TIER" \
      --arg tool "$TOOL_NAME" \
      --arg message "$(echo "$MESSAGE" | head -c 300)" \
      --arg category "$CATEGORY" \
      --arg severity "$SEVERITY" \
      --arg file "$settings_file" \
      '{timestamp: $ts, tier: $tier, tool: $tool, message: $message, category: $category, severity: $severity, file: $file}')
    safe_jsonl_append "$FINDINGS_LOG" "$ENTRY"
  done
done

if [ "$HAS_OUTPUT" = true ]; then
  echo "---"
  echo "Total: $TOTAL_FINDINGS finding(s) across MCP server configurations"
  echo "Action: Review MCP server definitions and address findings"
  echo ""
  echo "=== END MCP-SCAN ==="
  echo ""
fi

# Advisory only — never block session start
exit 0
