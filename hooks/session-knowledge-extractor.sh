#!/usr/bin/env bash
# session-knowledge-extractor.sh — Extract knowledge patterns from session
# Trigger: Stop (after conversation-capture.sh, before session-cleanup.sh)

_HOOK_NAME="session-knowledge-extractor"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
METRICS_DIR="$(_resolve_metrics_dir)"
KNOWLEDGE_FILE="$PROJECT_DIR/.cognitive-os/metrics/knowledge-graph.jsonl"

# Extract patterns from this session's data

# 1. Check for recurring errors (same fingerprint across sessions)
ERROR_FILE="$METRICS_DIR/error-learning.jsonl"
GLOBAL_ERROR_FILE="$PROJECT_DIR/.cognitive-os/metrics/error-learning.jsonl"

if [ -f "$ERROR_FILE" ] && [ -f "$GLOBAL_ERROR_FILE" ]; then
  # Get fingerprints from this session
  SESSION_FINGERPRINTS=$(jq -r '.fingerprint // empty' "$ERROR_FILE" 2>/dev/null | sort -u)

  for fp in $SESSION_FINGERPRINTS; do
    [ -z "$fp" ] && continue
    # Count occurrences in global history
    GLOBAL_COUNT=$(grep -c "\"$fp\"" "$GLOBAL_ERROR_FILE" 2>/dev/null || echo 0)
    if [ "$GLOBAL_COUNT" -ge 3 ]; then
      # Get error details
      ERROR_DETAIL=$(grep "\"$fp\"" "$GLOBAL_ERROR_FILE" | tail -1 | jq -r '{type: .type, service: .service, context: .context}' 2>/dev/null)
      ENTRY=$(jq -c -n \
        --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg fp "$fp" \
        --argjson count "$GLOBAL_COUNT" \
        --arg pattern "recurring_error" \
        --argjson detail "$ERROR_DETAIL" \
        '{timestamp: $ts, pattern: $pattern, fingerprint: $fp, occurrences: $count, detail: $detail, recommendation: "Consider permanent fix or auto-repair registry entry"}' 2>/dev/null)
      [ -n "$ENTRY" ] && safe_jsonl_append "$KNOWLEDGE_FILE" "$ENTRY"
    fi
  done
fi

# 2. Check skill success rate degradation
SKILL_FILE="$METRICS_DIR/skill-metrics.jsonl"
if [ -f "$SKILL_FILE" ]; then
  # Find skills that failed in this session
  FAILED_SKILLS=$(jq -r 'select(.success == false) | .skill' "$SKILL_FILE" 2>/dev/null | sort -u)
  for skill in $FAILED_SKILLS; do
    [ -z "$skill" ] && continue
    ENTRY=$(jq -c -n \
      --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --arg skill "$skill" \
      --arg pattern "skill_failure" \
      '{timestamp: $ts, pattern: $pattern, skill: $skill, recommendation: "Review skill or run /optimize-skill"}' 2>/dev/null)
    [ -n "$ENTRY" ] && safe_jsonl_append "$KNOWLEDGE_FILE" "$ENTRY"
  done
fi

exit 0
