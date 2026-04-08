#!/usr/bin/env bash
# PostToolUse hook: Error Learning
# Fires on "Bash" tool use — captures failures to error-learning.jsonl.
# Classifies errors, deduplicates within 60s, and appends to JSONL.

set -uo pipefail

_HOOK_NAME="error-learning"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

EXIT_CODE=$(stdin_field '.tool_response.exit_code' '0')
COMMAND=$(stdin_field '.tool_input.command' '')
STDOUT=$(stdin_field '.tool_response.stdout' '')
STDERR=$(stdin_field '.tool_response.stderr' '')

# Only process failures
[ "$EXIT_CODE" = "0" ] || [ "$EXIT_CODE" = "" ] && exit 0
[ "$EXIT_CODE" = "null" ] && exit 0

COMBINED="$STDOUT $STDERR"

# Classify error type
ERROR_TYPE="UNKNOWN_ERROR"
if echo "$COMMAND" | grep -qE '(jest|vitest|go test|gradlew test|pytest|yarn test|npm test)' || \
   echo "$COMBINED" | grep -qiE '(FAILED|failing|assertion error|test.*fail)'; then
  ERROR_TYPE="TEST_FAILURE"
elif echo "$COMMAND" | grep -qE '(eslint|golangci-lint|tsc --noEmit|go vet)' || \
     echo "$COMBINED" | grep -qiE '(lint error|vet:)'; then
  ERROR_TYPE="LINT_ERROR"
elif echo "$COMBINED" | grep -qiE '(syntax error|unexpected token|cannot find|undefined:)'; then
  ERROR_TYPE="COMPILATION_ERROR"
elif echo "$COMMAND" | grep -qE '(go build|gradlew build|yarn build|npm run build|tsc)'; then
  ERROR_TYPE="BUILD_ERROR"
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
