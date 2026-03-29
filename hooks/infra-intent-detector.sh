#!/usr/bin/env bash
# PreToolUse hook on Agent — scans agent prompt/task for infrastructure intent keywords.
# Suggests matching infrastructure from cognitive-os.yaml config. Does NOT block.
# Logs detections to .cognitive-os/metrics/infra-detections.jsonl
#
# UNIVERSAL: This hook reads infrastructure from cognitive-os.yaml instead of
# hardcoding project-specific ports and services.

set -euo pipefail

_HOOK_NAME="infra-intent-detector"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "infra-intent-detector"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
COGNITIVE_OS_YAML="$COGNITIVE_OS_DIR/cognitive-os.yaml"
METRICS_LOG="$COGNITIVE_OS_DIR/metrics/infra-detections.jsonl"

# Read tool input from stdin
INPUT=$(cat)

# Only process Agent/task/delegate tool calls
# Guard against malformed JSON — jq failure should not kill the hook
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || true
if [[ -z "$TOOL_NAME" || ( "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ) ]]; then
  exit 0
fi

# Extract the prompt/task description from the tool input
# Guard against malformed JSON — exit 0 on jq failure
PROMPT_TEXT=$(echo "$INPUT" | jq -r '
  (.tool_input.prompt // "") + " " +
  (.tool_input.description // "") + " " +
  (.tool_input.task // "") + " " +
  (.tool_input.instructions // "")
' 2>/dev/null | tr '[:upper:]' '[:lower:]') || true

if [[ -z "$PROMPT_TEXT" || "$PROMPT_TEXT" == "   " ]]; then
  exit 0
fi

# --- Infrastructure keyword categories ---

DETECTED_INTENTS=()
SUGGESTIONS=()

# Database keywords
DB_PATTERN="store|persist|save to database|database|collection|table|crud|query|migration|schema|entity|repository"
if echo "$PROMPT_TEXT" | grep -qiE "$DB_PATTERN"; then
  DETECTED_INTENTS+=("database")
  SUGGESTIONS+=("Database: Check cognitive-os.yaml project.infrastructure.database for configured databases, or docker-compose.yml for available database containers.")
fi

# Auth keywords
AUTH_PATTERN="login|register|user account|authentication|password|jwt|session|oauth|token|authorize|sign.?up|sign.?in"
if echo "$PROMPT_TEXT" | grep -qiE "$AUTH_PATTERN"; then
  DETECTED_INTENTS+=("auth")
  SUGGESTIONS+=("Auth: Check cognitive-os.yaml project.infrastructure.auth for configured auth provider.")
fi

# Real-time keywords
REALTIME_PATTERN="real.?time|websocket|live|sync|multiplayer|collaborative|socket\.io|sse|server.sent"
if echo "$PROMPT_TEXT" | grep -qiE "$REALTIME_PATTERN"; then
  DETECTED_INTENTS+=("real-time")
  SUGGESTIONS+=("Real-time: Check if WebSocket infrastructure exists in docker-compose.yml. If not, consider adding Socket.IO with Valkey/Redis adapter.")
fi

# Storage keywords
STORAGE_PATTERN="upload|file storage|image|s3|bucket|asset|blob|attachment|media"
if echo "$PROMPT_TEXT" | grep -qiE "$STORAGE_PATTERN"; then
  DETECTED_INTENTS+=("storage")
  SUGGESTIONS+=("Storage: Check docker-compose.yml for S3-compatible storage (SeaweedFS/MinIO/GCS emulator). If none exists, add one or use local filesystem mock.")
fi

# Queue keywords
QUEUE_PATTERN="async|background job|queue|event driven|message broker|kafka|rabbitmq|publish|subscribe|worker|consumer|producer"
if echo "$PROMPT_TEXT" | grep -qiE "$QUEUE_PATTERN"; then
  DETECTED_INTENTS+=("queue")
  SUGGESTIONS+=("Queue: Check cognitive-os.yaml project.infrastructure.messaging for configured message broker.")
fi

# Cache keywords
CACHE_PATTERN="cache|redis|valkey|fast lookup|session store|ttl|expir|memoiz|rate limit"
if echo "$PROMPT_TEXT" | grep -qiE "$CACHE_PATTERN"; then
  DETECTED_INTENTS+=("cache")
  SUGGESTIONS+=("Cache: Check cognitive-os.yaml project.infrastructure.cache for configured cache service.")
fi

# Search keywords
SEARCH_PATTERN="search|full.?text|index|elasticsearch|algolia|find by|filter|facet"
if echo "$PROMPT_TEXT" | grep -qiE "$SEARCH_PATTERN"; then
  DETECTED_INTENTS+=("search")
  SUGGESTIONS+=("Search: Check docker-compose.yml for search engine (Elasticsearch, MeiliSearch, Typesense). If none, consider database-native text search.")
fi

# --- Output suggestions if any detected ---

if [[ ${#DETECTED_INTENTS[@]} -eq 0 ]]; then
  exit 0
fi

INTENTS_STR=$(IFS=", "; echo "${DETECTED_INTENTS[*]}")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build suggestion output
SUGGESTION_TEXT="INFRASTRUCTURE SUGGESTION:\nDetected intent: ${INTENTS_STR}\n"
for s in "${SUGGESTIONS[@]}"; do
  SUGGESTION_TEXT="${SUGGESTION_TEXT}  - ${s}\n"
done
SUGGESTION_TEXT="${SUGGESTION_TEXT}Note: These are suggestions only. Verify against current stack before acting."

# Log to metrics
mkdir -p "$(dirname "$METRICS_LOG")"
PROMPT_PREVIEW=$(echo "$PROMPT_TEXT" | head -c 200 | tr '\n' ' ')
ENTRY="{\"timestamp\":\"${TIMESTAMP}\",\"intents\":[$(printf '"%s",' "${DETECTED_INTENTS[@]}" | sed 's/,$//')],\"prompt_preview\":\"$(echo "$PROMPT_PREVIEW" | sed 's/"/\\"/g')\"}"
safe_jsonl_append "$METRICS_LOG" "$ENTRY"

# Output suggestion as stderr info (does not block)
echo -e "$SUGGESTION_TEXT" >&2

exit 0
