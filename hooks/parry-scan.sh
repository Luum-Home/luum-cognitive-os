#!/usr/bin/env bash
# PreToolUse hook: Parry Prompt Injection Scanner
# Fires on "Agent" tool use — scans agent prompts for prompt injection attempts.
# Requires parry-guard to be installed. Gracefully skips if not found.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="parry-scan"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode

# Graceful skip if parry-guard not installed
if ! command -v parry-guard >/dev/null 2>&1; then
  exit 0
fi

# Check if parry is enabled in config
CONFIG_FILE="$_PROJECT_DIR/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$_PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
if [ -f "$CONFIG_FILE" ]; then
  PARRY_ENABLED=$(grep -A2 'parry:' "$CONFIG_FILE" 2>/dev/null | grep 'enabled:' | head -1 \
    | sed 's/.*enabled:[[:space:]]*//' | tr -d '[:space:]' || true)
  [ "$PARRY_ENABLED" = "false" ] && exit 0
fi

read_stdin_json
PROMPT=$(stdin_field '.tool_input.prompt' '')

[ -z "$PROMPT" ] && exit 0

METRICS_DIR=$(_resolve_metrics_dir)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Run parry-guard scan
SCAN_RESULT=$(echo "$PROMPT" | parry-guard hook 2>&1)
SCAN_EXIT=$?

if [ "$SCAN_EXIT" -ne 0 ]; then
  # Injection detected
  safe_jsonl_append "$METRICS_DIR/parry-findings.jsonl" \
    "{\"timestamp\":\"$TIMESTAMP\",\"tier\":\"BLOCKER\",\"message\":\"Prompt injection detected by parry-guard\",\"result\":$(echo "${SCAN_RESULT:0:200}" | jq -Rs '.')}"
  echo "PARRY: Prompt injection detected. Agent launch blocked." >&2
  echo "$SCAN_RESULT" >&2
  exit 2
fi

# Clean scan — log for audit
safe_jsonl_append "$METRICS_DIR/parry-findings.jsonl" \
  "{\"timestamp\":\"$TIMESTAMP\",\"tier\":\"CLEAN\",\"message\":\"No injection detected\"}"

exit 0
