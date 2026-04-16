#!/usr/bin/env bash
# PreToolUse hook: Reinvention Check
# Fires on "Agent" tool use — warns if agent may be recreating existing implementations.
# Advisory only (exit 0 always).

set -uo pipefail

_HOOK_NAME="reinvention-check"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

PROMPT=$(stdin_field '.tool_input.prompt' '')

[ -z "$PROMPT" ] && exit 0

# Only fire if prompt contains creation intent + file-type targets
if ! echo "$PROMPT" | grep -qiE '(create|implement|write|add)'; then
  exit 0
fi
if ! echo "$PROMPT" | grep -qE '(lib/|hooks/|new file|new hook|new script)'; then
  exit 0
fi

# Extract the thing being created
TARGET=$(echo "$PROMPT" | grep -oE '[a-z][a-z0-9_-]+\.(sh|py|go|ts|js)' | head -3 | tr '\n' ' ' || true)
[ -z "$TARGET" ] && TARGET=$(echo "$PROMPT" | grep -oE 'lib/[a-z_]+' | head -2 | tr '\n' ' ' || true)

METRICS_DIR=$(_resolve_metrics_dir)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

FOUND_SOURCES=""
PLUGIN_DIRS=(
  "$_PROJECT_DIR/.claude/plugins/hermes-agent"
  "$_PROJECT_DIR/.claude/plugins/pi-mono"
  "$_PROJECT_DIR/lib"
  "$_PROJECT_DIR/hooks"
)

for TARGET_FILE in $TARGET; do
  BASE="${TARGET_FILE%.*}"
  for DIR in "${PLUGIN_DIRS[@]}"; do
    [ -d "$DIR" ] || continue
    MATCH=$(find "$DIR" -type f -name "*${BASE}*" 2>/dev/null | head -2 || true)
    if [ -n "$MATCH" ]; then
      FOUND_SOURCES="$FOUND_SOURCES $MATCH"
    fi
  done
done

if [ -n "$FOUND_SOURCES" ]; then
  echo "REINVENTION CHECK: Similar implementation(s) may already exist:" >&2
  for src in $FOUND_SOURCES; do
    echo "  - $src" >&2
  done
  echo "Consider reusing or extending existing code before creating new files." >&2

  safe_jsonl_append "$METRICS_DIR/reinvention-checks.jsonl" \
    "{\"timestamp\":\"$TIMESTAMP\",\"target\":\"${TARGET// /,}\",\"sources\":$(echo "$FOUND_SOURCES" | jq -Rs '.')}"
fi

exit 0
