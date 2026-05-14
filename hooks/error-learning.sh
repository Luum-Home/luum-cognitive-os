#!/usr/bin/env bash
# SCOPE: both
# PostToolUse hook: Error Learning
# Fires on "Bash" tool use — captures failures to error-learning.jsonl.
# Classifies errors, deduplicates within 60s, and appends to JSONL.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="error-learning"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

EXIT_CODE=$(stdin_field '.exit_code' '0')
COMMAND=$(stdin_field '.tool_input.command' '')
# tool_response may be a plain string (stdout) or an object with stdout/stderr fields.
# Use direct jq with type-checking to handle both formats.
STDOUT=$(echo "$_STDIN_JSON" | jq -r 'if (.tool_response | type) == "object" then .tool_response.stdout // "" else .tool_response // "" end' 2>/dev/null || true)
STDERR=$(echo "$_STDIN_JSON" | jq -r 'if (.tool_response | type) == "object" then .tool_response.stderr // "" else "" end' 2>/dev/null || true)

# Only process failures
[ "$EXIT_CODE" = "0" ] || [ "$EXIT_CODE" = "" ] && exit 0
[ "$EXIT_CODE" = "null" ] && exit 0

COMBINED="$STDOUT $STDERR"

# Classify error type — command-based checks run first to avoid false positives.
# Example: "compilation failed" contains "failed" but is a BUILD_ERROR not TEST_FAILURE.
ERROR_TYPE="UNKNOWN_ERROR"
if echo "$COMMAND" | grep -qE '(eslint|golangci-lint|tsc --noEmit|go vet)' || \
   echo "$COMBINED" | grep -qiE '(lint error|vet:)'; then
  ERROR_TYPE="LINT_ERROR"
elif echo "$COMBINED" | grep -qiE '(syntax error|unexpected token|cannot find module|undefined:)'; then
  ERROR_TYPE="COMPILATION_ERROR"
elif echo "$COMMAND" | grep -qE '(go build|gradlew build|yarn build|npm run build|tsc)'; then
  ERROR_TYPE="BUILD_ERROR"
elif echo "$COMMAND" | grep -qE '(jest|vitest|go test|gradlew test|pytest|yarn test|npm test)' || \
   echo "$COMBINED" | grep -qiE '(assertion error|test.*fail|test suite failed)'; then
  ERROR_TYPE="TEST_FAILURE"
fi

# Fingerprint for deduplication (md5 of first 100 chars of error)
ERROR_SNIPPET="${COMBINED:0:100}"
if command -v md5sum >/dev/null 2>&1; then
  FINGERPRINT=$(echo -n "$ERROR_SNIPPET" | md5sum | awk '{print $1}')
elif command -v md5 >/dev/null 2>&1; then
  FINGERPRINT=$(echo -n "$ERROR_SNIPPET" | md5)
else
  FINGERPRINT="nohash"
fi

METRICS_DIR=$(_resolve_metrics_dir)
ERROR_LOG="$METRICS_DIR/error-learning.jsonl"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
NOW_EPOCH=$(date +%s)

# Deduplicate: skip if same fingerprint seen in last 60s
if [ -f "$ERROR_LOG" ]; then
  CUTOFF=$(( NOW_EPOCH - 60 ))
  DUPE=$(grep "\"fingerprint\":\"$FINGERPRINT\"" "$ERROR_LOG" 2>/dev/null | tail -1 || true)
  if [ -n "$DUPE" ]; then
    DUPE_EPOCH=$(echo "$DUPE" | jq -r '.timestamp_epoch // 0' 2>/dev/null || echo 0)
    [ "$DUPE_EPOCH" -gt "$CUTOFF" ] && exit 0
  fi
fi

# Extract service name from command path
SERVICE=$(echo "$COMMAND" | grep -oE 'internal/[a-z_-]+' | head -1 | tr '/' '-' || echo "unknown")

safe_jsonl_append "$ERROR_LOG" \
  "{\"timestamp\":\"$TIMESTAMP\",\"timestamp_epoch\":$NOW_EPOCH,\"type\":\"$ERROR_TYPE\",\"service\":\"$SERVICE\",\"fingerprint\":\"$FINGERPRINT\",\"command\":$(echo "$COMMAND" | jq -Rs '.'),\"exit_code\":$EXIT_CODE}"

exit 0
