#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: observability, tracing
# PostToolUse hook: Send traces to Langfuse and/or Opik after Agent executions
# Fires on "Agent" — extracts execution metadata and POSTs to observability backends
# Both providers disabled by default (env var gated)
# Must complete in <5 seconds (non-blocking, fire-and-forget)

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="observability-trace"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Read stdin and gate on Agent tool
read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent"

# Exit early if no input or no jq
if [ -z "$INPUT" ]; then exit 0; fi
if ! command -v jq &>/dev/null; then exit 0; fi

# Check if either provider is enabled
LANGFUSE_ENABLED="${LANGFUSE_ENABLED:-false}"
OPIK_ENABLED="${OPIK_ENABLED:-false}"

if [ "$LANGFUSE_ENABLED" != "true" ] && [ "$OPIK_ENABLED" != "true" ]; then
  exit 0
fi

# --- Extract trace metadata ---
AGENT_NAME=$(echo "$INPUT" | jq -r '
  .tool_input.skill // .tool_input.description // .tool_input.prompt // "unknown"
' 2>/dev/null | head -c 100)
AGENT_NAME=$(echo "$AGENT_NAME" | sed -E 's/^([a-zA-Z0-9_-]+).*/\1/' | tr '[:upper:]' '[:lower:]')
[ -z "$AGENT_NAME" ] && AGENT_NAME="unknown-agent"

TOOL_RESULT=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"' 2>/dev/null)

# Determine success/failure
SUCCESS="true"
if [ "$EXIT_CODE" != "0" ] && [ "$EXIT_CODE" != "" ]; then
  SUCCESS="false"
fi
if echo "$TOOL_RESULT" | grep -qi "error\|failed\|rejected\|exception\|timed out" 2>/dev/null; then
  SUCCESS="false"
fi

# Extract token counts and duration
TOTAL_TOKENS=$(echo "$INPUT" | jq -r 'try (.tool_response.total_tokens // .tool_response.usage.total_tokens // 0) catch 0' 2>/dev/null || echo "0")
INPUT_TOKENS=$(echo "$INPUT" | jq -r 'try (.tool_response.input_tokens // .tool_response.usage.input_tokens // 0) catch 0' 2>/dev/null || echo "0")
OUTPUT_TOKENS=$(echo "$INPUT" | jq -r 'try (.tool_response.output_tokens // .tool_response.usage.output_tokens // 0) catch 0' 2>/dev/null || echo "0")
DURATION_MS=$(echo "$INPUT" | jq -r 'try (.tool_response.duration_ms // .tool_response.durationMs // 0) catch 0' 2>/dev/null || echo "0")
MODEL=$(echo "$INPUT" | jq -r 'try (.tool_response.model // .tool_response.usage.model // "unknown") catch "unknown"' 2>/dev/null || echo "unknown")

# Get current phase
PHASE=$(get_phase "unknown")

# Timestamps
NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Compute approximate start time from duration
if [ "$DURATION_MS" -gt 0 ] 2>/dev/null; then
  DURATION_SECS=$((DURATION_MS / 1000))
  START_EPOCH=$(($(date +%s) - DURATION_SECS))
  START_ISO=$(date -u -r "$START_EPOCH" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "$NOW_ISO")
else
  START_ISO="$NOW_ISO"
fi

# Generate a unique trace ID
TRACE_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))" 2>/dev/null || echo "trace-$(date +%s)-$$")

# Estimate cost
COST_USD="0.0"
if command -v python3 &>/dev/null; then
  COST_USD=$(python3 -c "
model = '${MODEL}'.lower()
costs = {'opus': (15.0, 75.0), 'sonnet': (3.0, 15.0), 'haiku': (0.25, 1.25)}
family = 'sonnet'
for f in costs:
    if f in model:
        family = f
        break
inp, out = costs[family]
cost = (${INPUT_TOKENS:-0} * inp + ${OUTPUT_TOKENS:-0} * out) / 1_000_000
print(f'{cost:.6f}')
" 2>/dev/null || echo "0.0")
fi

# Input/output text excerpts for trace context
INPUT_TEXT=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // ""' 2>/dev/null | head -c 500)
OUTPUT_TEXT=$(echo "$TOOL_RESULT" | head -c 500 2>/dev/null || echo "")

# Metrics directory for local logging
METRICS_DIR="$(resolve_session_dir)"
TRACE_LOG="$METRICS_DIR/observability-traces.jsonl"

# --- Send to Langfuse ---
LANGFUSE_STATUS="skipped"
if [ "$LANGFUSE_ENABLED" = "true" ]; then
  LANGFUSE_HOST="${LANGFUSE_HOST:-http://localhost:3100}"
  LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
  LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"

  if [ -n "$LANGFUSE_PUBLIC_KEY" ] && [ -n "$LANGFUSE_SECRET_KEY" ]; then
    # Langfuse v3 ingestion API: POST /api/public/ingestion
    LANGFUSE_PAYLOAD=$(jq -nc \
      --arg id "$TRACE_ID" \
      --arg name "$AGENT_NAME" \
      --arg start "$START_ISO" \
      --arg end "$NOW_ISO" \
      --arg model "$MODEL" \
      --arg phase "$PHASE" \
      --argjson tokens "${TOTAL_TOKENS:-0}" \
      --arg cost "$COST_USD" \
      --argjson success "$SUCCESS" \
      --arg input "$INPUT_TEXT" \
      --arg output "$OUTPUT_TEXT" \
      --argjson input_tokens "${INPUT_TOKENS:-0}" \
      --argjson output_tokens "${OUTPUT_TOKENS:-0}" \
      '{
        batch: [{
          id: $id,
          type: "trace-create",
          timestamp: $end,
          body: {
            id: $id,
            name: $name,
            input: $input,
            output: $output,
            metadata: {
              agent: $name,
              phase: $phase,
              model: $model,
              tokens: $tokens,
              input_tokens: $input_tokens,
              output_tokens: $output_tokens,
              cost_usd: $cost,
              success: $success
            }
          }
        }]
      }' 2>/dev/null)

    if [ -n "$LANGFUSE_PAYLOAD" ]; then
      # Base64 encode credentials for Basic auth
      AUTH_HEADER=$(printf '%s:%s' "$LANGFUSE_PUBLIC_KEY" "$LANGFUSE_SECRET_KEY" | base64 2>/dev/null | tr -d '\n')

      HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 3 --max-time 5 \
        -X POST "${LANGFUSE_HOST}/api/public/ingestion" \
        -H "Content-Type: application/json" \
        -H "Authorization: Basic ${AUTH_HEADER}" \
        -d "$LANGFUSE_PAYLOAD" 2>/dev/null || echo "000")

      if [ "$HTTP_CODE" -ge 200 ] 2>/dev/null && [ "$HTTP_CODE" -lt 300 ] 2>/dev/null; then
        LANGFUSE_STATUS="sent"
      else
        LANGFUSE_STATUS="failed:${HTTP_CODE}"
        echo "[observability-trace] WARNING: Langfuse POST returned HTTP ${HTTP_CODE}" >&2
      fi
    else
      LANGFUSE_STATUS="failed:payload_build"
    fi
  else
    LANGFUSE_STATUS="failed:missing_keys"
    echo "[observability-trace] WARNING: LANGFUSE_ENABLED=true but LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY is empty" >&2
  fi
fi

# --- Send to Opik ---
OPIK_STATUS="skipped"
if [ "$OPIK_ENABLED" = "true" ]; then
  OPIK_HOST="${OPIK_HOST:-http://localhost:5173}"

  OPIK_PAYLOAD=$(jq -nc \
    --arg id "$TRACE_ID" \
    --arg name "$AGENT_NAME" \
    --arg start "$START_ISO" \
    --arg end "$NOW_ISO" \
    --arg model "$MODEL" \
    --arg phase "$PHASE" \
    --argjson tokens "${TOTAL_TOKENS:-0}" \
    --arg cost "$COST_USD" \
    --argjson success "$SUCCESS" \
    --arg input "$INPUT_TEXT" \
    --arg output "$OUTPUT_TEXT" \
    --argjson input_tokens "${INPUT_TOKENS:-0}" \
    --argjson output_tokens "${OUTPUT_TOKENS:-0}" \
    '{
      id: $id,
      name: $name,
      start_time: $start,
      end_time: $end,
      input: { text: $input },
      output: { text: $output },
      metadata: {
        agent: $name,
        phase: $phase,
        model: $model,
        tokens: $tokens,
        input_tokens: $input_tokens,
        output_tokens: $output_tokens,
        cost_usd: $cost,
        success: $success
      }
    }' 2>/dev/null)

  if [ -n "$OPIK_PAYLOAD" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      --connect-timeout 3 --max-time 5 \
      -X POST "${OPIK_HOST}/api/v1/private/traces" \
      -H "Content-Type: application/json" \
      -d "$OPIK_PAYLOAD" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" -ge 200 ] 2>/dev/null && [ "$HTTP_CODE" -lt 300 ] 2>/dev/null; then
      OPIK_STATUS="sent"
    else
      OPIK_STATUS="failed:${HTTP_CODE}"
      echo "[observability-trace] WARNING: Opik POST returned HTTP ${HTTP_CODE}" >&2
    fi
  else
    OPIK_STATUS="failed:payload_build"
  fi
fi

# --- Log trace attempt locally ---
TRACE_LOG_LINE=$(jq -nc \
  --arg ts "$NOW_ISO" \
  --arg trace_id "$TRACE_ID" \
  --arg agent "$AGENT_NAME" \
  --arg model "$MODEL" \
  --arg phase "$PHASE" \
  --argjson tokens "${TOTAL_TOKENS:-0}" \
  --argjson duration "${DURATION_MS:-0}" \
  --arg cost "$COST_USD" \
  --argjson success "$SUCCESS" \
  --arg langfuse "$LANGFUSE_STATUS" \
  --arg opik "$OPIK_STATUS" \
  '{timestamp: $ts, trace_id: $trace_id, agent: $agent, model: $model, phase: $phase,
    tokens: $tokens, duration_ms: $duration, cost_usd: $cost, success: $success,
    langfuse: $langfuse, opik: $opik}' 2>/dev/null)

[ -n "$TRACE_LOG_LINE" ] && safe_jsonl_append "$TRACE_LOG" "$TRACE_LOG_LINE"

exit 0
