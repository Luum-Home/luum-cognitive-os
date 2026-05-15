#!/usr/bin/env bash
# SCOPE: os-only
# Resolve one canonical task id for cross-session claim coordination.

_cos_normalize_task_text() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | tr '\n\r\t' '   ' \
    | sed 's/[[:space:]][[:space:]]*/ /g' \
    | sed 's/^[[:space:]]*//' \
    | sed 's/[[:space:]]*$//'
}

_cos_hash_task_text() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$1" <<'PYEOF' 2>/dev/null
import hashlib
import sys
print(hashlib.sha256(sys.argv[1].encode("utf-8")).hexdigest()[:16])
PYEOF
    return
  fi
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | shasum -a 256 | awk '{print substr($1,1,16)}'
    return
  fi
  printf '%s' "$1" | cksum | awk '{print $1}'
}

cos_resolve_task_id() {
  local input_json="${1:-}"
  local fallback_description="${2:-}"
  local fallback_tool_use_id="${3:-}"
  local explicit description normalized digest

  if [ -n "$input_json" ] && command -v jq >/dev/null 2>&1; then
    explicit=$(printf '%s' "$input_json" | jq -r '
      .task_id
      // .id
      // .tool_input.task_id
      // .tool_input.taskId
      // .tool_input.id
      // .tool_input.dispatch_task_id
      // .tool_input.dispatchTaskId
      // .tool_input.cos_task_id
      // .tool_input.cosTaskId
      // empty
    ' 2>/dev/null || true)
    if [ -n "$explicit" ] && [ "$explicit" != "null" ]; then
      printf '%s\n' "$explicit"
      return 0
    fi
  fi

  description="$fallback_description"
  if [ -z "$description" ] && [ -n "$input_json" ] && command -v jq >/dev/null 2>&1; then
    description=$(printf '%s' "$input_json" | jq -r '
      .tool_input.prompt
      // .tool_input.description
      // .tool_input.task
      // empty
    ' 2>/dev/null || true)
  fi

  normalized=$(_cos_normalize_task_text "$description")
  if [ -n "$normalized" ] && [ "$normalized" != "unknown task" ] && [ "$normalized" != "unknown" ]; then
    digest=$(_cos_hash_task_text "$normalized")
    printf 'task-desc-%s\n' "$digest"
    return 0
  fi

  if [ -n "$fallback_tool_use_id" ] && [ "$fallback_tool_use_id" != "null" ]; then
    printf 'task-tool-%s\n' "$fallback_tool_use_id"
    return 0
  fi

  printf 'task-%s-%s\n' "$(date +%s)" "$RANDOM"
}

